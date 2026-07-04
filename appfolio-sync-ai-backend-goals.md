# AppFolio Sync + AI Backend Service Goals

**Document purpose:** Align business, architecture, data model, sync strategy, and AI implementation goals before asking Codex or another AI coding agent to build the backend service.

**Project:** AI Chatbot - Property / AppFolio Maintenance AI Assistant  
**Primary business user:** Property manager  
**Primary technical goal:** Build a reliable backend service that pulls/syncs AppFolio data into our database, organizes it into a clean property-management data model, and gives AI enough safe context to help property managers respond faster.  
**Recommended core stack:** Go backend + PostgreSQL + worker queue. Python may be used only for experimental or unofficial connector work.

---

## 1. One-Sentence Summary

We are building a backend sync and AI recommendation service that pulls AppFolio property-management data, normalizes it into our own database, links properties, units, leases, people, work orders, documents, messages, and notes, then uses AI to summarize context and draft safe human-approved replies for property managers.

---

## 2. Business Context

Property managers currently spend too much time checking AppFolio, work orders, emails, SMS, notes, vendor updates, and tenant messages before replying.

The goal is not just to create a chatbot. The goal is to create an internal AI operations layer that helps managers answer faster while keeping control, privacy, and auditability.

The service should help answer questions like:

- What happened on this maintenance case?
- Who is involved: tenant, owner, vendor, property manager?
- What is the latest message from tenant/vendor/owner?
- What is the status of the work order?
- Are there internal notes that must not be shared?
- What should the property manager say next?
- Can AI draft a reply that the manager can review, edit, approve, copy, and manually send?

---

## 3. Product Goal

Build a production-ready backend foundation that can:

1. Pull or sync AppFolio data.
2. Store raw source payloads for traceability.
3. Normalize data into our own relational model.
4. Link people, properties, units, leases, work orders, notes, messages, and attachments.
5. Build safe AI context for each maintenance case.
6. Generate AI summaries, intent classification, recommended actions, and draft replies.
7. Enforce human-in-the-loop approval.
8. Prevent internal, owner-only, or `#` notes from leaking into tenant/vendor replies.
9. Track all actions in audit logs.
10. Prepare the foundation for future automation, RBAC, SSO, multi-organization support, and deeper AppFolio integration.

---

## 4. What This Service Is

This backend service is the source of truth for our product workflow.

It should include:

- API service for the dashboard.
- Worker service for sync jobs and AI jobs.
- PostgreSQL database.
- AppFolio connector interface.
- Official AppFolio connector implementation when access is confirmed.
- Fake/mock connector for development and tests.
- Optional experimental unofficial connector for communication records only, behind a feature flag.
- AI provider abstraction.
- Recommendation workflow.
- Audit log.
- Sync health tracking.
- RBAC and organization isolation.

---

## 5. What This Service Is Not

Phase 1 must not become too broad.

Phase 1 is **not**:

- A tenant-facing chatbot.
- A fully automated outbound messaging bot.
- A legal, insurance, liability, or payment decisioning engine.
- A vendor dispatch automation system.
- A replacement for AppFolio.
- A write-back system unless AppFolio entitlement and safe write behavior are confirmed.

The first production goal is an internal maintenance inbox and AI review workflow.

---

## 6. Recommended Technical Direction

### 6.1 Core Backend

Use **Golang** for the production backend service.

Recommended Go stack:

- Go 1.22+ or latest stable.
- Echo for HTTP routing.
- PostgreSQL as primary database.
- `pgx` for database driver.
- `sqlc` for type-safe SQL.
- Forward-only SQL migrations.
- OpenAPI as the frontend/backend contract.
- API binary and worker binary.
- Queue abstraction, with SQS/EventBridge in AWS production.

Why Go:

- Good for long-running workers.
- Strong concurrency model.
- Strong type safety.
- Good performance.
- Good fit for sync, queues, API, and domain services.
- Easier to build a stable production backend foundation.

### 6.2 Python Usage

Use **Python only as an optional experimental connector layer**, especially for browser/cookie-based AppFolio access that was already tested.

Python can be useful for:

- Browser automation proof of concept.
- HTML/PDF parsing experiments.
- Scraping communication records when official API does not expose email/SMS.
- Fast iteration during discovery.

Python should not own the core production workflow unless the team makes a deliberate decision later.

The production backend should treat Python as an internal provider behind an interface, not as the main source of truth.

---

## 7. High-Level Architecture

```text
Next.js Dashboard
    |
    | HTTPS / OpenAPI client
    v
Go API Service
    |
    | reads/writes
    v
PostgreSQL
    ^
    |
Go Worker Service
    |
    | scheduled jobs / queue jobs
    v
AppFolio Connector Interface
    |---- Official AppFolio API / Saved Reports
    |---- Fake Connector for local/dev/test
    |---- Optional Unofficial Browser Connector, feature-flagged

Go Worker Service
    |
    | builds safe context
    v
AI Provider Interface
    |---- OpenAI / Claude / other model provider

Go API Service
    |
    | returns inbox, work order detail, recommendations, audit, sync health
    v
Property Manager Dashboard
```

---

## 8. Root Data Decision

Do not choose only `Property` or only `People` as the root.

Use this rule:

```text
Property / Unit / Lease = operational context root
Party / Person / Organization = identity root
Work Order / Message = workflow event root
```

### Why

Most support and maintenance cases happen at a location:

```text
Property -> Unit -> Lease -> Tenant -> Work Order -> Message -> AI Recommendation
```

But the same person can appear in multiple roles:

```text
Same Party can be:
- Tenant
- Owner
- Homeowner
- Vendor contact
- Board member
- Applicant
```

So the data model must separate identity from role.

### Recommended interpretation

- **Property** tells us where the issue is.
- **Unit** tells us the exact location.
- **Lease** tells us tenant relationship and rules.
- **Party** tells us who the person/company is.
- **Role** tells us what that party means in this context.
- **Work order** tells us what operational case is active.
- **Communication** tells us what was said.
- **Recommendation** tells us what AI suggests next.

---

## 9. Canonical Data Model

The backend should normalize AppFolio data into our own canonical model.

Do not mirror AppFolio directly as the main product model. Store AppFolio raw payloads separately for traceability, but use our own clean relational model for product logic.

### 9.1 Organization and Users

```text
organizations
users
user_sessions
user_identities
roles
permissions
role_permissions
user_roles
user_property_assignments
```

Purpose:

- Multi-client support.
- Organization isolation.
- Admin/property manager/maintenance staff roles.
- Future SSO support.
- Property-level access control.

### 9.2 External References

Every synced external record should have an external mapping.

```text
external_refs
- id
- organization_id
- source_system        // appfolio, twilio, gmail, manual, etc.
- source_entity_type   // property, unit, tenant, owner, vendor, work_order, email, sms
- source_entity_id
- internal_table
- internal_id
- source_url
- first_seen_at
- last_seen_at
- created_at
- updated_at
```

This allows idempotent sync and prevents duplicates.

### 9.3 Parties and Roles

```text
parties
- id
- organization_id
- party_type           // person, company
- display_name
- first_name
- last_name
- company_name
- primary_email
- primary_phone
- status
- created_at
- updated_at

party_roles
- id
- organization_id
- party_id
- role_type            // tenant, owner, homeowner, vendor, board_member, applicant, property_manager
- status
- start_date
- end_date
- metadata_json
- created_at
- updated_at
```

Why this matters:

- Avoid duplicate tenant/owner/vendor records for the same person.
- Allow future role changes.
- Support one person having multiple roles.

### 9.4 Properties and Units

```text
properties
- id
- organization_id
- name
- address_line_1
- address_line_2
- city
- state
- postal_code
- country
- property_type
- status
- created_at
- updated_at

units
- id
- organization_id
- property_id
- unit_number
- bedrooms
- bathrooms
- status
- created_at
- updated_at
```

For single-family properties, still create one internal default unit such as `MAIN` so the data model stays consistent.

### 9.5 Leases and Occupancy

```text
leases
- id
- organization_id
- property_id
- unit_id
- lease_status
- start_date
- end_date
- rent_amount
- deposit_amount
- metadata_json
- created_at
- updated_at

lease_parties
- id
- organization_id
- lease_id
- party_id
- relationship_type    // primary_tenant, co_tenant, occupant, guarantor
- is_financially_responsible
- start_date
- end_date
```

The lease is important because AI needs to understand tenant-specific rules and occupancy context.

### 9.6 Property Relationships

```text
property_party_relationships
- id
- organization_id
- property_id
- party_id
- relationship_type    // owner, homeowner, hoa_board, property_manager, asset_manager
- ownership_percentage
- start_date
- end_date
- metadata_json
```

This supports:

- One property with multiple owners.
- One owner with multiple properties.
- HOA/board relationships.
- Property manager assignment.

### 9.7 Vendors

```text
vendors
- id
- organization_id
- party_id
- trade_type           // plumbing, electrical, hvac, general, etc.
- status
- license_number
- insurance_expiry
- metadata_json
- created_at
- updated_at
```

Vendors are still parties, but vendor-specific fields belong in a vendor profile.

### 9.8 Work Orders

```text
work_orders
- id
- organization_id
- property_id
- unit_id
- lease_id nullable
- tenant_party_id nullable
- vendor_party_id nullable
- source_work_order_id
- title
- description
- category
- priority
- status
- version
- created_at_source
- updated_at_source
- completed_at_source nullable
- created_at
- updated_at
```

Work orders are one of the most important operational roots for AI.

### 9.9 Work Order Notes

```text
work_order_notes
- id
- organization_id
- work_order_id
- source_note_id
- author_party_id nullable
- body_text
- source_visibility      // from AppFolio if available
- derived_visibility     // internal, owner_only, shareable, unknown
- classifier_version
- classifier_reason
- created_at_source
- created_at
```

Important rule:

- Notes starting with `#` must be treated as internal/private unless explicitly overridden by an authorized workflow.
- Tenant/vendor replies must never include internal note content.

### 9.10 Messages / Communications

```text
messages
- id
- organization_id
- source                // appfolio_official, appfolio_unofficial, twilio, gmail, manual
- channel               // email, sms, note, call
- direction             // inbound, outbound
- from_party_id nullable
- to_party_id nullable
- property_id nullable
- unit_id nullable
- lease_id nullable
- work_order_id nullable
- subject nullable
- body_text
- sent_at
- status
- external_message_id
- raw_payload_id nullable
- created_at
- updated_at

message_matches
- id
- organization_id
- message_id
- work_order_id
- match_status          // auto_matched, low_confidence, manual_review, manually_matched, unmatched
- confidence_score
- match_reason
- matched_by nullable
- matched_at nullable
- created_at
```

Messages are essential for AI because they tell the system what the tenant/vendor/owner is asking now.

### 9.11 Documents and Attachments

```text
documents
- id
- organization_id
- source
- document_type         // lease_agreement, owner_statement, invoice, work_order_attachment, email_attachment
- property_id nullable
- unit_id nullable
- lease_id nullable
- party_id nullable
- work_order_id nullable
- file_url nullable
- extracted_text nullable
- metadata_json
- created_at
```

Documents can later improve AI context, especially lease agreements and work order attachments.

### 9.12 AI Recommendations

```text
ai_recommendations
- id
- organization_id
- work_order_id
- source_message_id nullable
- review_status         // queued, processing, ready_for_review, approved, rejected, failed
- audience              // tenant, vendor, owner, internal
- summary
- detected_intent
- recommended_action
- draft_reply
- confidence
- safety_flags_json
- source_context_used_json
- source_context_excluded_json
- model_provider
- model_name
- prompt_version
- error_message nullable
- version
- created_at
- updated_at

recommendation_revisions
- id
- organization_id
- recommendation_id
- revision_number
- draft_reply
- edited_by nullable
- edit_reason nullable
- created_at

approval_events
- id
- organization_id
- recommendation_id
- revision_id
- action                // approved, rejected, copied, manual_send_marked, regenerated
- actor_user_id
- reason nullable
- channel nullable
- external_reference nullable
- created_at
```

Editing, copying, and manual-send tracking should be immutable events, not simple mutable statuses.

### 9.13 Integration and Sync

```text
integration_connections
integration_cursors
integration_payloads
sync_runs
job_executions
outbox_events
audit_events
```

Purpose:

- Store connection status.
- Track cursor per entity.
- Store redacted raw payloads.
- Track every sync run.
- Retry failed jobs.
- Emit outbox events.
- Audit every important action.

---

## 10. AppFolio Sync Strategy

### 10.1 Phase 0 Discovery

Before assuming AppFolio capabilities, validate:

- What access method is available?
  - Official API?
  - Saved report export?
  - MAX/database export?
  - Browser session access?
- Which entities are available?
- Are email and SMS communication records accessible?
- Are work order notes accessible?
- Are attachments accessible?
- What are rate limits?
- What authentication method is allowed?
- What retention period is available?
- What fields are stable IDs?

### 10.2 Source Priority

Use this source priority:

```text
1. Official AppFolio API or official saved reports
2. Approved AppFolio exports/reports
3. Fallback email/SMS webhooks if communication is not available
4. Optional unofficial browser/cookie connector only as an experimental bonus, not contractual core
```

The unofficial connector should be:

- Disabled by default.
- Feature-flagged.
- Used only with explicit client authorization.
- Used only for missing data such as email/SMS communication if official paths do not provide it.
- Not the primary source for core master data.
- Not promised as a contractual dependency unless legal/security review approves it.

### 10.3 Sync Order

Initial full sync should happen in this order:

```text
1. Organizations / integration connection
2. Properties
3. Units
4. Parties / contacts
   - Tenants
   - Owners
   - Homeowners
   - Vendors
   - Applicants if needed
5. Leases / occupancy
6. Property-party relationships
7. Work orders
8. Work order notes
9. Work order attachments / document references
10. Communications: email, SMS, AppFolio messages
11. Message-to-work-order matching
12. AI recommendation queue
13. Search/vector/index updates if needed later
```

### 10.4 Incremental Sync

Each entity type should have an independent cursor.

Example cursor keys:

```text
appfolio.properties
appfolio.units
appfolio.parties
appfolio.leases
appfolio.work_orders
appfolio.work_order_notes
appfolio.attachments
appfolio.messages
```

Each sync page should:

1. Create or update a `sync_runs` record.
2. Read the last cursor.
3. Fetch one page from the source.
4. Store raw payload or redacted raw payload metadata.
5. Normalize source records.
6. Upsert normalized records transactionally.
7. Write audit/outbox events for meaningful changes.
8. Advance cursor only after successful persistence.
9. Record counts, errors, and duration.

### 10.5 Idempotency

All sync operations must be idempotent.

Use unique constraints like:

```text
unique(organization_id, source_system, source_entity_type, source_entity_id)
```

Do not create duplicates if the same AppFolio page is fetched twice.

### 10.6 Partial Failure

If one record fails:

- Record the failure.
- Do not corrupt the cursor.
- Continue safely if possible.
- Retry according to policy.
- Send repeated failures to DLQ.
- Show failure reason in sync health.

---

## 11. AppFolio Connector Interface

The Go backend should define a provider-neutral interface.

Example conceptual interface:

```go
type AppFolioClient interface {
    FetchProperties(ctx context.Context, cursor SyncCursor) (Page[SourceProperty], error)
    FetchUnits(ctx context.Context, cursor SyncCursor) (Page[SourceUnit], error)
    FetchContacts(ctx context.Context, cursor SyncCursor) (Page[SourceContact], error)
    FetchLeases(ctx context.Context, cursor SyncCursor) (Page[SourceLease], error)
    FetchWorkOrders(ctx context.Context, cursor SyncCursor) (Page[SourceWorkOrder], error)
    FetchWorkOrderNotes(ctx context.Context, cursor SyncCursor) (Page[SourceWorkOrderNote], error)
    FetchMessages(ctx context.Context, cursor SyncCursor) (Page[SourceMessage], error)
    FetchAttachments(ctx context.Context, cursor SyncCursor) (Page[SourceAttachment], error)
    Capabilities(ctx context.Context) (AppFolioCapabilities, error)
}
```

Capabilities should include:

```text
can_read_properties
can_read_units
can_read_tenants
can_read_owners
can_read_vendors
can_read_work_orders
can_read_work_order_notes
can_read_messages
can_read_attachments
can_write_back_notes
can_send_messages
```

For Phase 1, even if the source supports sending, the product must not expose automatic outbound sending.

---

## 12. AI Recommendation Workflow

The AI flow should be deterministic around data access and safety.

```text
1. Message or work order changes.
2. Worker queues recommendation generation.
3. Load work order with organization and property access policy.
4. Load related property, unit, lease, parties, vendor, owner context.
5. Load notes and messages.
6. Split context into:
   - manager-visible context
   - audience-shareable context
   - excluded/private context
7. Classify notes:
   - # notes
   - internal notes
   - owner-only notes
   - unknown visibility notes
   - shareable notes
8. Build structured prompt with source references.
9. Call AI provider.
10. Parse structured output.
11. Run deterministic safety checks.
12. Persist recommendation and source references.
13. Set status to ready_for_review or failed.
14. Manager reviews, edits, approves, rejects, copies, and marks manually sent.
15. Audit all actions.
```

### 12.1 AI Output Must Include

```text
summary
intent
recommended_action
audience
draft_reply
confidence
safety_flags
source_context_used
source_context_excluded
```

### 12.2 Supported Intents

```text
asking_eta
requesting_update
reporting_new_issue
confirming_schedule
cost_approval
vendor_follow_up
urgency_escalation
general_update
```

### 12.3 AI Must Not

- Send messages automatically.
- Include internal `#` notes in tenant/vendor drafts.
- Invent vendor ETA.
- Invent appointment confirmation.
- Invent completion status.
- Invent cost approval.
- Make legal, insurance, or liability claims.
- Expose owner-only or internal context to tenant/vendor audience.
- Use data the user is not authorized to access.

---

## 13. Context Separation Rules

The service must not rely only on the AI model to hide sensitive information.

The backend must filter context before prompt construction.

### 13.1 Manager-Visible Context

May include:

- Work order details.
- Tenant/vendor/owner context allowed by user role.
- Internal notes if the manager is authorized.
- Owner-only context if authorized.
- Source message history.
- AI safety flags.
- Excluded context summary.

### 13.2 Tenant/Vendor-Shareable Context

May include:

- Public work order status.
- Safe summary of what is happening.
- Confirmed facts only.
- Approved appointment details only if present in source.
- Approved vendor updates only if present in source.

Must exclude:

- `#` notes.
- Internal staff notes.
- Owner-only notes.
- Private owner data.
- Unverified estimates.
- Cost approvals unless explicitly confirmed and shareable.
- Legal/liability interpretation.

---

## 14. Human-in-the-Loop Workflow

Phase 1 is strictly human-reviewed.

Recommended status flow:

```text
queued
  -> processing
  -> ready_for_review
  -> approved
  -> copied
  -> manual_send_marked

queued
  -> processing
  -> failed

ready_for_review
  -> rejected

ready_for_review
  -> regenerated
```

Implementation detail:

- `review_status` should track major workflow state.
- Edits, copy events, manual-send events, approvals, rejections, and regenerations should be immutable events.
- Copy should be available only after approval.
- Manual-send mark should be available only after approval or copy.
- No production `Send` button in Phase 1.

---

## 15. API Scope

Use public prefix:

```text
/api/v1
```

### 15.1 Health

```text
GET /health/live
GET /health/ready
```

### 15.2 Auth and User Management

```text
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/password/forgot
POST /api/v1/auth/password/reset
GET  /api/v1/users
POST /api/v1/users
POST /api/v1/users/invitations
PATCH /api/v1/users/{id}
PUT /api/v1/users/{id}/roles
PUT /api/v1/users/{id}/property-assignments
```

### 15.3 Portfolio

```text
GET /api/v1/properties
GET /api/v1/properties/{id}
GET /api/v1/properties/{id}/units
GET /api/v1/tenants
GET /api/v1/owners
GET /api/v1/vendors
```

### 15.4 Work Orders

```text
GET /api/v1/work-orders
GET /api/v1/work-orders/{id}
GET /api/v1/work-orders/{id}/timeline
GET /api/v1/work-orders/{id}/notes
GET /api/v1/work-orders/{id}/messages
```

### 15.5 Messages

```text
GET  /api/v1/messages/unmatched
POST /api/v1/messages/{id}/match
POST /api/v1/messages/{id}/unmatch
```

### 15.6 Recommendations

```text
GET   /api/v1/recommendations
GET   /api/v1/recommendations/{id}
POST  /api/v1/recommendations/{id}/regenerate
PATCH /api/v1/recommendations/{id}/draft
POST  /api/v1/recommendations/{id}/approve
POST  /api/v1/recommendations/{id}/reject
POST  /api/v1/recommendations/{id}/copy-events
POST  /api/v1/recommendations/{id}/manual-send-events
```

### 15.7 Sync and Audit

```text
GET  /api/v1/sync-runs
GET  /api/v1/sync-runs/{id}
POST /api/v1/sync-runs
GET  /api/v1/integration-health
GET  /api/v1/audit-events
```

---

## 16. Worker Jobs

The worker should process queue jobs, not HTTP internal job endpoints as the main architecture.

Recommended jobs:

```text
appfolio_sync_entity
appfolio_sync_full
message_match
recommendation_generate
recommendation_regenerate
stale_vendor_check
attachment_metadata_sync
```

Standard queue payload:

```json
{
  "schema_version": 1,
  "job_id": "uuid",
  "job_type": "generate_recommendation",
  "organization_id": "uuid",
  "idempotency_key": "string",
  "correlation_id": "uuid",
  "requested_by": "user-or-service-id",
  "payload": {}
}
```

Each job should:

- Validate organization.
- Run under a service actor.
- Use idempotency key.
- Track execution attempts.
- Use retry with backoff.
- Send exhausted failures to DLQ.
- Write audit/outbox events where relevant.

---

## 17. Suggested Repository Structure

```text
apps/api/
├── cmd/
│   ├── api/main.go
│   └── worker/main.go
├── internal/
│   ├── platform/
│   │   ├── config/
│   │   ├── database/
│   │   ├── httpserver/
│   │   ├── queue/
│   │   ├── logging/
│   │   └── observability/
│   ├── auth/
│   ├── authorization/
│   ├── audit/
│   ├── organizations/
│   ├── users/
│   ├── properties/
│   ├── contacts/
│   ├── leases/
│   ├── workorders/
│   ├── messages/
│   ├── recommendations/
│   ├── integrations/
│   │   └── appfolio/
│   ├── ai/
│   └── jobs/
├── db/
│   ├── migrations/
│   ├── queries/
│   └── generated/
├── api/
│   └── openapi.yaml
└── test/
```

Module rules:

- Handlers validate HTTP input only.
- Services own business logic, transactions, state transitions, and authorization.
- Repositories own persistence.
- Policies run before returning data or building AI context.
- Workers call services directly.
- OpenAPI is the contract for frontend clients.

---

## 18. Authentication and Authorization

Phase 1 should include:

- Email/password auth.
- Admin-created invitations.
- Opaque cookie sessions.
- Hashed session tokens in database.
- CSRF protection for cookie-authenticated mutations.
- Logout and session revocation.
- Password reset.
- Account disabling.
- Login throttling.

Initial roles:

```text
admin
property_manager
maintenance_staff
```

Initial permissions:

```text
work_order.read
work_order.review
recommendation.generate
recommendation.edit
recommendation.approve
recommendation.reject
audit.read
sync.manage
organization.manage
user.manage
```

Every service method should accept an actor context:

```text
ActorContext
- user_id
- organization_id
- roles
- permissions
- property_assignments
- auth_method
- request_id
- correlation_id
```

---

## 19. Tenant Isolation

Every tenant-owned table must include:

```text
organization_id
```

Rules:

- Every query must filter by organization.
- Every worker job must carry organization ID.
- Every queue message must validate organization ID.
- PostgreSQL RLS should provide defense in depth.
- Composite foreign keys should prevent cross-organization relationships.
- Tests must attempt cross-organization reads/writes.

---

## 20. Observability and Audit

The service must track:

- API errors.
- Request latency.
- Sync success/failure.
- Sync duration.
- Records processed.
- Queue depth.
- DLQ count.
- AI generation latency.
- AI failure count.
- Safety flags.
- Unmatched messages.
- Review backlog.
- Database health.

Audit events should record:

- Organization.
- Actor.
- Action.
- Resource.
- Before/after snapshot where useful.
- Request ID.
- Correlation ID.
- IP/user agent for HTTP actions.
- Timestamp.
- Metadata.

Never log:

- Passwords.
- Session tokens.
- Secrets.
- Full raw PII payloads.
- Full message bodies unless explicitly stored in protected domain tables.

---

## 21. Phased Implementation Plan

### Phase 0 — Discovery and Access Validation

Deliverables:

- Confirm AppFolio access method.
- Confirm available entities.
- Confirm whether inbound emails/SMS are accessible.
- Confirm attachment availability.
- Confirm rate limits.
- Confirm authentication method.
- Build sample payload fixtures.

### Phase 1A — Backend Foundation

Deliverables:

- Go module in `apps/api`.
- API and worker binaries.
- Config system.
- Logging.
- Health endpoints.
- Error format.
- PostgreSQL connection.
- Migration setup.
- OpenAPI skeleton.

### Phase 1B — Database and Tenancy

Deliverables:

- Organization schema.
- Users and auth tables.
- RBAC tables.
- Property/unit/party/work-order/message/recommendation tables.
- External refs.
- Sync tables.
- Audit/outbox tables.
- RLS and tenant-isolation tests.

### Phase 1C — AppFolio Sync Spine

Deliverables:

- AppFolio connector interface.
- Fake connector.
- Entity normalizers.
- Idempotent upserts.
- Sync cursor handling.
- Sync run tracking.
- Queue job contracts.
- DLQ behavior.

### Phase 1D — Maintenance Read Model

Deliverables:

- Work order list API.
- Work order detail API.
- Timeline API.
- Notes/messages API.
- Property/tenant/vendor/owner lookup APIs.
- Pagination, filtering, sorting.

### Phase 1E — AI Recommendation Pipeline

Deliverables:

- Context builder.
- Internal/shareable context splitter.
- `#` note classifier.
- Prompt builder.
- AI provider interface.
- Structured output parser.
- Safety checker.
- Recommendation persistence.
- Regenerate/edit/approve/reject/copy/manual-send workflow.

### Phase 1F — Production Hardening

Deliverables:

- Monitoring.
- Alarms.
- Runbooks.
- Backup/restore test.
- Security review.
- UAT fixes.
- Deployment pipeline.

---

## 22. Acceptance Criteria

The backend service is acceptable when:

- Properties, units, people, leases, work orders, notes, vendors, owners, tenants, and messages can be synced or loaded from fixtures.
- Sync is idempotent.
- Raw source payloads are stored or traceable.
- AppFolio cursor per entity is tracked.
- Work orders are visible in the API.
- Work order detail returns linked property, unit, tenant, vendor, owner, notes, and messages where available.
- Inbound messages can be matched to work orders.
- Low-confidence matches enter manual review.
- AI can generate summary, intent, recommended action, and draft reply.
- Tenant/vendor drafts exclude `#`, owner-only, and internal notes.
- AI safety checks block or flag risky drafts.
- Property managers can edit, approve, reject, copy, and mark manually sent.
- Copy/manual-send actions are blocked before approval.
- No automatic outbound email/SMS exists in Phase 1.
- Audit log records every recommendation workflow transition.
- Organization isolation is tested.
- Sync failures, AI failures, and queue failures are observable.

---

## 23. Important Risks

### 23.1 AppFolio Access Risk

AppFolio access may be limited. Build the connector using interfaces, fake fixtures, and capability flags before depending on a specific API.

### 23.2 Communication Access Risk

Email/SMS may not be available through official AppFolio access. If missing, consider fallback inbound email/SMS or experimental browser connector, but do not make unofficial scraping the contractual foundation.

### 23.3 Internal Note Leakage Risk

This is a high-risk area. Context filtering must happen before the AI prompt is built.

### 23.4 AI Hallucination Risk

AI must not invent ETA, cost approval, completion, appointment, legal, insurance, or liability claims. Deterministic safety checks must run after AI output.

### 23.5 Workflow Reliability Risk

Approval workflow must live in backend/database, not only frontend state.

---

## 24. Codex Prompt to Build the Backend

Copy and paste this prompt into Codex when you want it to start implementation.

```text
You are a senior backend architect and senior Go engineer. Build the backend foundation for an AppFolio Sync + AI Maintenance Assistant service.

Business goal:
We need a backend service that can pull/sync all available AppFolio property-management data into our own database, normalize it, link all related context, and use AI to help property managers respond faster to maintenance messages. The AI must summarize, classify intent, recommend next action, and draft a reply, but humans must review and approve. Phase 1 must never automatically send outbound email/SMS.

Repository direction:
- Keep the existing Next.js dashboard.
- Build production backend in apps/api.
- Use Go as the core backend language.
- Use Echo for HTTP routing.
- Use PostgreSQL with pgx, sqlc, and forward-only migrations.
- Create two binaries: cmd/api and cmd/worker.
- Use OpenAPI as the frontend/backend contract.
- Use a modular monolith structure, not microservices.

Architecture:
- API service handles dashboard requests.
- Worker service handles AppFolio sync, message matching, AI recommendation generation, and stale vendor checks.
- PostgreSQL stores normalized product data, external refs, raw payload references, sync runs, recommendations, approvals, audit events, and outbox events.
- AppFolio integration must be provider-neutral and capability-based.
- AI provider must be provider-neutral.
- Do not implement outbound sending in Phase 1.

Core data model:
Use Property/Unit/Lease as the operational context root and Party as the identity root.
Implement tables or migrations for:
- organizations
- users
- sessions/invitations/password reset basics if implementing auth now
- roles, permissions, role_permissions, user_roles, user_property_assignments
- external_refs
- parties
- party_roles
- properties
- units
- leases
- lease_parties
- property_party_relationships
- vendors
- work_orders
- work_order_notes
- work_order_attachments or documents
- messages
- message_matches
- ai_recommendations
- recommendation_revisions
- approval_events
- integration_connections
- integration_cursors
- integration_payloads
- sync_runs
- job_executions
- audit_events
- outbox_events

Important data rules:
- Every tenant-owned table must include organization_id.
- Every query must be organization-scoped.
- Use unique external refs for idempotent sync.
- Use optimistic concurrency/versioning for work orders and recommendations.
- Store source visibility and derived visibility for notes separately.
- Notes starting with # must be treated as internal/private.
- JSONB is okay for raw payloads, metadata, source context references, safety flags, and immutable snapshots, but not for core relational fields.

AppFolio sync requirements:
- Define an AppFolioClient interface for properties, units, contacts, leases, work orders, notes, messages, and attachments.
- Implement a fake connector using fixtures first.
- Do not assume the exact AppFolio API shape yet.
- Add capability flags for each entity and write-back/send behavior.
- Implement idempotent normalizers and upserts.
- Track cursor per entity.
- Create sync_runs rows.
- Store raw/redacted payload metadata.
- Advance cursors only after successful persistence.
- Retry rate limits with exponential backoff and jitter.
- Do not blindly retry auth failures.
- Keep fallback email/SMS and unofficial browser connector disabled by default.

AI recommendation requirements:
- Build manager-visible and audience-shareable context separately.
- Filter unauthorized/private context before prompt construction.
- Exclude # notes, internal notes, and owner-only notes from tenant/vendor draft prompts.
- Create an AI provider interface.
- Generate structured output: summary, detected_intent, recommended_action, audience, draft_reply, confidence, safety_flags, source_context_used, source_context_excluded.
- Validate AI output schema.
- Run deterministic safety checks.
- Flag or fail drafts that leak internal content, invent ETA/completion/appointment/cost approval/liability, lack source grounding, or mismatch audience.
- Persist recommendation with model metadata and prompt version.
- No provider/service interface should expose outbound send in Phase 1.

Workflow requirements:
- Recommendation review statuses: queued, processing, ready_for_review, approved, rejected, failed.
- Edits, approvals, rejections, copy events, manual-send marks, and regenerations must be immutable events.
- Copy approved draft should be blocked until approval.
- Manual-send mark should be blocked until approval/copy.
- Rejection requires reason.
- Mutating workflow endpoints should support idempotency keys and expected_version.

API requirements:
Use /api/v1 prefix. Implement or scaffold:
- GET /health/live
- GET /health/ready
- GET /api/v1/properties
- GET /api/v1/properties/{id}
- GET /api/v1/properties/{id}/units
- GET /api/v1/tenants
- GET /api/v1/owners
- GET /api/v1/vendors
- GET /api/v1/work-orders
- GET /api/v1/work-orders/{id}
- GET /api/v1/work-orders/{id}/timeline
- GET /api/v1/work-orders/{id}/notes
- GET /api/v1/work-orders/{id}/messages
- GET /api/v1/messages/unmatched
- POST /api/v1/messages/{id}/match
- POST /api/v1/messages/{id}/unmatch
- GET /api/v1/recommendations
- GET /api/v1/recommendations/{id}
- POST /api/v1/recommendations/{id}/regenerate
- PATCH /api/v1/recommendations/{id}/draft
- POST /api/v1/recommendations/{id}/approve
- POST /api/v1/recommendations/{id}/reject
- POST /api/v1/recommendations/{id}/copy-events
- POST /api/v1/recommendations/{id}/manual-send-events
- GET /api/v1/audit-events
- GET /api/v1/sync-runs
- GET /api/v1/sync-runs/{id}
- POST /api/v1/sync-runs
- GET /api/v1/integration-health

API standards:
- JSON uses snake_case.
- Timestamps use RFC3339 UTC.
- Collections return items and next_cursor.
- Use cursor pagination.
- Use RFC 9457 problem-details style errors.
- Include X-Request-ID.
- Use allow-listed sorting/filtering.
- Never return cross-organization data.

Testing requirements:
Add tests for:
- AppFolio normalization.
- Idempotent sync.
- Cursor resumption.
- Duplicate pages.
- Partial failure.
- Rate-limit retry decisions.
- RBAC and property assignment boundaries.
- Tenant isolation and cross-org attack attempts.
- # note classification.
- Internal/shareable context splitter.
- AI output validation.
- Internal-note leak attempts.
- Hallucinated ETA/cost/completion checks.
- Recommendation state transitions.
- Copy/manual-send gating.
- Audit event creation.

Implementation order:
1. Create Go module and folder structure in apps/api.
2. Add config, logging, request IDs, health endpoints, error handling, and OpenAPI skeleton.
3. Add PostgreSQL migrations for organization, external refs, portfolio, work order, messages, recommendations, sync, audit, and jobs.
4. Add sqlc queries and repositories.
5. Add fake AppFolio connector and fixture-based sync.
6. Add worker job framework with in-memory/local queue adapter first, then SQS abstraction.
7. Add work order list/detail/timeline APIs.
8. Add message matching APIs.
9. Add AI provider interface with fake provider first.
10. Add context builder, safety checker, and recommendation persistence.
11. Add recommendation review workflow APIs.
12. Add audit and sync health APIs.
13. Add tests for acceptance criteria.

Do not:
- Build a tenant-facing chatbot in Phase 1.
- Add automatic outbound sending.
- Trust the AI model to hide private context.
- Hard-code AppFolio API assumptions before discovery.
- Put production workflow state only in frontend/client memory.
- Create duplicate tenant/owner/vendor people records when one Party with roles can represent them.

Deliver high-quality, maintainable code with clear module boundaries, tests, and comments where helpful.
```

---

## 25. Implementation Notes for the Team

### Recommended First PR

The first PR should not try to implement the full product.

First PR should include:

- Go service skeleton.
- API and worker entrypoints.
- Config and logging.
- Health endpoints.
- Database connection.
- Migration tool setup.
- OpenAPI skeleton.
- Basic CI test command.

### Recommended Second PR

Second PR should include:

- Organization schema.
- External refs.
- Properties/units/parties/work_orders schema.
- Fake AppFolio connector.
- Sync run creation.
- Fixture-based property/unit/work-order sync.

### Recommended Third PR

Third PR should include:

- Work order list/detail/timeline API.
- Notes and messages schema.
- Message matching skeleton.
- Audit events.

### Recommended Fourth PR

Fourth PR should include:

- AI context builder.
- Internal/shareable splitter.
- `#` note classifier.
- Fake AI provider.
- Recommendation generation job.

### Recommended Fifth PR

Fifth PR should include:

- Recommendation review workflow.
- Edit/approve/reject/copy/manual-send events.
- Safety tests.
- End-to-end fixture test.

---

## 26. Final Architecture Principle

The product should be designed around this simple truth:

```text
AppFolio is the source system.
Our database is the operational AI context store.
AI is the assistant.
The property manager is the decision maker.
Audit is the trust layer.
```

