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

| Method | Endpoint | Purpose / access |
|---|---|---|
| POST | `/requests/{request_id}/transfers` | Create a partial transfer batch; source college representative |
| GET | `/transfers` | Participating college scoped list |
| GET | `/transfers/{transfer_id}` | Source/destination college or platform administrator |
| POST | `/transfers/{transfer_id}/dispatch` | Source college representative |
| POST | `/transfers/{transfer_id}/receipt` | Destination college representative; supports good/damaged/missing quantities |
| POST | `/transfers/{transfer_id}/cancel` | Submit cancellation request; decision routed to resource-owning college representative before any dispatch or Platform Admin after dispatch has begun |
| POST | `/transfers/{transfer_id}/cancellation-decision` | Resource-owning college representative if no batch has been dispatched; Platform Admin if any batch has been dispatched |
| POST | `/transfers/{transfer_id}/dispute-resolution` | Platform Admin only; records approved outcome and inventory adjustment |
| GET | `/transfers/{transfer_id}/history` | Participating college or platform administrator |

### Receipt payload (illustrative)

```json
{
  "quantity_received_good": 25,
  "quantity_damaged": 3,
  "quantity_missing": 2,
  "receipt_confirmation": "25 chairs received in good condition; 3 damaged; 2 missing."
}
```

Validation:
- The three quantities must be non-negative.
- Their sum must equal the dispatched quantity for a fully reconciled receipt report, unless the business later explicitly allows an unknown/unverified remainder.
- Good quantity can be confirmed.
- Damaged/missing quantity opens a dispute and cannot be marked completed until Platform Admin records a resolution.
- Approved outcomes: accept the verified report/good quantity, approve a replacement transfer, or reject the claim after review.
- Disputed quantities remain held until physical status is verified and the resolution is recorded; inventory is adjusted only according to the verified outcome, in the same transaction as the resolution and audit record.

### Cancellation behavior

If no batch has been dispatched, an authorized representative of the resource-owning college reviews the cancellation request. If any batch has been dispatched, Platform Admin reviews cancellation of remaining unshipped batches.

If any batch has been dispatched:
- the college submits a cancellation request;
- Platform Admin approves or rejects;
- only unshipped batches may be cancelled;
- reserved quantity for approved cancelled unshipped batches is released;
- already-dispatched batches continue through receipt/dispute resolution.

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
