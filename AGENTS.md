# CampusCycle — Project Instructions for AI Coding Agents

## 1. Project Identity and Source of Truth

CampusCycle is a college-focused resource-sharing and resource-management platform. Its purpose is to help participating colleges manage educational resources through listings, donations, exchanges, purchase enquiries, requests, inventory reservations, and transfers.

Use the root `PROJECT_PROGRESS.md` as the authoritative source for current progress, phase status, and the unified Phase 0–12 roadmap.

Use the `project-blueprint/` directory as the source of truth for approved technical design documentation, including architecture, database design, database schema, API specifications, and design decisions.

### Current Project Status

- Phase 0 — Foundation and Environment Setup: **COMPLETED**.
- Phase 1 — Frontend Development: **COMPLETED** as a frontend prototype.
- Phase 2 — System Design, Database Design and API Planning: **COMPLETED**.
- Phase 3 — Backend Foundation: **COMPLETED**.
- Phase 4 — Database Development: **COMPLETED and independently approved**.
- Phase 5 - Authentication and Authorization: **COMPLETED**.
- Phase 6 – Resource Management: **COMPLETED**.
- Phase 7 – Requests, Approvals and Reservations: **COMPLETED**.

Phase 1 uses demonstration data and local React state. Phase 4 provides the approved database schema and migrations. Phase 5 implements authentication, college onboarding, account management, and authorization. Phase 6 implements resource listing management, inventory reads, and local image handling without schema changes. Phase 7 implements request submission, approvals, reservations, purchase confirmation, and request-level cancellation before transfer batches exist. Transfer workflows and complete frontend-backend integration are not yet implemented.

Do not describe the entire application as complete.

---

## 2. CampusCycle V1 Scope

Preserve the original V1 requirements:

- College registration and authentication.
- College and user management.
- Resource marketplace and listings.
- Donations.
- Exchanges.
- Purchase enquiries.
- Purchase payments handled outside the application.
- Resource requests with approval and rejection.
- Inventory management and reservations.
- Inter-college transfers and tracking.
- Dispatch and receipt confirmation.
- Dashboard and analytics.

### Main Business Workflow

**Listing → Request → Approval → Reservation → Dispatch → Receipt → Completion**

### Explicitly Out of Scope

- Temporary borrowing.
- Rentals and return workflows.
- Online payment gateways.
- Chat and social features.
- AI recommendations and image recognition.
- Live GPS tracking.
- Route optimization.
- Native mobile applications.
- Other unapproved functionality.

Do not expand the V1 scope without explicit developer approval.

Do not invent missing business rules. Record unclear requirements and request clarification before designing or implementing behavior that depends on them.

---

## 3. Existing Frontend — Preserve It

Project root: `D:\CampusCycle`

Frontend: `D:\CampusCycle\frontend`

The agreed frontend stack is:

- React.
- Vite.
- JavaScript.
- Tailwind CSS v4.
- Lucide React.

Existing frontend modules:

- Dashboard.
- Marketplace.
- My Listings.
- My Requests.
- Inventory.
- Transfers.
- Analytics.

The existing frontend is a completed prototype, primarily using local React state and demonstration data.

Preserve its functionality and decisions:

- Do not rewrite the frontend or replace its design system.
- Do not remove existing modules.
- Do not unnecessarily modify completed functionality.
- Preserve light and dark themes.
- Preserve responsive layouts.
- Preserve the existing blue/green design direction.
- Do not change code merely to substitute a preferred implementation.
- Modify frontend code only when required by an approved task.

---

## 4. Agreed Technology Stack

| Component | Technology |
|---|---|
| Frontend | React |
| Build Tool | Vite |
| Programming Language | JavaScript |
| Styling | Tailwind CSS v4 |
| Icons | Lucide React |
| Backend | Python + FastAPI |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Authentication | JWT |
| Database | SQLite |
| Database Migrations | Alembic |
| API Documentation | Swagger / OpenAPI |
| Testing | Pytest and appropriate frontend/integration checks |
| Version Control | Git + GitHub |
| Containerization | Docker |
| Orchestration | Docker Compose |

Use this stack unless a genuine technical issue requires a proposed change.

Explain significant architecture changes and obtain approval before changing agreed decisions.

Avoid unnecessary dependencies and overengineering.

---

## 5. Development Roadmap

Follow the roadmap and statuses in `PROJECT_PROGRESS.md`.

Phase names and numbering must match it exactly.

| Phase | Name | Current Status |
|---|---|---|
| 0 | Foundation and Environment Setup | COMPLETED |
| 1 | Frontend Development | COMPLETED |
| 2 | System Design, Database Design and API Planning | COMPLETED |
| 3 | Backend Foundation | COMPLETED |
| 4 | Database Development | COMPLETED and independently approved |
| 5 | Authentication and Authorization | COMPLETED |
| 6 | Resource Management | COMPLETED |
| 7 | Requests, Approvals and Reservations | COMPLETED |
| 8 | Logistics and Transfer Tracking | UPCOMING |
| 9 | Frontend-Backend Integration | UPCOMING |
| 10 | Analytics Integration | UPCOMING |
| 11 | Docker Deployment | UPCOMING |
| 12 | Testing, Documentation and Finalization | UPCOMING |

Do not skip phases or begin work from a later phase without explicit approval.

Phase 3 is complete. Phase 4 implementation has been independently reviewed and approved; follow `PROJECT_PROGRESS.md` for the current phase status.

Do not reimplement Phase 2 unless explicitly requested.

---

## 6. Phase 2 — Approved System Design

Phase 2 — System Design, Database Design and API Planning is **COMPLETED**.

Its approved design documentation is maintained in:

`project-blueprint/`

### Approved Phase 2 Deliverables

- System architecture.
- Database design and ER relationships.
- Detailed database schema.
- Inventory and reservation rules.
- Request and approval workflows.
- Transfer and receipt workflows.
- Authentication and authorization planning.
- API endpoint specifications.
- Standard API response formats.
- Security and validation requirements.
- Final design review.

### Approved Database Tables

The approved database design contains seven tables:

1. `colleges`
2. `users`
3. `resources`
4. `requests`
5. `transfers`
6. `transfer_status_history`
7. `refresh_tokens`

Use the approved schema in `project-blueprint/database-schema.md` as the reference when implementing the database in Phase 4.

Do not create alternative schemas or introduce additional tables without explaining the reason and obtaining approval.

### Approved Business and Database Rules

#### College and User Management

- Each user belongs to one college, except the global Platform Admin.
- Platform Admin is a separate global role.
- Pending and rejected colleges may browse but cannot transact.
- College Representatives can create representative accounts only within their own college.
- Representatives cannot create Platform Admin accounts.
- Representatives cannot manage users belonging to other colleges.
- The last active representative of a college cannot be deactivated.

#### Inventory and Reservations

- Inventory reservations apply only to approved quantities.
- Approval of a request must not reserve the entire resource listing.
- Inventory changes must preserve quantity consistency.
- Reservation operations must use appropriate database transactions and concurrency protection.
- Dispatched quantities remain reserved until receipt and the relevant completion conditions are satisfied.
- Inventory must not be adjusted based on unverified physical receipt claims.

#### Requests and Exchanges

- Rejected requests remain rejected.
- A requesting college must submit a new request if it wants to try again.
- Exchange requests involve one offered resource.
- Exchange approval must reserve both sides atomically.
- If either side cannot be reserved, the entire reservation operation must roll back.
- An exchange request becomes completed only after both resource movements are completed and receipt is confirmed.

#### Purchase Enquiries

- Submitting a purchase enquiry does not reserve inventory.
- Inventory reservation happens only after the requesting college confirms its intention to purchase.
- If sufficient inventory is unavailable after confirmation, do not automatically cancel the request or reserve unavailable stock.

#### Transfers and Partial Transfers

- One approved request may have multiple partial transfers.
- Partial transfers are created by the sending college representative.
- The total transferred quantity must not exceed the approved quantity for the relevant transfer leg.
- Every transfer must maintain status history.
- The destination college confirms receipt.

#### Damaged and Missing Items

- The receiving college must report good, damaged, and missing quantities.
- Damaged and missing quantities must be disputed rather than automatically marked as successfully received.
- Disputed quantities must not be treated as completed until the dispute is resolved.
- Inventory adjustments must follow verified physical status and the recorded resolution.

#### Cancellation

- Before dispatch, cancellation requires review by the resource-owning college representative.
- Approved pre-dispatch cancellation releases the unshipped reserved quantity.
- After dispatch, ordinary cancellation is blocked.
- Exceptional post-dispatch cancellation requires Platform Admin approval.
- Only unshipped batches may be cancelled and released through that process.
- Dispatched batches continue until their physical status is resolved.

#### Disputes

- Platform Admin is responsible for resolving transfer disputes.
- Possible outcomes include accepting verified good quantity, approving a replacement transfer, or rejecting a claim after review.
- Inventory adjustments happen only after the physical situation is verified and the resolution is recorded.

#### Authentication

- Access token target: 15 minutes.
- Refresh token lifetime: 7 days.
- Refresh tokens rotate when used.
- Logout revokes the refresh token.
- Refresh tokens must be stored securely; never store raw refresh-token values in the database.
- Authentication and authorization must be enforced by the backend.

### Phase 2 Completion Boundary

Phase 2 is a design and planning deliverable.

No backend APIs, SQLAlchemy models, database migrations, or actual database tables were created as part of Phase 2.

Phase 3 — Backend Foundation is complete. Phase 4 — Database Development has been implemented, independently reviewed, and approved.

---

## 7. Phase 3 — Backend Foundation: COMPLETED

The backend foundation is implemented and verified. See the Phase 3 section of `PROJECT_PROGRESS.md` for its completion record.

### Objective

Establish a clean, maintainable, and properly configured FastAPI backend.

### Planned Tasks

- Create the backend project structure.
- Configure the Python virtual environment and dependencies.
- Install and configure FastAPI and Uvicorn.
- Configure environment variables.
- Configure application settings.
- Create the FastAPI application entry point.
- Configure CORS.
- Implement a basic health-check endpoint.
- Configure centralized error handling.
- Configure logging.
- Verify backend startup.
- Verify Swagger/OpenAPI documentation.
- Update backend setup documentation.

### Phase 3 Restrictions

- Do not implement database models before Phase 4.
- Do not create database migrations before Phase 4.
- Phase 5 authentication and authorization are implemented; do not add features beyond its approved contract without approval.
- Do not implement resource or request business workflows prematurely.
- Do not implement Docker deployment before Phase 11.

Complete and verify the backend foundation before moving to Phase 4.

---

## 8. Phase 4 — Database Development: COMPLETED AND APPROVED

The approved Phase 2 schema is implemented as exactly seven SQLAlchemy models and Alembic migrations. The latest local corrective revision is `c81f23a7d940`, parented to `f4a6d9c123ab`; it has been verified on isolated SQLite databases. Tests cover model relationships, database constraints, foreign-key enforcement, indexes, UTC timestamps, request offer-field integrity, and migrations from an empty database and the previous head. The persistent Docker database and volume were not accessed for this targeted correction; its previous recorded verification was at revision `f4a6d9c123ab`.

Phase 4 does not include authentication endpoints, refresh-token operations, business APIs, or service-layer workflows. Phase 4 has been independently reviewed and approved. Use `PROJECT_PROGRESS.md` for the detailed verification record and current status.

---

## 9. Development Workflow and Quality

Use Codex for coding tasks.

Work on one task at a time, in small, logical, verifiable steps.

For every task:

1. Inspect the existing project and relevant dependencies before making changes.
2. Understand the requested work and explain the approach briefly.
3. Identify the files that need changes.
4. Modify only what the task requires.
5. Run relevant checks and tests when appropriate.
6. Report only checks that were actually run and their results.
7. Report changed files and remaining issues.

Write clear, maintainable code with:

- Focused modules.
- Meaningful names.
- Appropriate validation.
- Proper error handling.
- Appropriate HTTP status codes.
- Secure database access.
- Transactions where needed.
- Suitable database constraints and indexes.
- Clear separation of frontend and backend responsibilities.

Do not overengineer.

Never claim a feature is complete unless it has been implemented and verified.

Never claim a test passed unless it was actually run successfully.

Maintain `PROJECT_PROGRESS.md` to reflect verified progress.

---

## 10. Security Requirements

- Never commit API keys, passwords, or other secrets.
- Never expose database credentials.
- Keep `.env` files out of Git.
- Use `.env.example` only for non-secret examples.
- Validate protected operations on the backend.
- Do not trust frontend-only permission checks.
- Use secure password hashing.
- Never store plaintext passwords.
- Store refresh tokens as hashes.
- Avoid logging sensitive information.
- Enforce college-level data isolation on the backend.
- Use appropriate authorization checks for every protected operation.

---

## 11. Git, GitHub and Docker

### Git and GitHub

- Do not commit without the developer's explicit approval.
- Do not push without the developer's explicit approval.
- Do not delete branches without permission.
- Do not overwrite project history.
- Do not perform destructive Git operations without explicit permission.
- Keep generated files, `node_modules`, build outputs, local environments, and secrets out of commits.
- Explain significant changes before requesting commit approval.
- Maintain meaningful commit messages.

### Docker

Docker deployment belongs to Phase 11.

The planned deployment includes:

- Frontend container.
- Backend container.
- Docker Compose orchestration.
- Environment-based configuration.
- SQLite-compatible persistent storage.
- Appropriate container networking.
- Health checks where appropriate.

Do not containerize prematurely or disrupt local development.

---

## 12. Communication and Collaboration

The developer is learning full-stack development.

Therefore:

- Explain important technical decisions in understandable language.
- Give commands with their exact working directory and terminal.
- Explain important commands.
- Work step by step.
- Avoid overwhelming the developer with multiple unrelated tasks.
- Be technically honest.
- Explain trade-offs and limitations.
- Ask for approval before changing product scope or important business rules.
- Wait for user verification when a task depends on local execution.
- Do not assume that a command succeeded without seeing its result.

The developer is responsible for running local commands and verifying their results.

Do not claim direct access to local project files or the developer's machine unless access has actually been provided.

---

## 13. Final Rule

Complete CampusCycle V1 before considering enhancements.

Prioritize:

1. Correctness.
2. Security.
3. Maintainability.
4. Consistent business rules.
5. Reliable inventory and transfer workflows.
6. A working end-to-end application.
7. Clear documentation.

Preserve the agreed V1 scope, existing project decisions, completed frontend, approved Phase 2 design, and recorded development progress.

Do not introduce unapproved features or silently change previously approved decisions.
