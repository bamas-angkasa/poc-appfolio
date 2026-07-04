Yes — as PM, I would **not** plan this as “build backend first, then maybe show UI later.”
The better plan is **impact-driven vertical phases**, so every phase gives Caleb/property managers something visible and valuable.

Your product goal is: **pull AppFolio data, organize it into our system, let AI understand the maintenance/property context, and help property managers reply faster with human approval.** This aligns with the PRD: internal maintenance inbox, AppFolio sync, AI recommendations, safety checks, approval workflow, copy-ready draft, audit log, sync health, and no automatic outbound sending in Phase 1. 

# Project Delivery Phases

## Phase 0 — Discovery & AppFolio Access Validation

**Goal:** Confirm what data we can really get from AppFolio before overbuilding.

**Business impact:**
Reduces integration risk. We will know whether we can get work orders, tenants, owners, vendors, notes, messages, attachments, and IDs from official API, saved reports, or unofficial cookie-based scraping.

**Deliverables:**

| Deliverable            | Description                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------- |
| AppFolio access report | What data is available from official API, saved reports, export, or unofficial API |
| Entity mapping         | AppFolio fields mapped to our internal schema                                      |
| Data gap report        | What official API cannot provide, especially email/SMS                             |
| Sync source decision   | Official API first, unofficial connector only for missing email/SMS                |
| Security/risk note     | Cookie-based scraper is experimental/bonus, not main contract dependency           |

**Acceptance criteria:**

* We know the source for each required entity.
* We know which data is available through official API/report.
* We know whether email/SMS must use unofficial API.
* We can show Caleb a simple “what data we can pull” table.

---

## Phase 1 — Backend Foundation + Canonical Data Model

**Goal:** Build the stable backend structure where all AppFolio data will live.

**Business impact:**
Creates the foundation for future AI, dashboard, audit, and sync. This phase is mostly technical, but it protects us from messy data later.

The backend foundation plan already recommends Go/Echo, PostgreSQL, API + worker binaries, RBAC, RLS, audit, provider-neutral AppFolio and AI adapters, and no outbound messaging in Phase 1. 

**Deliverables:**

| Deliverable              | Description                                                                            |
| ------------------------ | -------------------------------------------------------------------------------------- |
| Go backend skeleton      | `api` service and `worker` service                                                     |
| PostgreSQL schema        | Organization, property, unit, party, lease, work order, message, recommendation tables |
| External reference table | Map AppFolio IDs to our internal IDs                                                   |
| RBAC foundation          | Admin, property manager, maintenance staff                                             |
| Audit foundation         | Track important actions from day one                                                   |
| OpenAPI contract         | Backend/frontend API contract                                                          |

**Core data model decision:**

```txt
Property / Unit / Lease = operational context root
Party = identity root
Work Order = maintenance case root
Communication = conversation timeline
AI Recommendation = decision support layer
```

**Acceptance criteria:**

* Backend runs locally.
* Database migrations work.
* Seed data exists.
* API health endpoint works.
* Basic property/work-order data can be inserted and queried.
* Every tenant-owned record has `organization_id`.

---

## Phase 2 — AppFolio Sync MVP

**Goal:** Pull the first useful AppFolio data into our database.

**Business impact:**
This is the first phase where we can prove: “We can get AppFolio data into our own system.”

**Deliverables:**

| Deliverable                  | Description                                                       |
| ---------------------------- | ----------------------------------------------------------------- |
| AppFolio connector interface | Provider-neutral interface, so official/unofficial source can fit |
| Property sync                | Pull properties                                                   |
| Unit sync                    | Pull units                                                        |
| People sync                  | Pull tenants, owners, vendors, homeowners if available            |
| Work order sync              | Pull active maintenance work orders                               |
| Notes sync                   | Pull work order notes                                             |
| Raw payload storage          | Store source payload for traceability/debugging                   |
| Sync cursors                 | Incremental sync support                                          |
| Sync run logs                | Success/failure/count/duration tracking                           |

**Important rule:**
Use the **official API/report sync as primary**, and only use the unofficial cookie-based connector for missing communication data such as email/SMS.

**Acceptance criteria:**

* Worker can run sync manually.
* Data is inserted idempotently, meaning duplicate sync does not create duplicate records.
* AppFolio IDs are mapped to internal IDs.
* Work orders are linked to property, unit, tenant, vendor, and owner context where available.
* Sync status is visible through API.

**Demo to Caleb:**

```txt
“Here is AppFolio data pulled into our database.
We can see property, unit, tenant, vendor, owner, and work order context linked together.”
```

---

## Phase 3 — Maintenance Inbox Read-Only Dashboard

**Goal:** Give property managers one place to see synced maintenance cases.

**Business impact:**
Even without AI, this already saves time because managers do not need to jump across AppFolio screens.

**Deliverables:**

| Deliverable                | Description                                                  |
| -------------------------- | ------------------------------------------------------------ |
| Maintenance inbox API      | List work orders                                             |
| Work order detail API      | Full context for one work order                              |
| Timeline API               | Notes, messages, status changes, sync events                 |
| Basic frontend integration | Dashboard uses real backend data                             |
| Filters                    | Ready for review, urgent, waiting vendor, stale, failed sync |
| Sync health view           | Show last sync, records processed, errors                    |

**Acceptance criteria:**

* Property manager can open inbox.
* Manager can click a work order.
* Detail page shows property, unit, tenant, vendor, owner context, notes, and timeline.
* No AI yet required.
* No send button exists.

**Demo to Caleb:**

```txt
“Now property managers can see all synced maintenance context in one dashboard.”
```

---

## Phase 4 — Communication Sync + Message Matching

**Goal:** Bring in email/SMS/message context and connect it to work orders.

**Business impact:**
This is where the product becomes much more valuable because AI needs the latest communication to understand what the tenant/vendor is asking.

**Deliverables:**

| Deliverable                      | Description                                       |
| -------------------------------- | ------------------------------------------------- |
| AppFolio communication sync      | Pull email/SMS if available                       |
| Unofficial connector integration | Optional, only for missing AppFolio communication |
| Message table                    | Store inbound/outbound email/SMS records          |
| Message matching engine          | Match message to property/unit/tenant/work order  |
| Confidence score                 | High/medium/low match                             |
| Manual matching UI/API           | Manager can link unmatched message                |
| Audit on match changes           | Track manual correction                           |

**Acceptance criteria:**

* Email/SMS records are stored.
* Messages are linked to work orders when possible.
* Low-confidence messages appear in “Needs manual matching.”
* Manager can manually match a message.
* Matched message queues AI recommendation generation.

**Demo to Caleb:**

```txt
“Now the system can detect which tenant/vendor message belongs to which work order.”
```

---

## Phase 5 — AI Recommendation Pipeline

**Goal:** Use AI to summarize the case, detect intent, recommend next action, and draft a reply.

**Business impact:**
This is the first major AI value moment: property managers can respond faster.

The backend plan defines the AI pipeline as loading work-order context, separating manager-visible and shareable context, excluding restricted notes, building a structured prompt, invoking a model provider, validating output, running safety checks, and moving the recommendation to `ready_for_review` or `failed`. 

**Deliverables:**

| Deliverable                 | Description                                        |
| --------------------------- | -------------------------------------------------- |
| Context builder             | Build full work order context                      |
| Internal/shareable splitter | Separate private notes from reply-safe context     |
| `#` note classifier         | Mark internal-only notes                           |
| Prompt builder              | Structured prompt for AI                           |
| AI provider abstraction     | Claude/OpenAI/etc can be swapped                   |
| Recommendation generator    | Summary, intent, action, draft reply               |
| Safety checker              | Prevent internal leaks, fake ETA, liability claims |
| Recommendation persistence  | Store AI output, sources, confidence, flags        |

**AI output should include:**

```txt
Summary
Detected intent
Recommended action
Draft reply
Audience
Confidence
Safety flags
Source context used
Source context excluded
```

**Acceptance criteria:**

* AI can generate recommendation for a synced work order.
* Draft reply excludes `#` internal notes.
* Draft does not invent ETA, cost approval, completion, or appointment confirmation.
* AI failure becomes visible as `failed`, not silent.
* AI never sends anything automatically.

**Demo to Caleb:**

```txt
“Here is a real work order. AI reads the synced context and drafts a safe reply for the manager to review.”
```

---

## Phase 6 — Human Approval Workflow

**Goal:** Let property managers edit, approve, reject, copy, and mark manually sent.

**Business impact:**
This turns AI from a demo into a usable operations workflow.

**Deliverables:**

| Deliverable                 | Description                                                 |
| --------------------------- | ----------------------------------------------------------- |
| Recommendation review panel | Show AI summary, draft, safety flags                        |
| Edit draft                  | Manager can modify AI draft                                 |
| Approve/reject              | Human decision required                                     |
| Copy approved draft         | Copy is only available after approval                       |
| Mark manually sent          | Track that manager sent through AppFolio/email/SMS manually |
| Revision history            | Store original draft and edited version                     |
| Approval events             | Store who approved/rejected and when                        |

**Important Phase 1 rule:**

```txt
No automatic outbound email/SMS.
No production Send button.
Only Copy Approved Draft + Mark Manually Sent.
```

**Acceptance criteria:**

* Manager can edit AI draft.
* Manager can approve or reject.
* Copy is blocked until approved.
* Manual-send tracking is blocked until approval/copy.
* Audit records original AI draft, edited draft, approval/rejection, copy, and manual-send event.

**Demo to Caleb:**

```txt
“AI helps draft the reply, but the property manager stays in control.”
```

---

## Phase 7 — Audit, Monitoring, and Sync Health

**Goal:** Make the system trustworthy and supportable.

**Business impact:**
This helps convince the client the product is safe for real operations, not just a prototype.

**Deliverables:**

| Deliverable           | Description                                             |
| --------------------- | ------------------------------------------------------- |
| Audit log UI/API      | View AI, sync, approval, edit, copy, manual-send events |
| Sync health dashboard | Last sync, errors, record count, duration               |
| Queue monitoring      | Failed jobs, retry count, DLQ visibility                |
| AI monitoring         | Success/failure, latency, safety flags                  |
| Error visibility      | Clear failed sync/AI status                             |
| Runbook               | What to do when sync or AI fails                        |

**Acceptance criteria:**

* Admin can see sync runs.
* Admin can see audit events.
* Failed sync is visible.
* Failed AI recommendation is visible.
* Every important workflow transition has an audit event.

**Demo to Caleb:**

```txt
“Every AI recommendation and manager action is traceable.”
```

---

## Phase 8 — UAT + Production Hardening

**Goal:** Prepare for staging/production with real users.

**Business impact:**
This makes the product ready for client validation and controlled rollout.

**Deliverables:**

| Deliverable                | Description                                 |
| -------------------------- | ------------------------------------------- |
| Staging deployment         | Real environment for Caleb/team testing     |
| Production deployment plan | Infrastructure, secrets, backups            |
| Security review            | Auth, RBAC, secret handling, webhook safety |
| Backup/restore test        | Database recovery confidence                |
| UAT feedback cycle         | Fix client feedback                         |
| Performance check          | Inbox/detail/API load target                |
| Final acceptance checklist | Ready for Phase 1 handoff                   |

**Acceptance criteria:**

* Staging works with real or realistic data.
* Client can test full golden flow.
* No internal-note leak in test cases.
* No automated outbound send exists.
* Monitoring is active.
* UAT issues are tracked and resolved/prioritized.

---

# Recommended Delivery Order

I would prioritize like this:

```txt
Phase 0: Discovery & AppFolio access validation
Phase 1: Backend foundation + canonical schema
Phase 2: AppFolio sync MVP
Phase 3: Read-only maintenance inbox
Phase 4: Communication sync + message matching
Phase 5: AI recommendation pipeline
Phase 6: Human approval workflow
Phase 7: Audit, monitoring, sync health
Phase 8: UAT + production hardening
```

# MVP “Golden Flow”

The most impactful MVP flow should be:

```txt
1. Sync AppFolio work order
2. Link property, unit, tenant, vendor, owner, notes, and messages
3. Show work order in maintenance inbox
4. Manager opens work order detail
5. AI summarizes issue and drafts reply
6. AI excludes internal / # notes
7. Manager edits and approves
8. Manager copies approved draft
9. Manager sends manually outside system
10. Manager marks manually sent
11. Audit log records everything
```

This is the core product. Everything else should support this flow.

# Phase Priority by Business Value

| Priority | Phase                 | Why it matters                              |
| -------- | --------------------- | ------------------------------------------- |
| P0       | Discovery             | Prevents wrong integration assumptions      |
| P0       | AppFolio sync         | Without data, AI has no value               |
| P0       | Maintenance inbox     | First visible operational value             |
| P0       | AI recommendation     | Main value proposition                      |
| P0       | Human approval        | Required for safety and trust               |
| P1       | Message matching      | Needed for communication-heavy workflow     |
| P1       | Audit log             | Required for client trust                   |
| P1       | Sync health           | Required for production operations          |
| P2       | Advanced automation   | Future phase only                           |
| P2       | AppFolio write-back   | Only after entitlement and safety confirmed |
| P2       | Tenant-facing chatbot | Future, not Phase 1                         |

# Suggested Milestone Definition

For project tracking, I would group the work into these milestones:

| Milestone | Name                  | Outcome                               |
| --------- | --------------------- | ------------------------------------- |
| M0        | Data Access Confirmed | We know what AppFolio can provide     |
| M1        | Data Foundation Ready | Backend and database are ready        |
| M2        | First Sync Working    | AppFolio data is in our database      |
| M3        | Inbox Usable          | Manager can view maintenance cases    |
| M4        | AI Draft Working      | AI can summarize and draft replies    |
| M5        | Review Workflow Ready | Manager can approve/copy/manual-send  |
| M6        | Production Candidate  | Audit, monitoring, staging, UAT ready |
