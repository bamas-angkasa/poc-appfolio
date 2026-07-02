from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import csv
import json
import re
import uuid

from .database import Database


ALIASES = {
    "property_id": ("property_id", "property id", "property_uid"),
    "unit_id": ("unit_id", "unit id", "unit_uid"),
    "tenant_id": ("tenant_id", "tenant id", "tenant_uid"),
    "lease_id": ("lease_id", "lease id", "occupancy_id", "occupancy id"),
    "owner_id": ("owner_id", "owner id", "owner_uid"),
    "work_order_id": ("work_order_id", "work order id", "service_request_id"),
    "vendor_id": ("vendor_id", "vendor id", "vendor_uid"),
    "manager_id": ("property_manager_id", "property manager id", "manager_id"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(record: dict[str, Any]) -> dict[str, Any]:
    return {str(k).strip().lower().replace("_", " "): v for k, v in record.items()}


def value(record: dict[str, Any], *names: str, default=None):
    normalized = clean(record)
    for name in names:
        key = name.strip().lower().replace("_", " ")
        if normalized.get(key) not in (None, ""):
            return normalized[key]
    return default


def source_id(record: dict[str, Any], entity: str) -> str | None:
    candidate = value(record, *ALIASES[entity])
    return str(candidate).strip() if candidate not in (None, "") else None


def as_float(item):
    if item in (None, ""):
        return None
    match = re.search(r"-?[\d,]+(?:\.\d+)?", str(item))
    return float(match.group().replace(",", "")) if match else None


def load_records(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("results", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("JSON must be an array or an object containing 'results'")
    return records


class ReportImporter:
    REPORT_TYPES = {"tenant_lease", "owner_property", "work_order", "vendor", "charge"}

    def __init__(self, db: Database):
        self.db = db

    def import_records(self, report_type: str, records: Iterable[dict], source: str = "upload") -> dict:
        if report_type not in self.REPORT_TYPES:
            raise ValueError(f"Unknown report_type; expected one of {sorted(self.REPORT_TYPES)}")
        rows = list(records)
        run_id = str(uuid.uuid4())
        started = now()
        with self.db.connect() as connection:
            connection.execute("INSERT INTO sync_runs(id,report_type,source,status,records_seen,started_at) VALUES(?,?,?,?,?,?)",
                               (run_id, report_type, source, "running", len(rows), started))
            imported = 0
            try:
                for record in rows:
                    getattr(self, f"_import_{report_type}")(connection, record)
                    imported += 1
                connection.execute("UPDATE sync_runs SET status='completed',records_imported=?,finished_at=? WHERE id=?",
                                   (imported, now(), run_id))
            except Exception as exc:
                connection.execute("UPDATE sync_runs SET status='failed',error=?,finished_at=? WHERE id=?",
                                   (str(exc), now(), run_id))
                raise
        return {"sync_run_id": run_id, "report_type": report_type, "records_seen": len(rows), "records_imported": imported}

    @staticmethod
    def _upsert(c, table: str, data: dict):
        columns = list(data)
        assignments = ",".join(
            f"{column}=COALESCE(excluded.{column},{table}.{column})"
            for column in columns if column != "id"
        )
        c.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) "
                  f"ON CONFLICT(id) DO UPDATE SET {assignments}", tuple(data.values()))

    def _import_tenant_lease(self, c, r):
        p, u, t, lease = (source_id(r, key) for key in ("property_id", "unit_id", "tenant_id", "lease_id"))
        if not all((p, u, t, lease)):
            raise ValueError("tenant_lease rows require property_id, unit_id, tenant_id, and lease_id")
        raw, stamp = json.dumps(r, default=str), now()
        manager = source_id(r, "manager_id")
        if manager:
            self._upsert(c, "property_managers", {"id": manager, "name": value(r, "property manager", "manager name", default=manager), "email": value(r,"manager email"), "phone": value(r,"manager phone"), "raw_json":raw,"updated_at":stamp})
        self._upsert(c, "properties", {"id":p,"name":value(r,"property name","property",default=p),"address":value(r,"property address"),"property_manager_id":manager,"raw_json":raw,"updated_at":stamp})
        self._upsert(c, "units", {"id":u,"property_id":p,"name":value(r,"unit name","unit",default=u),"address":value(r,"unit address"),"raw_json":raw,"updated_at":stamp})
        self._upsert(c, "tenants", {"id":t,"name":value(r,"tenant name","tenant",default=t),"email":value(r,"tenant email","email"),"phone":value(r,"tenant phone","phone"),"raw_json":raw,"updated_at":stamp})
        self._upsert(c, "leases", {"id":lease,"tenant_id":t,"unit_id":u,"start_date":value(r,"lease start","start date"),"end_date":value(r,"lease end","end date"),"status":value(r,"lease status","status"),"balance":as_float(value(r,"balance")),"raw_json":raw,"updated_at":stamp})

    def _import_owner_property(self, c, r):
        p, owner = source_id(r,"property_id"), source_id(r,"owner_id")
        if not p or not owner: raise ValueError("owner_property rows require property_id and owner_id")
        raw, stamp = json.dumps(r, default=str), now()
        property_name = value(r,"property name","property")
        c.execute("INSERT OR IGNORE INTO properties(id,name,address,property_manager_id,raw_json,updated_at) VALUES(?,?,?,?,?,?)",(p,property_name or p,value(r,"property address"),None,raw,stamp))
        if property_name:
            self._upsert(c,"properties",{"id":p,"name":property_name,"address":value(r,"property address"),"property_manager_id":None,"raw_json":raw,"updated_at":stamp})
        self._upsert(c,"owners",{"id":owner,"name":value(r,"owner name","name",default=owner),"email":value(r,"owner email","email"),"phone":value(r,"owner phone","phone numbers","phone"),"address":value(r,"owner address","address"),"raw_json":raw,"updated_at":stamp})
        c.execute("INSERT INTO property_owners(property_id,owner_id,ownership_percent) VALUES(?,?,?) ON CONFLICT(property_id,owner_id) DO UPDATE SET ownership_percent=excluded.ownership_percent",(p,owner,as_float(value(r,"ownership percent","ownership %"))))

    def _import_vendor(self, c, r):
        vendor = source_id(r,"vendor_id")
        if not vendor: raise ValueError("vendor rows require vendor_id")
        self._upsert(c,"vendors",{"id":vendor,"name":value(r,"vendor name","name",default=vendor),"email":value(r,"email"),"phone":value(r,"phone"),"raw_json":json.dumps(r,default=str),"updated_at":now()})

    def _import_work_order(self, c, r):
        work, p = source_id(r,"work_order_id"), source_id(r,"property_id")
        if not work or not p: raise ValueError("work_order rows require work_order_id and property_id")
        raw, stamp = json.dumps(r,default=str), now()
        property_name = value(r,"property name","property")
        c.execute("INSERT OR IGNORE INTO properties(id,name,address,property_manager_id,raw_json,updated_at) VALUES(?,?,?,?,?,?)",(p,property_name or p,value(r,"property address"),None,raw,stamp))
        if property_name:
            self._upsert(c,"properties",{"id":p,"name":property_name,"address":value(r,"property address"),"property_manager_id":None,"raw_json":raw,"updated_at":stamp})
        self._upsert(c,"work_orders",{"id":work,"property_id":p,"unit_id":source_id(r,"unit_id"),"tenant_id":source_id(r,"tenant_id"),"vendor_id":source_id(r,"vendor_id"),"status":value(r,"status"),"description":value(r,"description","work order summary"),"created_at":value(r,"created at","created date"),"completed_at":value(r,"completed at","completed date"),"raw_json":raw,"updated_at":stamp})

    def _import_charge(self, c, r):
        charge, lease = str(value(r,"charge id") or ""), source_id(r,"lease_id")
        if not charge or not lease: raise ValueError("charge rows require charge_id and lease_id")
        self._upsert(c,"charges",{"id":charge,"lease_id":lease,"amount":as_float(value(r,"amount")) or 0,"description":value(r,"description"),"due_date":value(r,"due date"),"raw_json":json.dumps(r,default=str),"updated_at":now()})
