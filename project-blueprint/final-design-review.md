# CampusCycle — Phase 2 Final Design Review

**Review status:** Completed  
**User approval:** All outstanding design decisions approved on 7 November 2026  
**Implementation status:** No backend code or database implementation has started.

## 1. Phase 2 deliverables

| Deliverable | Result |
|---|---|
| System architecture (`architecture.md`, already in repository) | Reviewed and approved earlier |
| Conceptual database design and ER model | Approved |
| Detailed logical database schema | Approved |
| REST API contract and endpoint plan | Approved |
| Design decision register | Approved decisions consolidated |

## 2. Approved table set

1. `colleges`
2. `users`
3. `resources`
4. `requests`
5. `transfers`
6. `transfer_status_history`
7. `refresh_tokens`

No separate disputes table is included in V1. Dispute information is represented on each transfer batch and audited through transfer status history.

## 3. Critical business rules verified across documents

- College representatives are tenant-scoped to one college; Platform Admin is global.
- Pending/rejected colleges can browse but cannot transact.
- Only approved quantities are reserved; reservation changes are transactional.
- Exchange approval reserves both sides atomically.
- Purchase enquiry does not reserve stock until buyer confirms purchase intention.
- Partial transfer batches cannot exceed the approved quantity for their movement leg.
- Dispatch does not reduce physical stock; accepted receipt/resolution updates inventory.
- A request completes only after all required movement legs and receipts are complete and no dispute remains.
- Pre-dispatch cancellation is reviewed by the resource-owning college representative; cancellation after any dispatch requires Platform Admin review for unshipped batches.
- Platform Admin resolves damaged/missing disputes; disputed quantity remains held until verified resolution.
- Rejected requests remain rejected and require a new request for another attempt.
- Refresh tokens are hashed, expire in 7 days, rotate on use, and support reuse detection; browser storage uses Secure/HttpOnly cookies with CSRF protection.
- Last active representative protection is enforced when deactivating accounts.

## 4. Scope check

The design remains within the agreed CampusCycle V1 scope: donations, exchanges, purchase enquiries with payment outside the application, resource requests/approvals, inventory/reservations, inter-college transfers, receipt confirmation, dispute handling, and analytics. No temporary borrowing/rentals/returns, payment gateway, chat/social feature, AI recommendation, live GPS/route optimization, or mobile app has been introduced.

## 5. Implementation readiness and boundary

**Phase 2 design is approved and ready to hand off to Phase 3.** This is not a claim that the system has been implemented. The next phase, when explicitly started by the user, is Backend Foundation: establish the FastAPI application structure, configuration, database connection/session lifecycle, health endpoint, and development tooling. ORM models, migrations, and actual table creation belong to the later database implementation phase according to the roadmap.

Before implementation, developers must translate this logical specification into concrete SQLAlchemy constraints and transaction-safe service behavior without changing approved business rules. Any new business rule or scope change must be brought back for user approval.
