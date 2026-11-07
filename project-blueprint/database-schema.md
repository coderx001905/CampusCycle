# CampusCycle V1 — Detailed Database Schema

**Status:** Approved Phase 2 logical schema — implementation not yet created  
**Database:** SQLite  
**Implementation:** Not created. This is a proposed logical schema, not SQLAlchemy model code or a migration.

Conventions:
- Primary keys use integer IDs unless noted otherwise.
- Timestamps are stored in UTC in a consistent ISO-8601-compatible representation (or SQLite integer timestamps if that storage convention is selected consistently during implementation).
- Use `NOT NULL` unless a field is explicitly marked nullable.
- Foreign-key deletion should generally be `RESTRICT` for business records; use deactivation rather than destructive deletion.

## 1. `colleges`

| Column | Type | Null? | Rules / purpose |
|---|---|---:|---|
| `id` | INTEGER | No | Primary key |
| `name` | VARCHAR(200) | No | College name |
| `address` | TEXT | No | Address |
| `city` | VARCHAR(100) | No | City |
| `contact_email` | VARCHAR(255) | No | Contact email |
| `verification_status` | VARCHAR(20) | No | `pending`, `verified`, `rejected`; default `pending` |
| `created_at` | DATETIME | No | Creation time |
| `updated_at` | DATETIME | No | Last update |

## 2. `users`

| Column | Type | Null? | Rules / purpose |
|---|---|---:|---|
| `id` | INTEGER | No | Primary key |
| `college_id` | INTEGER | Yes | FK to `colleges.id`; null only for platform admin |
| `name` | VARCHAR(150) | No | Display name |
| `email` | VARCHAR(255) | No | Unique, normalized/case-insensitive |
| `password_hash` | VARCHAR(255) | No | Never store plaintext password |
| `role` | VARCHAR(30) | No | `platform_admin` or `college_representative` |
| `is_active` | BOOLEAN | No | Account active flag; default true |
| `created_at` | DATETIME | No | Creation time |
| `updated_at` | DATETIME | No | Last update |

Constraints:
- `platform_admin` must have `college_id IS NULL`.
- `college_representative` must have a non-null `college_id`.
- College representatives can create other representative accounts only within their own college.
- A unique normalized email index is required.

## 3. `resources`

| Column | Type | Null? | Rules / purpose |
|---|---|---:|---|
| `id` | INTEGER | No | Primary key |
| `college_id` | INTEGER | No | FK to owning college |
| `created_by_user_id` | INTEGER | No | FK to `users.id` |
| `name` | VARCHAR(200) | No | Resource name |
| `description` | TEXT | Yes | Description |
| `category` | VARCHAR(100) | No | V1 category label |
| `condition` | VARCHAR(30) | No | Condition descriptor; allowed values to standardize |
| `quantity_total` | INTEGER | No | Physical quantity represented by listing |
| `quantity_available` | INTEGER | No | Unreserved quantity |
| `quantity_reserved` | INTEGER | No | Quantity allocated to approved workflows |
| `unit` | VARCHAR(50) | No | e.g. pieces, sets, books |
| `transfer_type` | VARCHAR(20) | No | `donation`, `exchange`, `sale` |
| `indicative_price` | NUMERIC(10,2) | Yes | Informational only; payment external |
| `image_path` | VARCHAR(500) | Yes | Stored path/reference, if image upload is approved |
| `status` | VARCHAR(20) | No | Proposed: `active`, `inactive`, `depleted` |
| `created_at` | DATETIME | No | Creation time |
| `updated_at` | DATETIME | No | Last update |

Constraints:
- All quantities must be non-negative.
- `quantity_available + quantity_reserved = quantity_total`.
- `quantity_reserved <= quantity_total`.
- Resource owner college must be eligible under the verification policy to create/manage transactional listings.
- `sale` means purchase enquiry only; CampusCycle does not collect payment.

## 4. `requests`

| Column | Type | Null? | Rules / purpose |
|---|---|---:|---|
| `id` | INTEGER | No | Primary key |
| `resource_id` | INTEGER | No | FK to requested `resources.id` |
| `requesting_college_id` | INTEGER | No | FK to requesting college |
| `requested_by_user_id` | INTEGER | No | FK to submitting user |
| `offered_resource_id` | INTEGER | Yes | FK to `resources.id`; required for exchange |
| `requested_quantity` | INTEGER | No | Quantity requested from listed resource |
| `offered_quantity` | INTEGER | Yes | Required for exchange |
| `request_type` | VARCHAR(30) | No | `donation`, `exchange`, `purchase_enquiry` |
| `purpose` | TEXT | No | Reason for request |
| `message` | TEXT | Yes | Additional message |
| `status` | VARCHAR(30) | No | Proposed values below |
| `reviewed_by_user_id` | INTEGER | Yes | FK to reviewer |
| `reviewed_at` | DATETIME | Yes | Review timestamp |
| `purchase_intent_confirmed_at` | DATETIME | Yes | Set when buyer confirms intention |
| `purchase_confirmed_by_user_id` | INTEGER | Yes | FK to confirming user |
| `created_at` | DATETIME | No | Creation time |
| `updated_at` | DATETIME | No | Last update |

Proposed request statuses:
- `pending`
- `approved`
- `rejected`
- `in_progress`
- `awaiting_resolution` — e.g. purchase intent confirmed but requested stock is no longer available
- `completed`
- `cancelled`

Constraints / validation:
- `requested_quantity > 0`.
- For `exchange`, `offered_resource_id` and `offered_quantity` are required and positive.
- For non-exchange requests, offered-resource fields must be null.
- The offered resource must belong to the requesting college.
- The requested resource must belong to a different college.
- Purchase enquiry approval alone does not reserve stock. Reservation is attempted on purchase-intent confirmation.
- On insufficient stock at purchase confirmation, no reservation is made and the request remains open in `awaiting_resolution`.
- `awaiting_resolution` must not be treated as `cancelled` or `completed`.

## 5. `transfers`

| Column | Type | Null? | Rules / purpose |
|---|---|---:|---|
| `id` | INTEGER | No | Primary key |
| `request_id` | INTEGER | No | FK to `requests.id` |
| `resource_id` | INTEGER | No | FK to resource being moved |
| `transfer_leg` | VARCHAR(30) | No | `requested_resource` or `offered_resource`; exchange uses both |
| `source_college_id` | INTEGER | No | FK to source college |
| `destination_college_id` | INTEGER | No | FK to destination college |
| `quantity` | INTEGER | No | Quantity in this batch |
| `quantity_received_good` | INTEGER | Yes | Good quantity confirmed by destination |
| `quantity_damaged` | INTEGER | Yes | Damaged quantity reported |
| `quantity_missing` | INTEGER | Yes | Missing quantity reported |
| `dispute_status` | VARCHAR(30) | No | Proposed: `none`, `open`, `resolved` |
| `dispute_resolution` | TEXT | Yes | Platform Admin resolution summary and rationale |
| `dispute_outcome` | VARCHAR(30) | Yes | `accept_report`, `replacement_approved`, or `claim_rejected`; set only when resolved |
| `replacement_for_transfer_id` | INTEGER | Yes | Self-FK to original disputed transfer; set on a replacement batch |
| `dispute_resolved_by_user_id` | INTEGER | Yes | FK to Platform Admin who resolves the dispute |
| `dispute_resolved_at` | DATETIME | Yes | Resolution timestamp |
| `created_by_user_id` | INTEGER | No | FK to sender-side representative |
| `dispatched_by_user_id` | INTEGER | Yes | FK to dispatching user |
| `received_by_user_id` | INTEGER | Yes | FK to receiving user |
| `pickup_or_delivery_date` | DATETIME | Yes | Planned date |
| `status` | VARCHAR(30) | No | Proposed values below |
| `dispatch_notes` | TEXT | Yes | Dispatch notes |
| `receipt_confirmation` | TEXT | Yes | Receipt note/confirmation |
| `received_at` | DATETIME | Yes | Receipt timestamp |
| `cancellation_requested_by_user_id` | INTEGER | Yes | FK to requester |
| `cancellation_requested_at` | DATETIME | Yes | Cancellation request time |
| `cancellation_reason` | TEXT | Yes | Reason |
| `cancellation_reviewed_by_user_id` | INTEGER | Yes | FK to reviewing user: resource-owning college representative before any dispatch; Platform Admin after dispatch has begun |
| `cancellation_reviewed_at` | DATETIME | Yes | Review time |
| `cancellation_decision` | VARCHAR(20) | Yes | `approved` or `rejected` |
| `created_at` | DATETIME | No | Creation time |
| `completed_at` | DATETIME | Yes | Completion time |

Proposed transfer statuses:
- `preparing`
- `dispatched`
- `partially_received`
- `disputed`
- `received`
- `completed`
- `cancellation_pending`
- `cancelled`

Validation:
- `quantity > 0`.
- Received-good + damaged + missing quantities cannot exceed dispatched quantity.
- A transfer cannot be completed while a disputed quantity remains unresolved.
- A replacement batch must reference the disputed original batch in `replacement_for_transfer_id`; replacement quantity must be reserved from available stock before dispatch.
- The sum of batch quantities for a request movement leg cannot exceed that leg's approved quantity.
- Only the source college's authorized representative may create/dispatch a batch.
- Only the destination college's authorized representative may confirm receipt.
- If no batch has been dispatched, an authorized representative of the resource-owning college reviews the cancellation.
- If any batch has been dispatched, cancellation of remaining unshipped batches requires Platform Admin approval.
- Approval of cancellation releases only unshipped reserved quantities. Dispatched batches continue through receipt/dispute handling.

**V1 dispute model:** This single-row representation supports one aggregate dispute per transfer batch. Platform Admin resolves disputes. Store the selected outcome in `dispute_outcome` and the rationale in `dispute_resolution`. For a replacement outcome, create a new transfer batch linked to the original using `replacement_for_transfer_id`; reserve replacement stock before dispatch. Disputed quantities remain held until physical status is verified and the resolution is recorded. A dedicated disputes table, attachments, or dispute messaging are not included in V1.

## 6. `transfer_status_history`

| Column | Type | Null? | Rules / purpose |
|---|---|---:|---|
| `id` | INTEGER | No | Primary key |
| `transfer_id` | INTEGER | No | FK to `transfers.id` |
| `changed_by_user_id` | INTEGER | Yes | FK to user; null for system event |
| `actor_type` | VARCHAR(20) | No | `user` or `system` |
| `previous_status` | VARCHAR(30) | Yes | Null for initial event |
| `new_status` | VARCHAR(30) | No | Status after change |
| `notes` | TEXT | Yes | Reason/context |
| `changed_at` | DATETIME | No | Event timestamp |

Every transfer status change must create a history record in the same transaction as the status update.

## 7. `refresh_tokens` — approved supporting table

This is the approved seventh table, added to support refresh-token rotation and reliable logout revocation.

| Column | Type | Null? | Rules / purpose |
|---|---|---:|---|
| `id` | INTEGER | No | Primary key |
| `user_id` | INTEGER | No | FK to `users.id` |
| `token_hash` | VARCHAR(255) | No | Store hash, never raw refresh token |
| `jti` | VARCHAR(100) | No | Unique token identifier |
| `token_family_id` | VARCHAR(100) | No | Identifies one login/session token family so reuse detection can revoke the full family |
| `expires_at` | DATETIME | No | Expiration |
| `revoked_at` | DATETIME | Yes | Set on logout/revocation |
| `created_at` | DATETIME | No | Issued time |
| `replaced_by_token_id` | INTEGER | Yes | Optional self-FK for rotation lineage |
| `user_agent` | VARCHAR(500) | Yes | Optional device/session context |
| `ip_address` | VARCHAR(64) | Yes | Optional; assess privacy/retention policy |

Rules:
- Raw refresh tokens are returned only at issuance and are never stored in plaintext; persist a cryptographic hash.
- Refresh checks signature/identifier, hash, expiry, revocation, token-family state, and user active state.
- Refresh-token lifetime is 7 days.
- Rotate the refresh token on every successful refresh; record replacement lineage. Detect reuse of a rotated token and revoke the associated token family/session.
- Logout revokes the presented refresh token.
- For browser clients, use a Secure, HttpOnly cookie with an appropriate SameSite policy and CSRF protection on refresh/logout. Do not use localStorage for long-lived refresh tokens.
- Access-token lifetime target is 15 minutes. Already-issued access tokens remain valid until expiry unless a separate access-token revocation mechanism is later approved.

## 8. Indexes

Recommended indexes:
- `users(email)` unique, normalized/case-insensitive.
- `users(college_id, is_active)`.
- `resources(college_id, status)`.
- `resources(category, status)`.
- `resources(transfer_type, status)`.
- `requests(resource_id, status)`.
- `requests(requesting_college_id, status)`.
- `requests(request_type, status)`.
- `transfers(request_id, transfer_leg, status)`.
- `transfers(source_college_id, status)`.
- `transfers(destination_college_id, status)`.
- `transfer_status_history(transfer_id, changed_at)`.
- `refresh_tokens(user_id, expires_at)`.
- `refresh_tokens(jti)` unique.
- `refresh_tokens(token_family_id, revoked_at)` for session-family revocation and reuse detection.
- `refresh_tokens(token_hash)` unique.

## 9. Rules requiring service-layer enforcement

SQLite CHECK constraints cannot conveniently enforce all cross-row or cross-table rules. The service layer must enforce:
- College ownership and role permissions.
- Request and resource college relationship.
- Exchange two-sided atomic reservation.
- Request movement-leg quantity totals across multiple transfer rows.
- Purchase confirmation stock availability.
- Cancellation eligibility and reviewer selection: resource-owning college representative before any dispatch; Platform Admin once any batch has been dispatched.
- Transfer receipt/dispute transitions and Platform Admin-only dispute resolution.
- Representative account deactivation must not deactivate the last active representative of a college.
- Rejected requests remain rejected; a new request is required for resubmission.
- Request completion only after all required movement legs are completed.
- Refresh-token rotation/revocation lifecycle.

Use explicit transactions and concurrency-safe conditional updates for stock reservation. A failed multi-resource reservation must roll back all updates.
