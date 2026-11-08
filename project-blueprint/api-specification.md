# CampusCycle V1 — API Specification

**Status:** Approved Phase 2 API contract  
**Base path:** `/api/v1`  
**Transport:** HTTPS in deployed environments; JSON request/response bodies  
**Authentication:** JWT access token plus approved 7-day rotating refresh-token flow  
**Implementation status:** No endpoints are implemented by this document.

## 1. API conventions

- Use REST-style resource paths and HTTP methods.
- Use ISO 8601 timestamps in UTC.
- Pagination: `page` (default 1), `page_size` (proposed default 20, maximum 100).
- Filtering and sorting must be allowlisted per endpoint.
- College scope is derived from the authenticated user, not trusted from arbitrary client-supplied IDs.
- FastAPI will expose generated OpenAPI/Swagger documentation.
- Versioning prefix: `/api/v1`.

### Success envelope

```json
{
  "success": true,
  "data": {}
}
```

### Error envelope

```json
{
  "error": {
    "code": "insufficient_stock",
    "message": "The requested quantity is no longer available.",
    "details": []
  }
}
```

Use stable machine-readable error codes. Never expose stack traces, password hashes, token values, or database internals.

## 2. Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Register a college and initial representative, subject to onboarding policy |
| POST | `/auth/login` | Verify credentials and issue access + refresh tokens |
| POST | `/auth/refresh` | Validate refresh token and issue a new access token |
| POST | `/auth/logout` | Revoke presented refresh token |
| GET | `/auth/me` | Return authenticated user's identity and college context |

### Login response (illustrative)

```json
{
  "success": true,
  "data": {
    "access_token": "<short-lived-jwt>",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": 12,
      "name": "College Representative",
      "role": "college_representative",
      "college_id": 4
    }
  }
}
```

Recommended browser handling:
- Keep the access token in memory where practical.
- Store the refresh token in a `Secure`, `HttpOnly`, appropriately `SameSite` cookie.
- Protect cookie-based refresh/logout endpoints against CSRF.
- Do not store long-lived refresh tokens in localStorage.
- Refresh tokens expire after 7 days and rotate on every successful refresh. Store only a hash in `refresh_tokens`; retain replacement lineage and detect reuse of an already-rotated token.
- On reuse detection, revoke the associated token family/session and require login again.
- Access-token lifetime target is 15 minutes; logout revokes the presented refresh token. Existing access tokens remain valid until expiry.

Approved token policy:
- Access token initial lifetime: 15 minutes.
- Refresh token lifetime: 7 days, rotated on every successful refresh. The refresh endpoint issues a new access token and sets the replacement refresh-token cookie.
- Reuse of a rotated refresh token revokes the associated token family/session and requires login again.
- Logout revokes the presented refresh token.
- Already-issued access tokens remain valid until expiry unless an additional denylist/revocation mechanism is separately approved.

## 3. Colleges

| Method | Endpoint | Access |
|---|---|---|
| GET | `/colleges/me` | College representative |
| PATCH | `/colleges/me` | Authorized representative; own college only |
| GET | `/colleges` | Platform administrator |
| GET | `/colleges/{college_id}` | Platform administrator or authorized scoped access |
| PATCH | `/admin/colleges/{college_id}/verification` | Platform administrator |

Verification values: `pending`, `verified`, `rejected`.

Pending and rejected colleges may browse resources but cannot transact. Verified colleges may transact.

## 4. Users

| Method | Endpoint | Access |
|---|---|---|
| GET | `/users/me` | Authenticated user |
| PATCH | `/users/me` | Authenticated user, own profile |
| GET | `/colleges/me/users` | Authorized representative, own college |
| POST | `/colleges/me/users` | Authorized representative; creates representative in own college only |
| PATCH | `/users/{user_id}/status` | Platform Admin across colleges; College Representative within own college, subject to last-active-representative protection |

College representatives cannot create platform administrators or users for another college.

## 5. Resources / marketplace

| Method | Endpoint | Access |
|---|---|---|
| GET | `/resources` | Authenticated users; pending/rejected may browse |
| POST | `/resources` | Verified college representative |
| GET | `/resources/{resource_id}` | Authenticated users, subject to visibility rules |
| PATCH | `/resources/{resource_id}` | Owning college, authorized representative |
| PATCH | `/resources/{resource_id}/status` | Owning college, authorized representative |

Suggested list filters: `category`, `transfer_type`, `condition`, `college_id` (where authorized), `search`, `page`, `page_size`.

## 6. Requests

| Method | Endpoint | Purpose / access |
|---|---|---|
| POST | `/requests` | Submit donation, exchange, or purchase enquiry; verified requesting college |
| GET | `/requests/mine` | Requests submitted by caller's college |
| GET | `/requests/received` | Requests received for resources owned by caller's college |
| GET | `/requests/{request_id}` | Either participating college, subject to field-level access |
| POST | `/requests/{request_id}/approve` | Authorized representative of resource-owning college |
| POST | `/requests/{request_id}/reject` | Authorized representative of resource-owning college; body requires a non-empty `reason` (maximum 2,000 characters) |
| POST | `/requests/{request_id}/cancel` | Requesting college submits a pre-transfer cancellation request with a non-empty `reason` |
| POST | `/requests/{request_id}/cancellation-decision` | Resource-owning college representative approves or rejects a pending request-level cancellation |
| POST | `/requests/{request_id}/purchase-confirmation` | Buyer confirms purchase intent; reservation attempted at this point |

Request listing endpoints use `page` (default `1`) and `page_size` (default `20`, maximum `100`). Detail access is limited to the requesting college and the college owning the requested resource. Approval accepts optional `approved_quantity`; donation approvals may be partial, while exchange and purchase approvals require the full requested quantity. Responses include review, approval, rejection, purchase-confirmation, and request-cancellation metadata.

### Request approval, rejection, and cancellation

- Only a verified College Representative of the resource-owning college may approve or reject a pending request. Platform Admin does not perform routine request review.
- Approval records the reviewer, timestamp, and approved quantity. Donation reservations may be partial. Exchange approval reserves the complete requested and offered quantities atomically. Purchase enquiry approval does not reserve inventory.
- Rejection requires a reason. The existing seven-table design did not contain a rejection-reason field; Phase 7 adds nullable `requests.rejection_reason`, stores it on rejection, and leaves rejected requests closed.
- Request-level cancellation is allowed only before any transfer row exists. Submission records the requesting representative, timestamp, reason, and previous status. Review is recorded as metadata on the existing request row; there is no new cancellation table or new request status.
- A cancellation submission does not release stock. Approval sets the request to `cancelled` and releases only its recorded reservation (including both sides of an approved exchange); rejection restores the prior status and retains reservations. Cancellation metadata and decisions are retained.
- Cancellation cannot be submitted more than once for a request. Transfer-row cancellation remains a separate Phase 8 workflow.

### Exchange approval behavior

Approving an exchange must:
1. Validate both colleges and both resources.
2. Validate requested and offered quantities.
3. Reserve both resources in a single database transaction.
4. Roll back both reservations if either side cannot be reserved.
5. Record the request approval and reservation outcome atomically.

### Purchase confirmation behavior

Purchase enquiry submission and approval do not reserve stock. On buyer purchase-intent confirmation:
- Attempt to reserve the requested quantity.
- If stock is sufficient, reserve it atomically and update request state.
- If stock is insufficient, reserve nothing, do not automatically cancel, and move the request to `awaiting_resolution`.
- Return a conflict response, e.g. HTTP `409` with code `insufficient_stock`.

## 7. Inventory

| Method | Endpoint | Access |
|---|---|---|
| GET | `/inventory/me` | Verified college representative; own college |
| GET | `/inventory/resources/{resource_id}` | Owning college or platform administrator |
| GET | `/inventory/resources/{resource_id}/reservations` | Owning college or platform administrator |

Inventory reads should distinguish total, available, and reserved quantities. Do not expose another college's internal reservation details to unauthorized users.

## 8. Transfers and receipt

All transfer endpoints use the `/api/v1` prefix and standard `{"success": true, "data": ...}` response envelopes.

| Method | Endpoint | Purpose / access |
|---|---|---|
| POST | `/requests/{request_id}/transfers` | Create a partial transfer batch; source college representative |
| GET | `/transfers` | Participating college scoped list; Platform Admin global list |
| GET | `/transfers/{transfer_id}` | Source/destination college representative or platform administrator |
| GET | `/transfers/{transfer_id}/history` | Transfer status audit history; participating college or platform administrator |
| POST | `/transfers/{transfer_id}/dispatch` | Mark batch as dispatched; source college representative |
| POST | `/transfers/{transfer_id}/receipt` | Confirm receipt with good/damaged/missing breakdown; destination college representative |
| POST | `/transfers/{transfer_id}/cancel` | Submit batch cancellation request; participating college representative |
| POST | `/transfers/{transfer_id}/cancellation-decision` | Cancellation review: resource-owning college representative before any dispatch, Platform Admin after dispatch |
| POST | `/transfers/{transfer_id}/dispute-resolution` | Resolve open transfer dispute; Platform Admin only |

### Transfer Creation Payload

```json
{
  "transfer_leg": "requested_resource",
  "quantity": 10,
  "pickup_or_delivery_date": "2026-11-15T10:00:00Z",
  "dispatch_notes": "First batch of lab equipment",
  "replacement_for_transfer_id": null
}
```

Validation & Authorization:
- Only an active representative of the source college (`request.resource.college_id` for `requested_resource` leg; `request.requesting_college_id` for `offered_resource` leg) can create a batch.
- Both colleges must be verified.
- The parent request must be in `approved` or `in_progress` status. For purchase enquiries, purchase intent must already be confirmed (`in_progress`).
- For non-replacement transfers, aggregate created quantities on that leg (excluding cancelled batches) cannot exceed the approved quantity for the leg.
- For replacement transfers (`replacement_for_transfer_id` specified), the target transfer must have `dispute_outcome == "replacement_approved"`, quantity cannot exceed the disputed damaged + missing count, and replacement stock is reserved atomically before batch creation.
- Initial transfer status is `preparing`, dispute status is `none`, and a `TransferStatusHistory` audit record is inserted atomically.

### Dispatch Payload

```json
{
  "dispatch_notes": "Dispatched via campus transport truck #4",
  "pickup_or_delivery_date": "2026-11-16T14:00:00Z"
}
```

Validation:
- Source college representative only.
- Current transfer status must be `preparing`. Duplicate dispatch is rejected with HTTP 409 `invalid_transfer_state`.
- Transitions status to `dispatched` and creates an audit history entry atomically.

### Receipt Payload

```json
{
  "quantity_received_good": 7,
  "quantity_damaged": 2,
  "quantity_missing": 1,
  "receipt_confirmation": "7 in good condition, 2 broken screen, 1 missing box."
}
```

Validation:
- Destination college representative only.
- Current transfer status must be `dispatched`. Duplicate confirmation is rejected with HTTP 409 `invalid_transfer_state`.
- Quantities must be non-negative and their sum must equal the batch `quantity` (HTTP 422 `invalid_receipt_quantities` otherwise).
- Verified good quantity is deducted immediately from the source resource's `quantity_total` and `quantity_reserved`.
- If `quantity_damaged > 0` or `quantity_missing > 0`, the transfer transitions to status `disputed` with `dispute_status = "open"`. Disputed items remain in `quantity_reserved`.
- If all items are good (`damaged == 0 and missing == 0`), transfer transitions to status `completed`. If the transfer is a replacement batch, the original disputed quantity is written off from the original resource.

### Dispute Resolution Payload

```json
{
  "dispute_outcome": "accept_report",
  "dispute_resolution": "Inspection confirmed damage during transit; written off."
}
```

Validation & Inventory Rules:
- Platform Admin only (HTTP 403 `forbidden` for college representatives).
- Transfer must have status `disputed` and `dispute_status = "open"` (HTTP 409 `invalid_dispute_state` on repeated resolution).
- Supported outcomes:
  - `accept_report`: Accepts the verified report; only verified good quantities are deducted; damaged and missing quantities remain reserved and are NOT automatically written off or released. Transfer transitions to `completed`, `dispute_status = "resolved"`.
  - `replacement_approved`: Authorizes a replacement batch; disputed quantity remains held in `quantity_reserved` until verified receipt of the replacement batch. Transfer transitions to `completed`, `dispute_status = "resolved"`.
  - `claim_rejected`: Rejects the damage/loss claim; disputed quantity remains held in `quantity_reserved` for manual accounting; not released to available and not written off. Transfer transitions to `completed`, `dispute_status = "resolved"`.

### Cancellation Behavior

- Participating college representatives submit cancellation via `POST /transfers/{transfer_id}/cancel` with a non-empty `reason`.
- Permitted only for transfers in status `preparing` or `dispatched` (not `disputed` or already `cancelled`/`completed`). Transfer transitions to `cancellation_pending`.
- Cancellation review via `POST /transfers/{transfer_id}/cancellation-decision` with `{"decision": "approved" | "rejected"}`:
  - **Before any batch of the request has been dispatched:** Decision belongs exclusively to the resource-owning college representative.
  - **After any batch has been dispatched:** Decision belongs exclusively to Platform Admin.
  - Only unshipped (`preparing`) batches can be approved for cancellation. If approved, the batch's reserved quantity is released back to `quantity_available` on the resource, and status moves to `cancelled`.
  - Dispatched batches cannot be cancelled (HTTP 409 `cannot_cancel_dispatched`); they must proceed through receipt and dispute resolution.
  - If rejected, the transfer status is restored to its previous status (`preparing` or `dispatched`).

### Request Aggregate Completion Rules

A request transitions to `completed` only when:
- All required movement legs (`requested_resource`, plus `offered_resource` for exchanges) have all approved quantities fully accounted for.
- All non-cancelled batches have been received and completed.
- No in-flight batches (`preparing`, `dispatched`, `cancellation_pending`) or open disputes (`open`) remain.
- All approved replacement workflows have been completely fulfilled and received.

## 9. Analytics

| Method | Endpoint | Access |
|---|---|---|
| GET | `/analytics/summary` | College-scoped summary; global view for platform admin |
| GET | `/analytics/categories` | Authorized analytics view |
| GET | `/analytics/transfers` | Authorized analytics view |
| GET | `/analytics/requests` | Authorized analytics view |
| GET | `/analytics/colleges` | Platform administrator |

Potential metrics:
- participating colleges;
- active listings;
- available resource quantities;
- pending/approved requests;
- completed transfers;
- transfers by category.

Do not publish estimated money-saved metrics until a defensible calculation method is defined.

## 10. Authorization rules

- Backend authorization is mandatory on every protected operation.
- College representatives can act only within their own college scope, except where they participate as the source or destination college in a specific transaction.
- Only the owning college may approve/reject a request for its resource.
- Only the source college may create and dispatch its transfer batch.
- Only the destination college may confirm receipt.
- Platform Admin can verify colleges, review cancellations after any dispatch, and resolve transfer disputes.
- College Representatives manage resources and transactions for their own college, may create/deactivate same-college representative accounts, and cannot deactivate the last active representative.
- Rejected requests remain rejected; clients submit a new request rather than reopening a rejected one.
- Pending and rejected colleges may browse but cannot transact.
- No user can create a platform administrator through the college-user endpoint.
- Frontend button visibility is not a security control.

## 11. HTTP status mapping

| Status | Use |
|---|---|
| 200 | Successful read/update/action |
| 201 | Resource created |
| 204 | Successful operation with no response body, where appropriate |
| 400 | Invalid operation or malformed business action |
| 401 | Missing/invalid/expired authentication |
| 403 | Authenticated but not authorized |
| 404 | Record does not exist or is outside caller's permitted visibility |
| 409 | State conflict, insufficient stock, duplicate/conflicting operation |
| 422 | Request schema/field validation failure |
| 500 | Unexpected server failure; no internal details returned |

## 12. Idempotency and transactions

- Approval/reservation, exchange reservation, purchase confirmation, dispatch, receipt, cancellation decision, and dispute resolution must use explicit transaction boundaries.
- Retryable actions should be idempotent or detect already-applied state to avoid duplicate stock changes.
- For high-impact write endpoints, consider an idempotency key; exact implementation is a Phase 3/4 engineering detail.
- If a multi-step operation fails, all related database changes must roll back.
- Use conditional updates/locking strategy appropriate to SQLite to prevent over-reservation under concurrent requests.
