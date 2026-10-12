# DeptHub

Notice board, class routine, and exam schedule for a university department.

## Quick Start (Local Development)

```bash
# 1. Clone repository
git clone <repo-url>
cd depthub

# 2. Setup virtual environment & dependencies
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 3. Run database migrations
alembic upgrade head

# 4. Start local development server
uvicorn app.main:app --reload --port 8000
```

Visit [http://localhost:8000](http://localhost:8000) or check health at [http://localhost:8000/health](http://localhost:8000/health).

## Feeds & Calendar Subscriptions

DeptHub provides real-time feeds without requiring user accounts or email setups:

### 1. Notice Board Atom Feed
- **URL**: `http://localhost:8000/feeds/notices.atom`
- Compatible with any RSS/Atom reader (e.g. NetNewsWire, Feedly, Thunderbird).

### 2. Batch Routine & Exam Calendar (.ics)
- **URL**: `http://localhost:8000/feeds/batch/{batch_id}.ics`
- Includes recurring weekly class timetable events and upcoming exam schedules with location and instructor details.

#### How to subscribe:
- **Google Calendar**:
  1. Open Google Calendar on web.
  2. In the left sidebar, click **+** next to *Other calendars* → select **From URL**.
  3. Paste the `.ics` link (e.g., `https://your-domain.com/feeds/batch/1.ics`) and click **Add calendar**.
- **Apple Calendar (iOS / macOS)**:
  1. Open Apple Calendar.
  2. Select **File** → **New Calendar Subscription** (or Settings → Calendar → Accounts → Add Subscribed Calendar on iOS).
  3. Enter the `.ics` URL and set the auto-refresh frequency (e.g., Every hour or Every day).
- **Microsoft Outlook**:
  1. Open Outlook Calendar.
  2. Click **Add calendar** → **Subscribe from web**.
  3. Paste the `.ics` URL, name the calendar (e.g. "DeptHub Schedule"), and click **Import**.

