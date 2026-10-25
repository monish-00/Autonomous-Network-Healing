"""Flask dashboard for service health and incident history.

GET requests only read health and database state. Recovery runs only after an
explicit POST to the manual check action.
"""

import os
import secrets
import hmac
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from app.database.database_manager import DATABASE_PATH, DatabaseManager
from app.monitoring.monitoring_controller import MonitoringController
from app.monitoring.network_monitor import check_host, check_http_health


def create_app(database_path=None):
    app = Flask(__name__)
    app.secret_key = os.environ.get("DASHBOARD_SECRET_KEY") or secrets.token_hex(32)
    resolved_db_path = Path(database_path or DATABASE_PATH)
    app.config["DATABASE_PATH"] = str(resolved_db_path)
    database = DatabaseManager(resolved_db_path)

    @app.get("/")
    def index():
        session.setdefault("form_token", secrets.token_urlsafe(32))
        host = os.environ.get("MONITOR_HOST", "127.0.0.1")
        port = int(os.environ.get("MONITOR_PORT", "8080"))
        path = os.environ.get("HEALTH_PATH", "/health")
        timeout = float(os.environ.get("CHECK_TIMEOUT_SECONDS", "3"))

        tcp_status = check_host(host, port, timeout=timeout)
        http_status = check_http_health(host, port, path=path, timeout=timeout)
        summary = database.get_dashboard_summary()
        return render_template(
            "index.html",
            target=f"{host}:{port}",
            tcp=tcp_status,
            http=http_status,
            summary=summary,
            form_token=session["form_token"],
        )

    @app.post("/check")
    def manual_check():
        submitted_token = request.form.get("form_token", "")
        expected_token = session.get("form_token", "")
        if not expected_token or not hmac.compare_digest(submitted_token, expected_token):
            return "Invalid form token", 400

        result = MonitoringController(database=database).check_target()
        if result["monitoring"]["status"] == "UP":
            flash("Manual check completed: application is healthy.", "success")
        else:
            flash("Manual check completed: application remains unhealthy.", "warning")
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    create_app().run(
        host=os.environ.get("DASHBOARD_BIND_HOST", "127.0.0.1"),
        port=int(os.environ.get("DASHBOARD_PORT", "5000")),
        debug=False,
    )
