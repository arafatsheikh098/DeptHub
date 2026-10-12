# Deployment Guide (Render)

This guide provides step-by-step instructions for deploying DeptHub to [Render](https://render.com) using Docker and Managed PostgreSQL.

---

## 1. Prerequisites

1. A [Render](https://render.com) account.
2. A GitHub or GitLab repository containing DeptHub code.
3. Git CLI and modern web browser.

---

## 2. Deployment Steps (Click-by-Click)

### Option A: Using Blueprint (`render.yaml` - Recommended)

1. Log in to your Render Dashboard.
2. Click **Blueprints** in the top navigation bar.
3. Click **New Blueprint Instance**.
4. Connect your DeptHub repository.
5. Render detects `render.yaml` and prepares two resources:
   - **depthub-db**: PostgreSQL Managed Database
   - **depthub**: Web Service (Docker)
6. Under Service Environment Variables, configure:
   - `PUBLIC_BASE_URL`: Set to your Render web service URL (e.g., `https://depthub.onrender.com`).
7. Click **Apply**.
8. Render will provision the database, build the Docker container, run migrations (`alembic upgrade head`), and boot the application server.

---

### Option B: Manual Setup via Dashboard

#### Step 1: Create PostgreSQL Database
1. In Render Dashboard, click **New +** > **PostgreSQL**.
2. Configure database settings:
   - **Name**: `depthub-db`
   - **Database**: `depthub`
   - **User**: `depthub`
   - **Region**: Same region as your web service (e.g., `Oregon (US West)` or `Frankfurt (EU Central)`)
   - **Instance Type**: `Free`
3. Click **Create Database**.
4. Copy the **Internal Database URL** from the database settings page.

#### Step 2: Create Web Service
1. In Render Dashboard, click **New +** > **Web Service**.
2. Connect your Git repository.
3. Configure service settings:
   - **Name**: `depthub`
   - **Region**: Same region as the database
   - **Language / Runtime**: `Docker`
   - **Instance Type**: `Free`
   - **Health Check Path**: `/health`
4. Add the Environment Variables (see table below).
5. Click **Create Web Service**.

---

## 3. Environment Variables Reference

| Variable Name | Purpose | Example | Required? |
| :--- | :--- | :--- | :--- |
| `ENV` | Application runtime mode. Must be `production` to enforce Secure cookies and disable development secrets. | `production` | **Yes** |
| `SECRET_KEY` | Cryptographic secret for signing session cookies and CSRF tokens. Boot fails if insecure or default. | `generateValue: true` or 32+ random hex bytes | **Yes** |
| `DATABASE_URL` | PostgreSQL connection URL. Normalized automatically to `postgresql+psycopg://`. | `postgresql://depthub:...@dpg-...:5432/depthub` | **Yes** |
| `PUBLIC_BASE_URL` | Public canonical base URL used in Atom feeds and absolute links. | `https://depthub.onrender.com` | **Yes** |
| `TIMEZONE` | IANA timezone for localized routine calculation and display. | `Asia/Dhaka` | No (default: `Asia/Dhaka`) |
| `FORWARDED_ALLOW_IPS`| Trusted proxy IPs for Uvicorn reverse proxy headers. | `*` | No (default: `*`) |
| `TERM_START` | Academic semester start date for `.ics` recurrence rules (YYYY-MM-DD). | `2026-01-01` | No (default: `2026-01-01`) |
| `TERM_END` | Academic semester end date for `.ics` recurrence rules (YYYY-MM-DD). | `2026-06-30` | No (default: `2026-06-30`) |
| `ADMIN_EMAIL` | Optional email to seed the initial administrator account on startup. | `admin@dept.university.edu` | Optional |
| `ADMIN_PASSWORD` | Optional password for the initial administrator account. | `ComplexSecretPass!987` | Optional |

---

## 4. Creating the First Admin User

There are two supported ways to create the initial admin user:

### Method 1: Render Web Shell (Recommended)
1. Go to your Web Service in the Render Dashboard.
2. Click the **Shell** tab.
3. Run the interactive CLI command:
   ```bash
   python -m app.cli create-admin
   ```
4. Enter the administrator email and choose a secure password.
5. Log in at `https://<YOUR-RENDER-URL>/auth/login`.

### Method 2: Initial Boot Environment Variables
Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in your Render Environment Variables. On the first startup, DeptHub seeds this administrator automatically if no admin user exists in the database.

---

## 5. Rollback Procedure

If a deployment introduces an issue:
1. In Render Dashboard, click your `depthub` Web Service.
2. Click the **Deploys** tab.
3. Locate the previous successful deploy.
4. Click the three dots `...` next to that deploy and select **Rollback to this deploy**.
5. To roll back database schema migrations if needed:
   - Open the **Shell** tab.
   - Run:
     ```bash
     alembic downgrade -1
     ```

---

## 6. Free Tier Limits & Caveats

> [!WARNING]
> Verify these platform constraints before running an important live demonstration or academic deadline:

- **Web Service Idle Sleep (Spindown)**:
  - On the Render Free tier, web services spin down after **15 minutes** of inactivity.
  - The first incoming request after spindown may experience a cold-start delay of **30–50 seconds**.
- **Managed PostgreSQL Expiry**:
  - Render Free PostgreSQL databases expire **30 days** after creation.
  - *CHECK BEFORE DEPLOYING*: For permanent production, upgrade to a paid Starter database tier ($7/month) or backup data regularly.
- **Outbound Bandwidth**:
  - Render Free includes 100 GB/month outbound bandwidth.
- **Container Build Concurrency**:
  - 1 concurrent build on the free plan. Builds take approximately 1–2 minutes.
