# CampusCycle Frontend

The CampusCycle frontend is a modern web application designed for inter-collegiate resource redistribution, listing management, inventory reservations, requests, and logistics tracking.

Built with **React 19**, **Vite 8**, **Tailwind CSS v4**, **Lucide React**, and **Axios**.

---

## 1. Quick Start & Local Development

### Prerequisites

- **Node.js**: v18.x or later (v20+ recommended)
- **npm**: v9.x or later
- **FastAPI Backend**: Running at `http://127.0.0.1:8000` (see `backend/README.md`)

### Setup Instructions

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```
   The application will be accessible at: `http://localhost:5173`.
   
   The development server includes a configured Vite proxy (`vite.config.js`) that forwards all `/api` requests directly to `http://127.0.0.1:8000`, preserving cookies and avoiding CORS origin mismatches.

3. **Run automated unit tests**:
   ```bash
   npm test
   ```
   Runs automated tests validating API client configuration, in-memory token management, CSRF extraction, and interceptor behaviors.

4. **Lint code**:
   ```bash
   npm run lint
   ```

5. **Build production bundle**:
   ```bash
   npm run build
   ```
   Production assets are generated in `frontend/dist/`.

---

## 2. Architecture & Directory Structure

```text
frontend/
├── src/
│   ├── api/                     # Backend API integration layer
│   │   ├── client.js            # Central Axios instance with interceptors & CSRF handling
│   │   ├── client.test.js       # Node test runner suite for API client
│   │   ├── analytics.js         # Analytics endpoints (summary, categories, requests, transfers, colleges)
│   │   ├── analytics.test.js    # Unit tests for analytics API client
│   │   ├── auth.js              # Authentication endpoints (login, register, refresh, logout)
│   │   ├── accounts.js          # College and user management endpoints
│   │   ├── resources.js         # Listings, inventory, and image upload endpoints
│   │   ├── requests.js          # Resource requests, approvals, and cancellations
│   │   └── transfers.js         # Logistics batches, dispatch, receipts, and disputes
│   ├── components/
│   │   ├── admin/               # Platform Admin views
│   │   │   ├── CollegeVerificationView.jsx  # College verification workflow
│   │   │   └── DisputeManagementView.jsx    # Disputed transfer resolution
│   │   ├── auth/                # Authentication modals
│   │   │   ├── LoginModal.jsx
│   │   │   └── RegisterModal.jsx
│   │   ├── common/              # Reusable UI components
│   │   │   └── NotificationToast.jsx
│   │   ├── modals/              # Action dialogs
│   │   │   ├── DisputeResolutionModal.jsx
│   │   │   ├── ReceiptModal.jsx
│   │   │   ├── TransferCreateModal.jsx
│   │   │   └── TransferHistoryModal.jsx
│   │   └── settings/            # College settings & team management
│   │       └── CollegeSettingsView.jsx
│   ├── context/
│   │   └── AuthContext.jsx      # Global authentication provider & session lifecycle
│   ├── pages/                   # Application view modules
│   │   ├── DashboardView.jsx    # Live metrics, summary KPIs, and recent activity
│   │   ├── AnalyticsView.jsx    # Real-time aggregated metrics, fulfillment, and logistics analytics
│   │   ├── MarketplaceView.jsx  # Browse, search, filter, and request resources
│   │   ├── MyListingsView.jsx   # Create and manage owned resource listings
│   │   ├── MyRequestsView.jsx   # Sent & received requests, approvals, and cancellations
│   │   ├── InventoryView.jsx    # Real-time inventory levels (total, reserved, available)
│   │   └── TransfersView.jsx    # Logistics tracking, dispatch, and inspection
│   ├── App.jsx                  # Main application shell, topbar, navigation, routing
│   └── main.jsx                 # Entry point with AuthProvider wrapper
├── vite.config.js               # Vite config with /api development proxy
└── package.json
```

---

## 3. Security & Authentication Architecture

1. **In-Memory Access Tokens**:
   - Access tokens are stored strictly in memory within `client.js`.
   - Access tokens are never written to `localStorage` or `sessionStorage`, mitigating token theft via Cross-Site Scripting (XSS).

2. **HttpOnly Cookie Refresh Tokens**:
   - Long-lived refresh tokens are stored in secure `HttpOnly` cookies set by the backend (`campuscycle_refresh`).
   - JavaScript cannot read this cookie directly.

3. **CSRF Protection**:
   - The backend provides a readable `campuscycle_csrf` cookie.
   - The Axios request interceptor automatically extracts this cookie and includes it as the `X-CSRF-Token` header on state-changing authentication endpoints (`/auth/refresh` and `/auth/logout`).

4. **Silent Refresh & Concurrency Queue**:
   - On application startup, `AuthContext` calls `/auth/refresh` to restore user sessions silently.
   - When any protected API request encounters an expired token (`401 Unauthorized`), the Axios response interceptor intercepts the error, queues concurrent requests, initiates a single refresh request, updates the token, and replays all queued calls.

5. **Role-Based Access Control (RBAC)**:
   - **Platform Admin**: Global oversight, verifying pending colleges, and resolving transfer disputes.
   - **College Representative**: Operates within their own college to manage listings, submit/approve requests, create transfer batches, and inspect deliveries.
   - **Unverified College**: Restricted from creating listings, requesting items, or initiating transfers until verified by Platform Admin.
