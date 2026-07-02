from contextlib import asynccontextmanager
import json
import sqlite3

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .client import AppFolioReportClient
from .config import get_settings
from .database import Database
from .importer import ReportImporter

settings = get_settings()
db = Database(settings.db_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.initialize()
    yield


app = FastAPI(title="AppFolio Report Context POC", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health(): return {"status": "ok"}


@app.post("/api/imports/file")
async def import_file(report_type: str = Form(...), file: UploadFile = File(...)):
    body = await file.read()
    try:
        if (file.filename or "").lower().endswith(".csv"):
            import csv, io
            records = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
        else:
            payload = json.loads(body)
            records = payload.get("results", payload) if isinstance(payload, dict) else payload
        return ReportImporter(db).import_records(report_type, records, f"file:{file.filename}")
    except (ValueError, json.JSONDecodeError, sqlite3.IntegrityError) as exc:
        raise HTTPException(422, str(exc)) from exc


def appfolio_client():
    if not all((settings.base_url, settings.client_id, settings.client_secret)):
        raise HTTPException(503, "Set APPFOLIO_BASE_URL, APPFOLIO_CLIENT_ID, and APPFOLIO_CLIENT_SECRET")
    return AppFolioReportClient(settings.base_url, settings.client_id, settings.client_secret, settings.timeout_seconds)


async def import_appfolio_pages(report_type: str, pages, source: str):
    totals = []
    try:
        async for page in pages:
            totals.append(ReportImporter(db).import_records(report_type, page, source))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"AppFolio report sync failed: {exc}") from exc
    return {"pages": len(totals), "records_imported": sum(item["records_imported"] for item in totals), "sync_runs": totals}


@app.post("/api/imports/appfolio/{report_type}/standard/{report_name}")
async def import_standard_report(report_type: str, report_name: str):
    client = appfolio_client()
    return await import_appfolio_pages(
        report_type,
        client.iter_standard_report(report_name),
        f"appfolio:standard:{report_name}",
    )


@app.post("/api/imports/appfolio/{report_type}/saved/{saved_report_id}")
async def import_saved_report(report_type: str, saved_report_id: str):
    client = appfolio_client()
    return await import_appfolio_pages(
        report_type,
        client.iter_saved_report(saved_report_id),
        f"appfolio:saved:{saved_report_id}",
    )


@app.post("/api/imports/appfolio/{report_type}/{saved_report_id}", deprecated=True)
async def import_saved_report_legacy(report_type: str, saved_report_id: str):
    return await import_saved_report(report_type, saved_report_id)


def rows(c, query, parameters=()):
    return [dict(row) for row in c.execute(query, parameters).fetchall()]


@app.get("/api/tenants/{tenant_id}/context")
def tenant_context(tenant_id: str):
    with db.connect() as c:
        tenant = c.execute("SELECT id,name,email,phone,updated_at FROM tenants WHERE id=?", (tenant_id,)).fetchone()
        if not tenant: raise HTTPException(404, "Tenant not found")
        leases = rows(c, "SELECT l.id,l.start_date,l.end_date,l.status,l.balance,u.id unit_id,u.name unit_name,p.id property_id,p.name property_name,p.address property_address FROM leases l JOIN units u ON u.id=l.unit_id JOIN properties p ON p.id=u.property_id WHERE l.tenant_id=?", (tenant_id,))
        property_ids = list({lease["property_id"] for lease in leases})
        owners, managers = [], []
        for property_id in property_ids:
            owners += rows(c, "SELECT o.id,o.name,o.email,o.phone,o.address,po.ownership_percent,po.property_id FROM owners o JOIN property_owners po ON po.owner_id=o.id WHERE po.property_id=?",(property_id,))
            managers += rows(c, "SELECT m.id,m.name,m.email,m.phone,p.id property_id FROM properties p JOIN property_managers m ON m.id=p.property_manager_id WHERE p.id=?",(property_id,))
        return {"tenant":dict(tenant),"leases":leases,"owners":owners,"property_managers":managers,"work_orders":rows(c,"SELECT id,property_id,unit_id,vendor_id,status,description,created_at,completed_at FROM work_orders WHERE tenant_id=? ORDER BY created_at DESC",(tenant_id,)),"charges":rows(c,"SELECT c.id,c.lease_id,c.amount,c.description,c.due_date FROM charges c JOIN leases l ON l.id=c.lease_id WHERE l.tenant_id=?",(tenant_id,))}


@app.get("/api/validation/links")
def validate_links():
    checks = {}
    with db.connect() as c:
        for name, query in {
            "units_without_property":"SELECT COUNT(*) FROM units u LEFT JOIN properties p ON p.id=u.property_id WHERE p.id IS NULL",
            "leases_without_tenant":"SELECT COUNT(*) FROM leases l LEFT JOIN tenants t ON t.id=l.tenant_id WHERE t.id IS NULL",
            "leases_without_unit":"SELECT COUNT(*) FROM leases l LEFT JOIN units u ON u.id=l.unit_id WHERE u.id IS NULL",
            "owner_links_without_property":"SELECT COUNT(*) FROM property_owners po LEFT JOIN properties p ON p.id=po.property_id WHERE p.id IS NULL",
        }.items(): checks[name] = c.execute(query).fetchone()[0]
    return {"valid": not any(checks.values()), "orphan_counts": checks}
