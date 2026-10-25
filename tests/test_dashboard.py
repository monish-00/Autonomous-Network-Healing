import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.database.database_manager import DatabaseManager
from app.fault_management.alarm_manager import AlarmManager
from dashboard.web_app import create_app


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.database_path = Path(self.temp_dir.name) / "dashboard.db"
        self.database = DatabaseManager(self.database_path)
        self.app = create_app(self.database_path)
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("dashboard.web_app.check_host")
    @patch("dashboard.web_app.check_http_health")
    @patch("dashboard.web_app.MonitoringController")
    def test_dashboard_renders_health_and_incident_history_without_recovery(
        self, controller, http_check, tcp_check
    ):
        tcp_check.return_value = {
            "status": "UP", "response_time_ms": 1.2, "error": None, "fault_type": None
        }
        http_check.return_value = {
            "status": "UP", "http_status_code": 200, "response_time_ms": 2.3,
            "error": None, "fault_type": None
        }
        alarm_manager = AlarmManager(self.database)
        alarm_manager.process_status("127.0.0.1:8080", "DOWN", "CONNECTION_REFUSED")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"TCP CONNECTIVITY", response.data)
        self.assertIn(b"CONNECTION_REFUSED", response.data)
        self.assertIn(b"ALARM_CREATED", response.data)
        controller.assert_not_called()
        self.assertTrue(self.database_path.exists())

    @patch("dashboard.web_app.MonitoringController")
    def test_manual_check_is_explicit_post_action(self, controller_class):
        controller = Mock()
        controller.check_target.return_value = {"monitoring": {"status": "UP"}}
        controller_class.return_value = controller
        page = self.client.get("/")
        token = page.data.decode().split('name="form_token" value="')[1].split('"')[0]
        response = self.client.post("/check", data={"form_token": token})
        self.assertEqual(response.status_code, 302)
        controller.check_target.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
