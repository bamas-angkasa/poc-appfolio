# POC 2: AppFolio Email/SMS Communication Sync

## Summary

Build a read-only Python sync pipeline that:

1. Discovers tenants and owners with their AppFolio IDs, email short UIDs, and phone numbers.
2. Syncs selected parties’ complete email and SMS histories.
3. Saves every AppFolio response to raw JSON before transformation.
4. Stores normalized records and attachment metadata in SQLite.
5. Detects expired browser cookies clearly.
6. Optionally downloads attachments to local files.

## Implementation Changes

### Party discovery

- Add `communication_parties` with:
  - `party_type`: `tenant` or `owner`
  - AppFolio source ID
  - name
  - preferred email and phone
  - email short UID
  - all discovered contacts as JSON
  - raw JSON
  - unique constraint on `(party_type, appfolio_source_id)`
- Paginate tenant and owner lists from first to last page.
- Fetch detail records when list responses lack phone, email, or short UID.
- Save discovery responses under `raw/{run_id}/parties/`.
- Sync communications only for explicitly selected party IDs.

### Email sync

- Request `/emails` with each party’s `short_uids[]`.
- Traverse page 1 through the parsed last page.
- Normalize and deduplicate list records by email ID.
- Request `/emails/{email_id}` for every email to obtain authoritative sender, recipients, body, direction, timestamps, and `attachment_links`.
- Save list and detail responses under `raw/{run_id}/emails/`.
- Parse attachment metadata from `attachment_links`, falling back to `attachment_url` HTML.
- Optionally GET attachment preview URLs and save files under `attachments/email/{email_id}/`.

### SMS sync

- Request `/sms` using the selected party’s normalized phone number.
- Begin with empty `min_id`/`max_id`, `limit=50`.
- Fetch older pages by setting `max_id` below the smallest returned message ID; stop on an empty/short page or when no new IDs appear.
- Deduplicate messages by SMS ID.
- Map `direction`, status, timestamp, remote number, sender user, body, errors, and thread UUID.
- Treat SMS `media` entries as communication attachments and optionally download them.
- Save responses under `raw/{run_id}/sms/{party_id}/`.

### Persistence

Create SQLite tables:

- `communications`
  - party foreign key
  - channel: `email` or `sms`
  - AppFolio source ID
  - direction, status, sent timestamp
  - from/to values
  - nullable subject
  - body
  - AppFolio href
  - raw JSON
  - sync timestamp
  - unique `(channel, appfolio_source_id)`

- `communication_attachments`
  - communication foreign key
  - AppFolio attachment/media ID
  - filename
  - remote/preview URL
  - local path
  - content type and size when available
  - raw JSON
  - unique `(communication_id, remote_url)`

Use SQLite transactions and upserts so rerunning a sync updates changed status/body data without duplicating records.

### Configuration and CLI

- Load `.env` with:
  - `APPFOLIO_DOMAIN`
  - `APPFOLIO_COOKIE`
  - `APPFOLIO_DB_PATH`
  - `APPFOLIO_RAW_DIR`
  - `APPFOLIO_ATTACHMENT_DIR`
- Add `.env.example`; exclude `.env`, raw responses, SQLite files, and downloaded attachments from Git.
- Provide commands:
  - `discover-parties --types tenants owners`
  - `list-parties`
  - `sync --party-id ID --party-id ID --channels email sms`
  - optional `--download-attachments`
- Preserve existing diagnostic commands where practical.
- Only issue HTTP GET requests in this POC.

### Authentication handling

- Detect `401`/`403`, redirects to login, login-page HTML, and unexpected HTML where JSON is required.
- Raise a dedicated session-expired error.
- Stop the run rather than storing login HTML as communication data.
- Log endpoint, party, channel, and page/cursor without logging cookie values.
- Return a clear instruction to refresh `APPFOLIO_COOKIE`.

## Test Plan

- Parse captured email list, email detail, attachment, and SMS fixtures.
- Verify email pagination reaches all pages and removes repeated IDs.
- Verify SMS cursor pagination stops safely and removes repeated IDs.
- Verify detail responses populate bodies and recipients.
- Verify attachment metadata and authenticated file download.
- Verify rerunning identical fixtures leaves row counts unchanged.
- Verify updated status/body fields are upserted.
- Verify expired-cookie redirects and `401`/`403` fail clearly.
- Run an authenticated POC against three selected parties and compare AppFolio counts with raw JSON and SQLite counts.

## Assumptions

- SQLite is the POC database.
- Tenants and owners are in scope; vendors are excluded.
- Discovery covers everyone, but communication sync requires selected IDs.
- Attachments are stored as files with paths in SQLite, not as blobs.
- `.env` is the credential mechanism and remains local.
- Initial sync retrieves full available history; later runs rely on upserts and duplicate protection.
