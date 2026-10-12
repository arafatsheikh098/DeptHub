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

## Testing & Linting

```bash
# Run test suite
pytest -v

# Run linting checks
ruff check .
ruff format --check .
```
