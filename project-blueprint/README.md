# CampusCycle — Phase 2 Design Drafts

**Status:** Phase 2 design decisions approved; final consistency review completed  
**Scope:** Phase 2 only: system design, database design, and API planning  
**Implementation status:** Design only. No backend code, ORM models, migrations, database tables, or API endpoints have been created.

## Included documents

1. `database-design.md` — conceptual data model and ER diagram.
2. `database-schema.md` — proposed tables, columns, constraints, indexes, and inventory semantics.
3. `api-specification.md` — proposed endpoints, permissions, payloads, response conventions, and workflow behavior.
4. `design-decisions.md` — approved decisions, role permissions, authentication settings, and workflow rules.
5. `final-design-review.md` — final consistency review and Phase 3 handoff boundary.

## Finalized design notes

- The approved model contains seven tables: `colleges`, `users`, `resources`, `requests`, `transfers`, `transfer_status_history`, and `refresh_tokens`.
- Refresh tokens are hashed at rest, expire after 7 days, rotate on use, and support reuse detection. Browser refresh tokens use Secure/HttpOnly cookies with CSRF protection. Access-token lifetime target is 15 minutes.
- Disputes are represented at the transfer-batch level in V1; a separate disputes table is not part of the approved scope. Platform Admin resolves disputes using the approved outcomes and records the decision.
- Pre-dispatch cancellation is reviewed by the resource-owning college representative. Once any batch has been dispatched, cancellation of remaining unshipped batches requires Platform Admin approval.
- Rejected requests remain rejected; a new request is required for resubmission.
- The permission boundaries, account deactivation rule, and all remaining decisions are recorded in `design-decisions.md`.
- The project must stay within the agreed V1 scope: donations, exchanges, purchase enquiries, requests, inventory, reservations, transfers, receipt confirmation, and analytics. Payments remain outside the app. No rentals/temporary borrowing/returns, chat, or AI features are added.

## Suggested placement in the repository

Copy these files into `D:\CampusCycle\docs\`. Keep the already-reviewed `architecture.md`; these documents complete the remaining Phase 2 design deliverables. Do not implement backend code until the user explicitly starts Phase 3.
