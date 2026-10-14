# Local PostgreSQL setup

PostgreSQL 18 is configured specifically for this project. It runs as a background process, separately from the existing stopped Windows services.

- Host: `127.0.0.1`
- Port: `5433`
- Database: `dealerdesk`
- Application role: `vikmo_app` (non-superuser; allowed to create the disposable test database)
- Credentials: generated and stored in the ignored `.env`
- Database files and server log: ignored `local_data/`

From the repository root:

```powershell
.venv\Scripts\python.exe scripts/local_postgres.py start
.venv\Scripts\python.exe manage.py runserver
```

In another terminal:

```powershell
cd frontend
npm run dev
```

Open http://127.0.0.1:8000 for the compiled application, or http://localhost:5173 for frontend development with hot reload. Django serves the existing `frontend/dist` build at the root and known React routes; development assets are served when `DEBUG` is enabled. Rebuild after frontend changes with `npm run build` in `frontend/`. Before a build exists, the root redirects to the frontend development server. Production hosting must serve `frontend/dist/assets` and `favicon.svg` through the web server.

Django admin is at http://127.0.0.1:8000/admin/. To create your own staff login:

```powershell
.venv\Scripts\python.exe manage.py createsuperuser
```

Database management:

```powershell
.venv\Scripts\python.exe scripts/local_postgres.py status
.venv\Scripts\python.exe scripts/local_postgres.py stop
```

All migrations have been applied. The supplied CSV catalogue is seeded with 600 products and 25 dealers. The 28 core, supplier-sync, and forecasting tests pass against PostgreSQL; their disposable database was removed afterward. Live health, catalogue, dealers, orders, and reorder APIs return HTTP 200.

Package downloads were unavailable in this session. The local `.venv` therefore uses the already available Python packages and `.validation-deps` through a local path file. Keep `.validation-deps` while using this environment. When package downloads are available, install the full existing `requirements.txt` to also run the assistant SDK tests.
