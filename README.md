# Autonomous Network Healing Platform

A small Python portfolio project that monitors a local service over TCP and HTTP, records alarms and incident events in SQLite, and tries a constrained recovery action for its controlled test service. The dashboard shows current health and persisted history without running recovery during page loads.

## Features

- TCP connectivity checks with measured response time and connection error classification.
- HTTP `/health` checks that validate both HTTP 200 and `{"status": "healthy"}`.
- Persistent alarm lifecycle, repeated-failure occurrence counts, and incident events.
- Measured recovery duration and outcome persistence.
- Independent TCP and HTTP verification after recovery; a reachable port alone is not considered application recovery.
- Local Flask dashboard with active alarms, recent incidents, and recovery statistics.
- Unit tests use isolated temporary SQLite files and mocked network/recovery dependencies.

Fault labels are simple rules such as `CONNECTION_REFUSED`, `TIMEOUT`, `HTTP_ERROR`, `INVALID_HEALTH_RESPONSE`, and `UNHEALTHY_RESPONSE`. This is basic diagnostic classification, not machine learning or advanced root cause analysis.

## Requirements and setup

Python 3.10 or newer is recommended. Runtime dependencies are listed in `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate with `source .venv/bin/activate` and replace Windows path separators in commands as needed.

## Run the components

Start the controlled HTTP test service in one terminal:

```powershell
python -m app.monitoring.test_service
```

Run a monitoring cycle in a second terminal:

```powershell
python -m app.monitoring.monitoring_controller
```

Start the dashboard in another terminal:

```powershell
python -m dashboard.web_app
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). A dashboard page load performs read-only TCP and HTTP checks and reads SQLite. Select **Run check and recovery** to explicitly run the controller workflow. The action is a POST protected by a session token; refreshing the page does not trigger recovery.

To exercise recovery, stop the test service and run a monitoring cycle. The recovery helper can start only the project's local test service; it does not restart arbitrary remote processes. If the TCP port is already open while HTTP is unhealthy, the helper reports that it cannot safely restart the controlled service and the alarm remains active.

## Configuration

Environment variables are optional:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MONITOR_HOST` | `127.0.0.1` | Target host for controller and dashboard health checks |
| `MONITOR_PORT` | `8080` | Target service port |
| `HEALTH_PATH` | `/health` | HTTP health endpoint path |
| `CHECK_TIMEOUT_SECONDS` | `3` | TCP and HTTP check timeout |
| `NETWORK_HEALING_DB` | `<project>/network_healing.db` | SQLite file path |
| `TEST_SERVICE_HOST` | `127.0.0.1` | Host used when manually starting the test service |
| `TEST_SERVICE_PORT` | `8080` | Port used when manually starting the test service |
| `DASHBOARD_BIND_HOST` | `127.0.0.1` | Dashboard bind address; loopback by default |
| `DASHBOARD_PORT` | `5000` | Dashboard port |
| `DASHBOARD_SECRET_KEY` | Random per process | Optional stable Flask session key |

For PowerShell, for example:

```powershell
$env:MONITOR_PORT = "8081"
$env:TEST_SERVICE_PORT = "8081"
$env:NETWORK_HEALING_DB = ".\data\network_healing.db"
```

The parent directory for a custom database path must already exist. Local database files, logs, and virtual environments are ignored by Git; the existing `network_healing.db` is retained as application data and is not used by tests.

## Tests and checks

Run the project tests and syntax check:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app tests dashboard
git diff --check
```

Tests do not require the local service or external network access. They use temporary databases under the test directory, which are removed after each test.

## Project layout

```text
app/
  database/database_manager.py       SQLite schema and persistence
  fault_management/alarm_manager.py  Alarm lifecycle coordination
  monitoring/network_monitor.py      TCP and HTTP checks/classification
  monitoring/monitoring_controller.py Monitoring, recovery, verification
  monitoring/test_service.py         Controlled local HTTP test service
  recovery/service_recovery.py       Constrained local service recovery
dashboard/
  web_app.py                         Flask routes and app factory
  templates/index.html               Dashboard page
  static/style.css                   Dashboard styling
docs/architecture.md                Design, data model, and limitations
tests/                               Isolated automated tests
```

See [docs/architecture.md](docs/architecture.md) for workflow and schema details.

## Limitations and future work

- The recovery action is intentionally limited to launching this repository's local test server. It does not manage a production service supervisor or remote host.
- Monitoring is run on demand; there is no background scheduler or historical time-series store.
- Current health shown on the dashboard is checked at page request time and is not persisted as a poll record.
- Rule-based fault labels are only a starting point. More precise platform-specific error handling, authentication, authorization, audit controls, and deployment hardening would be needed before exposing the dashboard beyond localhost.
- SQLite is suitable for this single-process demonstration. A multi-worker deployment would need stronger coordination and likely a server database.
