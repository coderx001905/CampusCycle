# CampusCycle — Phase 2 Design Decisions

**Status:** Approved by the user on 7 November 2026  
**Purpose:** Authoritative record of V1 business and technical decisions for implementation.

## 1. Approved core decisions

| ID | Area | Approved decision |
|---|---|---|
| D-01 | College membership | Each college representative belongs to exactly one college. |
| D-02 | Platform administration | Platform Admin is a separate global account with `college_id = NULL`. |
| D-03 | Partial transfers | One request may have multiple partial transfer batches. |
| D-04 | Exchange structure | One offered resource per exchange request. |
| D-05 | Transfer audit | Every transfer status change is recorded in `transfer_status_history`. |
| D-06 | Exchange completion | An exchange completes only after both resource movement legs are completed and receipt is confirmed, with no unresolved disputed quantity. |
| D-07 | Inventory reservation | Reserve only the quantity approved for the request, not the entire listing stock. |
| D-08 | Cancellation after dispatch | If any batch has been dispatched, cancellation of remaining unshipped batches requires Platform Admin review. Already-dispatched batches continue through receipt/dispute handling. |
| D-09 | Purchase enquiry | Stock is reserved only after the buyer confirms purchase intention, not on enquiry submission or approval. |
| D-10 | College verification | Pending colleges may browse but cannot transact. |
| D-11 | Transfer creation | The sending college representative creates partial transfer batches. |
| D-12 | Exchange reservation | Reserve both sides atomically immediately after exchange approval. If either reservation fails, roll back both. |
| D-13 | Purchase with insufficient stock | If buyer confirms purchase intention but stock is insufficient, reserve nothing, do not auto-cancel, and leave the request in `awaiting_resolution`. |
| D-14 | Receipt problems | Destination college confirms good quantity and reports damaged/missing quantity as disputed. Disputed quantity is not completed until resolved. |
| D-15 | Additional college users | Authorized College Representatives may create representative accounts for their own college only. They cannot create users for other colleges or Platform Admins. |
| D-16 | Access/refresh tokens | Access-token lifetime target is 15 minutes. Refresh tokens expire after 7 days, rotate on successful use, and support reuse detection. Logout revokes the presented refresh token. Existing access tokens remain valid until expiry unless separate access-token revocation is later adopted. |
| D-17 | Rejected college access | Rejected colleges may browse resources like pending colleges but cannot transact. |
| D-18 | Refresh-token persistence | Add `refresh_tokens` as the seventh table. Store only token hashes, never raw refresh tokens. |
| D-19 | Browser token storage | Store refresh tokens in Secure, HttpOnly cookies with CSRF protection. Do not store long-lived refresh tokens in localStorage. |
| D-20 | Role boundaries | V1 has `platform_admin` and `college_representative` roles with the permissions in Section 2. |
| D-21 | Representative account management | A College Representative may manage/deactivate representative accounts within their own college. The last active representative of a college cannot be deactivated. Platform Admin may manage accounts across colleges. |
| D-22 | Rejected requests | A rejected request remains rejected. A new request must be submitted to try again; rejected requests are not reopened or edited back to pending. |
| D-23 | Pre-dispatch cancellation | If no batch has been dispatched, cancellation is reviewed by an authorized representative of the resource-owning college. Approval releases the unshipped reserved quantity. |
| D-24 | Dispute authority | Platform Admin is the authority for resolving damaged/missing item disputes. |
| D-25 | Dispute outcomes | Allowed outcomes are: accept the verified good quantity/report; approve a replacement transfer; or reject the claim after review. The resolution and evidence/notes must be recorded. |
| D-26 | Dispute inventory handling | Disputed quantities remain held and cannot be reused or marked completed until physical status is verified and the Platform Admin records a resolution. Inventory is adjusted only according to the verified outcome. |

## 2. V1 role and permission matrix

| Action | Platform Admin | College Representative |
|---|---|---|
| View platform-wide colleges and analytics | Yes | No; own-college scope only |
| Verify/reject colleges | Yes | No |
| Browse resources | Yes | Yes, including while college is pending/rejected |
| Create/manage own-college resource listings | Oversight | Yes, own college only |
| Submit requests | No business requirement for admin | Yes, on behalf of own college |
| Approve/reject requests for resources owned by own college | No routine college workflow | Yes, own college only |
| Confirm purchase intention for own submitted request | No | Yes |
| Create/dispatch transfer batches | No routine sender workflow | Yes, source college only |
| Confirm receipt/report damage or missing goods | No routine receiver workflow | Yes, destination college only |
| Create representative accounts | May manage across colleges | Yes, own college only |
| Deactivate representative accounts | Across colleges | Own college only; cannot deactivate last active representative |
| Review pre-dispatch cancellation | No routine role | Resource-owning college representative |
| Review cancellation after any batch dispatched | Yes | May submit request only |
| Resolve transfer disputes | Yes | May report/provide information, not resolve |

All authorization is enforced by the backend. College scope is derived from the authenticated user, never trusted from a client-supplied college ID. A user cannot approve a request on behalf of a different/resource-owning college unless they belong to that college.

## 3. Authentication settings

- Access token: JWT; target lifetime 15 minutes.
- Refresh token: 7-day lifetime.
- Refresh token records: `refresh_tokens` table; persist a cryptographic hash and unique token identifier (`jti`), not the raw token.
- Rotation: issue a replacement refresh token on each successful refresh; mark the prior token as replaced/revoked and retain lineage. Reuse of an already-rotated token revokes the associated token family/session and requires login again.
- Browser transport/storage: Secure, HttpOnly cookie with an appropriate SameSite policy and CSRF protection on refresh/logout. Exact cookie domain/path and deployment-specific SameSite setting are configuration details for implementation.
- Logout: revoke the presented refresh token. Existing access tokens remain valid until their short expiry unless a separate access-token denylist/revocation mechanism is later approved.

## 4. Cancellation and dispute workflow

### Cancellation before dispatch
1. A representative submits a cancellation request with a reason.
2. If no batch has been dispatched, an authorized representative of the resource-owning college reviews it.
3. If approved, cancel the unshipped batch/quantity and release only its reserved quantity. If rejected, retain the existing request/transfer state and reservation.

### Cancellation after dispatch has begun
1. If any batch has been dispatched, Platform Admin reviews cancellation of the remaining unshipped batches.
2. If approved, cancel only unshipped batches and release only their reserved quantity.
3. Already-dispatched batches continue through receipt and dispute resolution; they are not erased or treated as cancelled.

### Damaged/missing goods dispute
1. Destination representative records good, damaged, and missing quantities.
2. Good quantity may be confirmed; damaged/missing quantity remains disputed and held.
3. Platform Admin reviews and records one of the approved outcomes: accept the verified report/good quantity, approve a replacement transfer, or reject the claim after review.
4. Inventory changes only after physical status is verified and the resolution is recorded. The backend must apply the exact quantity effects atomically and preserve the audit trail.
5. A transfer/request cannot be completed while disputed quantity remains unresolved.

V1 stores one aggregate dispute state/resolution summary per transfer batch. A separate disputes table, attachments, and dispute messaging are not included in the approved V1 design.

## 5. Rejected requests and college verification

- Rejected resource requests remain immutable in their rejected state for audit/history. A new request is required for a new attempt.
- Pending and rejected colleges may browse but cannot transact. Verified colleges may transact.

## 6. Technical conventions

- Database: SQLite.
- API prefix: `/api/v1`.
- API style: REST/JSON.
- Authentication: JWT Bearer access token plus refresh-token cookie flow.
- Pagination: `page` and `page_size`; proposed default 20 and maximum 100.
- Timestamps: UTC, serialized as ISO 8601.
- Success/error response conventions and HTTP status mapping are defined in `api-specification.md`.

## 7. Explicit V1 scope guard

Included: college registration/authentication, college/user management, resource listings, donations, exchanges, purchase enquiries (payments outside the app), requests and approvals, inventory/reservations, partial inter-college transfers, receipt confirmation, dispute handling, and analytics.

Excluded: temporary borrowing/rentals/returns, online payment processing, chat/social features, AI recommendations/image recognition, live GPS/route optimization, and a mobile app.

## 8. Implementation boundary

These decisions complete Phase 2 design approval. They do not mean backend code has been created. Phase 3 may begin only when the user explicitly asks to start it.
