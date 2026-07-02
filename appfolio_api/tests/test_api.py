import os
os.environ["APPFOLIO_DB_PATH"] = ":memory:"

from fastapi.testclient import TestClient
from app.main import app, db
from app.client import AppFolioReportClient
from app.importer import ReportImporter


def test_tenant_context(tmp_path):
    db.path = tmp_path / "test.db"
    with TestClient(app) as client:
        importer = ReportImporter(db)
        importer.import_records("tenant_lease", [{"Property ID":"p1","Property Name":"Oak Court","Unit ID":"u1","Unit Name":"2A","Tenant ID":"t1","Tenant Name":"Ada Tenant","Lease ID":"l1","Lease Status":"Current","Balance":"125.50","Property Manager ID":"m1","Property Manager":"Pat Manager"}])
        importer.import_records("owner_property", [{"Property ID":"p1","Property Name":"Oak Court","Owner ID":"o1","Owner Name":"Olivia Owner","Ownership Percent":"100%"}])
        importer.import_records("work_order", [{"Work Order ID":"w1","Property ID":"p1","Unit ID":"u1","Tenant ID":"t1","Status":"Open","Description":"Leaky faucet"}])
        response = client.get("/api/tenants/t1/context")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant"]["name"] == "Ada Tenant"
        assert data["leases"][0]["property_name"] == "Oak Court"
        assert data["owners"][0]["id"] == "o1"
        assert data["work_orders"][0]["id"] == "w1"
        assert client.get("/api/validation/links").json()["valid"] is True


def test_missing_required_ids(tmp_path):
    db.path = tmp_path / "bad.db"; db.initialize()
    try:
        ReportImporter(db).import_records("tenant_lease", [{"Tenant ID":"t1"}])
        assert False, "expected validation failure"
    except ValueError as exc:
        assert "require" in str(exc)


def test_both_appfolio_report_routes_are_exposed():
    paths = app.openapi()["paths"]
    assert "/api/imports/appfolio/{report_type}/standard/{report_name}" in paths
    assert "/api/imports/appfolio/{report_type}/saved/{saved_report_id}" in paths


def test_report_identifiers_reject_path_injection():
    client = AppFolioReportClient("https://example.appfolio.com", "id", "secret")
    async def consume(iterator):
        async for _ in iterator:
            pass
    import asyncio
    try:
        asyncio.run(consume(client.iter_standard_report("../saved/bad")))
        assert False, "expected validation failure"
    except ValueError as exc:
        assert "Invalid" in str(exc)
