# Vehicentric

## AI-assisted lead follow-up workspace for used-car sales.

**Tagline:** Recover missed leads. Make every next step count.

Vehicentric is an internal workspace for used-car sales teams. It helps staff review overdue buyer enquiries, check vehicle and appointment details, and act on the right follow-up.

Its AI agent, **Agent Idaten**, reads the lead history, checks current business records, looks up the relevant sales procedure, and proposes one specific action:

- **Create a follow-up task** for a salesperson, such as checking whether the buyer wants to consider another vehicle.
- **Propose a test-drive booking** when the buyer has clearly asked for a test drive and a valid vehicle, salesperson, and time slot are available.

A follow-up task is an internal work item assigned to a salesperson. It does not place a call or send a message. An operator must approve an agent proposal before it changes business records. The backend checks the latest data, performs the approved action, and records what happened. Idaten does not contact customers.

This is not a public car marketplace or a full dealership management system. Demo leads, buyers, staff, listings, and bookings are generated sample data. Vehicle specifications may use cited manufacturer sources; sample listing prices and stock status are not live market data.

<!-- ## 1. Main screens

1. **Lead Recovery Dashboard:** Overdue leads, assigned salesperson, lead status, last activity, contact restrictions, pending proposals, and open tasks.
2. **Lead Review:** Buyer preferences and history, vehicle details, related sales-procedure evidence, Idaten's proposed action, and approve/reject controls.
3. **Agent Trace:** The ordered steps Idaten ran, including tool calls, records checked, procedure passages found, decisions, errors, and action results. It shows recorded steps, not hidden model reasoning.
4. **Agent Activity:** Actions and decisions that actually occurred, including approvals, task creation, bookings, cancellations, vehicle checkout/return, and recorded outcomes. Each relevant item links to its agent trace.
5. **Vehicle Inventory:** Search and filter listings, view condition and inspection status, and compare suitable alternatives.
6. **Test Drive Schedule:** Available slots, bookings, assigned salesperson, customer-confirmation record, appointment status, vehicle checkout/return, and overdue alerts. -->

The operator can check inventory and create a booking manually. Agent Idaten uses the same backend rules and records, so its results cannot bypass the rules used by the operator.

## 1. Project workflow

1. The operator starts lead recovery.
2. The backend selects overdue, open leads using fixed rules. It does not ask the language model to calculate dates or decide lead eligibility.
3. Idaten checks the lead, recent activity, contact permission, existing tasks, relevant vehicles, and applicable sales-procedure documents.
4. Idaten proposes a follow-up task or, when there is clear evidence of a test-drive request, a test-drive booking. It includes the facts and procedure sources behind its suggestion.
5. The operator approves or rejects the proposal.
6. On approval, the backend rechecks the current data. If the proposal is still valid, it creates the task or booking in a database transaction.
7. The result appears in Agent Activity and the related Agent Trace. If the data changed or a conflict appeared, the action is rejected and the reason is shown.
8. Staff record real-world outcomes. Creating a task does not mean a call occurred, and reserving a slot does not mean the buyer was notified or confirmed.

## 2. Test-drive rules

Test-drive booking is part of the first release. It is an internal reservation and does not send a message or book anything in an external calendar.

- The agent may propose a test drive only when the lead has a recorded inbound activity that clearly says the buyer requested one. General interest in a car is not enough.
- The contact-permission status must be `permitted`. `unknown` or `do_not_contact` blocks a booking until staff resolves the status.
- The selected listing must belong to the lead's location, be available, and have passed inspection. Sold, withdrawn, reserved, or review-needed vehicles cannot be booked.
- The salesperson must be active, assigned to that location, and eligible to handle test drives. The selected slot must be open, in the future, and at the same location.
- The prototype offers three sample slots per day, at 10:00, 13:00, and 16:00 local time. Each slot is 30 minutes, followed by a 15-minute vehicle turnaround buffer. These are configurable demo rules, not universal dealership hours.
- The backend checks vehicle and salesperson conflicts when showing slots and checks again when a booking is approved. A screen showing a free slot is not a guarantee that it will still be free later.
- Agent proposals do not reserve a slot. Only successful approval commits the reservation. Manual bookings use the same checks.

### Booking status and return of the vehicle

- `scheduled`: an internal slot is reserved. Customer confirmation remains `not_recorded` until staff records it.
- `checked_out`: staff has recorded that the vehicle physically left. The system never assumes this happened.
- `returned`: staff has recorded the actual return time. The vehicle is not available for another drive before its return is recorded.
- `completed`: staff has recorded the result of the drive.
- `cancelled`: staff cancelled the booking before checkout and recorded a reason.
- `no_show`: staff explicitly recorded a no-show after the slot ended. The system does not infer a no-show just because time passed.

If a checked-out vehicle passes its expected return time, the schedule shows **Return overdue**. The booking stays checked out and the vehicle remains blocked until staff records the actual return. A scheduled appointment with no recorded outcome after its slot ends shows **Appointment outcome unresolved**.

## 3. Scope

### Included

- One local operations workspace with the six screens above.
- Lead recovery, lead history, vehicle search, internal follow-up tasks, and test-drive booking.
- Human approval for every action proposed by Agent Idaten.
- Agent trace, activity history, and an audit record for important changes.
- A small set of sample sales-procedure documents with source and section references.
- A repeatable data seed and tests for normal cases and important failure cases.

### Not included

- Public marketplace, buyer login, self-service booking, payments, or financing.
- Real calls, email, SMS, or WhatsApp; external customer notifications or calendar connections.
- Licence checks, gate passes, GPS tracking, or connections to a real dealership system.
- Multi-tenant hosting, production authentication, multiple autonomous agents, or separately deployed business microservices.
- Claims of real sales growth or savings. These would require a live trial and measured results.

## 4. Architecture

Vehicentric is a **modular monolith**: one web app and one backend application with clear module boundaries. The modules run as one service and use one MySQL database. They are not separate business microservices.

### High-level Architecture

flowchart TB
OP["Sales Operator"] --> UI["Web App<br/>React + TypeScript"]
UI --> API["FastAPI"]

    subgraph APP["Vehicentric Backend - Modular Monolith"]
        API --> REC["Lead Recovery"]
        API --> SVC["Business Services<br/>Leads, Inventory, Follow-ups, Test Drives"]
        API --> APPROVE["Approval and Execution"]

        REC --> AGENT["LangGraph Workflow<br/>Agent Idaten"]
        AGENT <--> MCPCLIENT["MCP Client"]
        MCPCLIENT <--> MCPSERVER["MCP Server<br/>Typed Read-only Tools"]
        MCPSERVER --> SVC

        AGENT --> RAG["RAG Retrieval"]
        AGENT --> TRACE["Agent Run and Trace Recorder"]

        APPROVE --> SVC
    end

    SVC --> DB[("MySQL")]
    TRACE --> DB

    RAG <--> VDB[("Chroma Vector Store")]
    DOCS["Sales SOP Documents"] --> INGEST["Document Chunking and Embeddings"]
    INGEST --> VDB

    AGENT <--> LLM["LLM Provider"]

    classDef user fill:#e8f0fe,stroke:#5478b8,color:#172b4d
    classDef agent fill:#f1e8ff,stroke:#8a63c7,color:#30204b
    classDef storage fill:#e5f4e8,stroke:#529568,color:#173d22
    class OP,UI user
    class AGENT,MCPCLIENT,MCPSERVER,RAG agent
    class DB,VDB storage

### Lead recovery and test-drive workflow

flowchart TD
A["Find Overdue Leads<br/>Using Business Rules"]
B["Agent Idaten Investigates<br/>Lead History, Preferences, Inventory and SOPs"]
C{"Is a Test Drive<br/>the Right Next Step?"}
D["Propose Follow-up Task<br/>or Request Human Review"]
E["Find Available Slots<br/>Check Vehicle, Salesperson and Opening Hours"]
F{"Is a Suitable Slot Available?"}
G["Propose Follow-up<br/>or Show Alternative Slots"]
H["Show Recommendation and Evidence<br/>Wait for Human Approval"]
I{"Approved?"}
J["Record Rejection<br/>No Business Action Executed"]
K["Recheck Lead, Vehicle and Slot<br/>Inside a Database Transaction"]
L{"Still Available?"}
M["Mark Proposal Stale<br/>Refresh Slots and Request Approval Again"]
N["Create Test-Drive Booking<br/>Record Action and Trace"]
O["Appointment Takes Place"]
P["Staff Records Outcome<br/>and Confirms Vehicle Return"]
Q{"Vehicle Confirmed Returned?"}
R["Mark Vehicle Available<br/>If No Other Hold Exists"]
S["Keep Vehicle Unavailable<br/>Raise Overdue-Return Alert"]

    A --> B --> C
    C -- "No" --> D --> H
    C -- "Yes" --> E --> F
    F -- "No" --> G --> H
    F -- "Yes" --> H
    H --> I
    I -- "No" --> J
    I -- "Yes" --> K --> L
    L -- "No" --> M --> H
    L -- "Yes" --> N --> O --> P --> Q
    Q -- "Yes" --> R
    Q -- "No" --> S

- **React and TypeScript:** displays the six screens and calls the API.
- **FastAPI and Pydantic:** provides API endpoints and validates requests and responses.
- **MySQL:** stores leads, listings, slots, bookings, tasks, proposals, trace events, and audit records. It is the source of truth for business data.
- **LangGraph:** runs Agent Idaten's bounded investigation flow.
- **MCP (Model Context Protocol):** provides a standard interface for the agent to call named, typed tools. The local MCP server uses standard input/output (`stdio`) and calls the same backend services; it does not contain a second copy of business rules.
- **RAG (retrieval-augmented generation):** finds relevant sections in the sample sales procedures and returns their sources with the answer.
- **Chroma:** stores searchable numerical representations of procedure text. It can be rebuilt from the source documents.
- **LLM provider adapter:** lets the backend use one configured language model without tying business rules to a single provider.

Dates, contact restrictions, vehicle readiness, slot availability, conflicts, approval, and database writes are controlled by backend business logic. The model cannot run arbitrary SQL or perform the final approved action by itself.

## 5. Project structure

```text
vehicentric/
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── src/vehicentric/
│   │   │   ├── main.py
│   │   │   ├── api/            # FastAPI routes and Pydantic schemas
│   │   │   ├── leads/          # Lead records, activity, eligibility
│   │   │   ├── lead_recovery/  # Overdue queue and recovery use case
│   │   │   ├── inventory/      # Listings, readiness, alternatives
│   │   │   ├── follow_ups/     # Follow-up task rules and actions
│   │   │   ├── test_drives/    # Slots, bookings, checkout and return
│   │   │   ├── agent/          # Agent Idaten and LangGraph workflow
│   │   │   ├── mcp/            # MCP server and typed tool definitions
│   │   │   ├── knowledge/      # Procedure ingestion and retrieval
│   │   │   ├── audit/          # Activity, audit, and trace persistence
│   │   │   ├── workspace/      # Dashboard and schedule read queries
│   │   │   └── infrastructure/ # Settings, database, model adapter, logging
│   │   └── tests/
│   │       ├── unit/
│   │       ├── integration/
│   │       └── evaluation/
│   └── web/
│       └── src/                # Pages, UI components, API client
├── data/
│   ├── reference/              # Vehicle specification sources
│   └── generated/              # Repeatable sample data
├── knowledge/policies/         # Sample sales-procedure documents
├── scripts/                    # Seed data and build the procedure index
├── docs/                       # Project notes and evaluation results
└── .env
```

## 6. Database Design

erDiagram
RETAIL_LOCATIONS {
bigint location_id PK
string location_code UK
string location_name
string city
string timezone
boolean is_active
}
TEAM_MEMBERS {
bigint team_member_id PK
bigint location_id FK
string staff_code UK
string display_name
string job_title
boolean is_active
}
VEHICLE_MODELS {
bigint vehicle_model_id PK
string make
string model_name
string variant
int model_year
}
VEHICLE_LISTINGS {
bigint listing_id PK
string stock_number UK
bigint location_id FK
bigint vehicle_model_id FK
decimal asking_price
string listing_status
string inspection_status
}
TEST_DRIVE_SLOTS {
bigint test_drive_slot_id PK
bigint location_id FK
datetime starts_at_utc
datetime ends_at_utc
string slot_status
}
PROSPECTS {
bigint prospect_id PK
string prospect_code UK
string display_name
string contact_permission
decimal budget_min
decimal budget_max
}
SALES_LEADS {
bigint lead_id PK
string lead_code UK
bigint prospect_id FK
bigint location_id FK
bigint assigned_team_member_id FK
bigint primary_listing_id FK
string stage
datetime next_follow_up_at
}
LEAD_ACTIVITIES {
bigint lead_activity_id PK
bigint lead_id FK
bigint recorded_by_team_member_id FK
string activity_type
datetime occurred_at
string outcome
}
POLICY_DOCUMENTS {
bigint policy_document_id PK
string document_code
string version_label
string status
string content_sha256 UK
}
POLICY_CHUNKS {
bigint policy_chunk_id PK
bigint policy_document_id FK
int chunk_index
string chunk_sha256 UK
string vector_record_id UK
}
AGENT_RUNS {
bigint agent_run_id PK
string run_uuid UK
string run_type
string run_status
string model_provider
int duration_ms
}
AGENT_RUN_EVENTS {
bigint agent_run_event_id PK
bigint agent_run_id FK
int event_sequence
string event_type
string event_status
int duration_ms
}
ACTION_PROPOSALS {
bigint action_proposal_id PK
string proposal_uuid UK
bigint agent_run_id FK
bigint lead_id FK
bigint proposed_assignee_team_member_id FK
bigint proposed_listing_id FK
bigint proposed_salesperson_team_member_id FK
bigint proposed_test_drive_slot_id FK
bigint test_drive_intent_activity_id FK
string action_type
string proposal_status
}
TEST_DRIVE_BOOKINGS {
bigint test_drive_booking_id PK
string booking_code UK
bigint location_id FK
bigint lead_id FK
bigint listing_id FK
bigint assigned_team_member_id FK
bigint test_drive_slot_id FK
bigint source_proposal_id FK
string booking_status
string customer_confirmation_status
}
FOLLOW_UP_TASKS {
bigint follow_up_task_id PK
string task_code UK
bigint lead_id FK
bigint assigned_team_member_id FK
bigint source_proposal_id FK
string task_type
string task_status
datetime due_at
}
AUDIT_LOGS {
bigint audit_log_id PK
bigint agent_run_id FK
string actor_type
string action_name
string target_type
string action_outcome
}

    RETAIL_LOCATIONS ||--o{ TEAM_MEMBERS : employs
    RETAIL_LOCATIONS ||--o{ VEHICLE_LISTINGS : stocks
    RETAIL_LOCATIONS ||--o{ TEST_DRIVE_SLOTS : defines
    RETAIL_LOCATIONS ||--o{ SALES_LEADS : receives
    RETAIL_LOCATIONS ||--o{ TEST_DRIVE_BOOKINGS : hosts

    VEHICLE_MODELS ||--o{ VEHICLE_LISTINGS : describes
    PROSPECTS ||--o{ SALES_LEADS : raises
    TEAM_MEMBERS o|--o{ SALES_LEADS : assigned_to
    VEHICLE_LISTINGS o|--o{ SALES_LEADS : primary_vehicle_for
    SALES_LEADS ||--o{ LEAD_ACTIVITIES : has_history
    TEAM_MEMBERS o|--o{ LEAD_ACTIVITIES : records

    POLICY_DOCUMENTS ||--o{ POLICY_CHUNKS : contains

    AGENT_RUNS ||--o{ AGENT_RUN_EVENTS : records
    AGENT_RUNS ||--o{ ACTION_PROPOSALS : produces
    SALES_LEADS ||--o{ ACTION_PROPOSALS : is_investigated_by
    TEAM_MEMBERS o|--o{ ACTION_PROPOSALS : proposed_task_assignee
    TEAM_MEMBERS o|--o{ ACTION_PROPOSALS : proposed_test_drive_staff
    VEHICLE_LISTINGS o|--o{ ACTION_PROPOSALS : proposed_vehicle
    TEST_DRIVE_SLOTS o|--o{ ACTION_PROPOSALS : proposed_slot
    LEAD_ACTIVITIES o|--o{ ACTION_PROPOSALS : test_drive_request_evidence

    SALES_LEADS ||--o{ TEST_DRIVE_BOOKINGS : has_bookings
    VEHICLE_LISTINGS ||--o{ TEST_DRIVE_BOOKINGS : is_booked_for
    TEAM_MEMBERS ||--o{ TEST_DRIVE_BOOKINGS : assigned_to
    TEST_DRIVE_SLOTS ||--o{ TEST_DRIVE_BOOKINGS : reserves
    ACTION_PROPOSALS o|--o| TEST_DRIVE_BOOKINGS : may_create

    SALES_LEADS ||--o{ FOLLOW_UP_TASKS : has_tasks
    TEAM_MEMBERS o|--o{ FOLLOW_UP_TASKS : assigned_to
    ACTION_PROPOSALS o|--o| FOLLOW_UP_TASKS : may_create

    AGENT_RUNS o|--o{ AUDIT_LOGS : associated_with

| Table                                         | What it stores                                                                                   |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `retail_locations`, `team_members`            | Sample locations and sales staff. Staff records are not login accounts.                          |
| `vehicle_models`, `vehicle_listings`          | Vehicle facts and individual sample stock units.                                                 |
| `prospects`, `sales_leads`, `lead_activities` | Buyer preferences, enquiries, lead status, and recorded activity.                                |
| `follow_up_tasks`                             | Internal work assigned to staff, with due date and status.                                       |
| `test_drive_slots`, `test_drive_bookings`     | Dated slots, resource assignments, booking status, actual checkout/return, and recorded outcome. |
| `policy_documents`, `policy_chunks`           | Source procedures and sections used for retrieval and citations.                                 |
| `agent_runs`, `agent_run_events`              | Agent run status, ordered trace events, tool results, errors, timing, and usage where available. |
| `action_proposals`                            | Proposed action, evidence, source citations, expiry, and human decision.                         |
| `audit_logs`                                  | Who approved, rejected, or changed something, when it happened, and the result.                  |

Store event timestamps in UTC and display appointment times in the location's time zone. Use foreign keys, appropriate indexes, and database transactions for related writes. Keep sample data marked as synthetic. Do not treat Chroma as the source of truth for procedure content.

## 7. Safety and failure handling

- **Stale proposal:** recheck the lead, contact permission, vehicle, inspection, slot, staff, and request evidence at approval. Reject the proposal if a required fact has changed.
- **Duplicate request or retry:** use an idempotency key (a stable request ID) and database uniqueness rules so a repeated request does not create another task or booking.
- **Two operators book at once:** lock the relevant rows and recheck conflicts in one transaction. The losing request gets a clear conflict response.
- **No valid slot or vehicle:** do not make a booking. Show the reason and allow the operator to review alternatives.
- **Vehicle return is late:** show an alert and keep the vehicle unavailable until the return is recorded.
- **No recorded appointment outcome:** show an unresolved status; do not mark it a no-show automatically.
- **No contact permission or unclear test-drive request:** do not propose outreach or a booking that breaks the rules. Ask for staff review or propose a permitted internal review task.
- **Model, MCP, database, or vector search fails:** show the failed step in the trace. Do not create a partially validated business action. Manual database-backed views should remain usable when their dependencies are available.
- **Missing procedure evidence:** state that no suitable procedure was found. Do not make up a policy or citation.
- **Untrusted notes or retrieved text:** treat them as data, not instructions that can change tool permissions. This protects against prompt injection, where text tries to trick the agent into breaking its rules.

A trace records tool inputs and outputs as short, safe summaries. It must not store secrets or hidden model reasoning. Save related changes in one database transaction, so they either all succeed or none do. The activity log marks an action successful only after the transaction commits and the result is read back.
