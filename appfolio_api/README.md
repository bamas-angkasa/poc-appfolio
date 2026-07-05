# AppFolio Report Context POC

Read-only FastAPI service that imports official AppFolio saved reports into normalized SQLite tables and builds tenant context. It intentionally does not reuse the browser-cookie scraper.

## Recommended reports

Do not make one master report unless AppFolio exposes every stable ID cleanly. Create these saved reports and include the exact ID columns:

1. `tenant_lease`: Property ID/name/address, Unit ID/name, Tenant ID/name/email/phone, Lease (or Occupancy) ID, dates, status, balance, Property Manager ID/name.
2. `owner_property`: Owner ID/name/contact/address, Property ID/name, ownership percent.
3. `work_order`: Work Order ID, Property ID, Unit ID, Tenant ID, Vendor ID, status, description and dates.
4. `vendor`: Vendor ID/name/contact.
5. `charge` (optional): Charge ID, Lease ID, amount, due date, description.

The owner-directory example in the prompt is insufficient for relational import because it has names but no Owner ID or Property ID. Add those fields to the saved report before using it.

## Run

```powershell
cd poc-appfolio/appfolio_api
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Load .env values into your shell or configure the environment in your IDE.
.venv\Scripts\uvicorn app.main:app --reload
```

The application automatically reads `.env` from this directory. Existing environment variables override values in that file. Open `http://127.0.0.1:8000/docs`; SQLite tables are created automatically.

The `examples/` directory contains synthetic CSV/JSON for three tenants. In the API docs, call `/api/imports/file` in this order: `tenant_lease.csv`, `owner_property.json`, then `work_order.csv`, choosing the matching `report_type` each time.

Upload CSV/JSON using `POST /api/imports/file` (`report_type` plus `file`). AppFolio exposes two report URL shapes, so the local API makes the distinction explicit:

- Standard report: `POST /api/imports/appfolio/{report_type}/standard/{report_name}` maps to AppFolio `/api/v2/reports/{report_name}.json`.
- Saved report: `POST /api/imports/appfolio/{report_type}/saved/{uuid}` maps to AppFolio `/api/v2/reports/saved/{uuid}.json`.

For example, `POST /api/imports/appfolio/owner_property/standard/owner_directory` calls AppFolio's standard owner-directory report. It can only be normalized if its selected columns contain both Owner ID and Property ID; names and `properties_owned` text alone are not safe relational identifiers. Both report forms follow `next_page_url`. Credentials are read only from environment variables and are never logged or committed.

The AppFolio client invokes standard reports with `POST` JSON and saved reports with `GET`. Standard-report `next_page_url` pages use `POST {}`, while saved-report pages remain `GET`; those cached pagination URLs are short-lived. Page size is capped at 5,000 and pagination remains enabled.

Retrieve combined context at `GET /api/tenants/{tenantId}/context` and check referential integrity at `GET /api/validation/links`.

## Test

```powershell
.venv\Scripts\pytest -q
```

For acceptance, export each report for 3–5 real tenants/properties, import in dependency order (`tenant_lease`, `owner_property`, `vendor`, `work_order`, `charge`), verify `/api/validation/links`, and compare the context endpoint with AppFolio.
