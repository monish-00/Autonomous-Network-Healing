import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database.database_manager import DatabaseManager
from app.fault_management.alarm_manager import AlarmManager
from app.monitoring import monitoring_controller
from app.monitoring.monitoring_controller import MonitoringController


def _result(status):
    return {"status": status, "url": "http://test/health", "error": None}


def _controller(db_path):
    controller = MonitoringController.__new__(MonitoringController)
    controller.host = "127.0.0.1"
    controller.port = 8080
    controller.health_path = "/health"
    controller.timeout = 3.0
    controller.alarm_manager = AlarmManager(
        DatabaseManager(db_path)
    )
    from app.recovery.service_recovery import ServiceRecovery

    controller.recovery_manager = ServiceRecovery(controller.host, controller.port)
    return controller


class MonitoringControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.controller = _controller(Path(self.temp_dir.name) / "controller.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_healthy_monitoring_does_not_attempt_recovery(self):
        with patch.object(monitoring_controller, "check_host", return_value=_result("UP")), \
             patch.object(monitoring_controller, "check_http_health", return_value=_result("UP")), \
             patch.object(self.controller.recovery_manager, "recover", side_effect=AssertionError("unexpected recovery")):
            result = self.controller.check_target()
        self.assertIsNone(result["recovery"])
        self.assertEqual(result["active_alarms"], [])


    def test_successful_recovery_verifies_http_persists_duration_and_resolves(self):
        tcp_results = iter((_result("DOWN"), _result("UP")))
        http_results = iter((_result("DOWN"), _result("UP")))
        recovery = {"success": True, "recovery_time_seconds": 2.537, "message": "restarted"}
        with patch.object(monitoring_controller, "check_host", side_effect=lambda *_, **__: next(tcp_results)), \
             patch.object(monitoring_controller, "check_http_health", side_effect=lambda *_, **__: next(http_results)), \
             patch.object(self.controller.recovery_manager, "recover", return_value=recovery):
            result = self.controller.check_target()

        row = self.controller.alarm_manager.get_all_alarms()[0]
        self.assertEqual(result["monitoring"]["status"], "UP")
        self.assertEqual(row["status"], "RESOLVED")
        self.assertEqual(row["recovery_success"], 1)
        self.assertEqual(row["recovery_duration"], 2.537)


    def test_failed_recovery_or_failed_http_verification_leaves_alarm_active(self):
        tcp_results = iter((_result("DOWN"), _result("UP")))
        http_results = iter((_result("DOWN"), _result("DOWN")))
        recovery = {"success": True, "recovery_time_seconds": 1.25, "message": "started"}
        with patch.object(monitoring_controller, "check_host", side_effect=lambda *_, **__: next(tcp_results)), \
             patch.object(monitoring_controller, "check_http_health", side_effect=lambda *_, **__: next(http_results)), \
             patch.object(self.controller.recovery_manager, "recover", return_value=recovery):
            result = self.controller.check_target()

        row = self.controller.alarm_manager.get_all_alarms()[0]
        self.assertTrue(result["active_alarms"])
        self.assertFalse(result["recovery"]["success"])
        self.assertTrue(result["recovery"]["attempt_success"])
        self.assertFalse(result["recovery"]["http_verified"])
        self.assertEqual(row["status"], "ACTIVE")
        self.assertEqual(row["recovery_success"], 0)
        self.assertEqual(row["recovery_duration"], 1.25)

    def test_unsuccessful_recovery_does_not_resolve_even_if_http_is_up(self):
        tcp_results = iter((_result("DOWN"), _result("UP")))
        http_results = iter((_result("DOWN"), _result("UP")))
        recovery = {"success": False, "recovery_time_seconds": 3.1, "message": "failed"}
        with patch.object(monitoring_controller, "check_host", side_effect=lambda *_, **__: next(tcp_results)), \
             patch.object(monitoring_controller, "check_http_health", side_effect=lambda *_, **__: next(http_results)), \
             patch.object(self.controller.recovery_manager, "recover", return_value=recovery):
            result = self.controller.check_target()

        row = self.controller.alarm_manager.get_all_alarms()[0]
        self.assertEqual(result["monitoring"]["status"], "DOWN")
        self.assertTrue(result["active_alarms"])
        self.assertEqual(row["status"], "ACTIVE")
        self.assertEqual(row["recovery_success"], 0)
        self.assertEqual(row["recovery_duration"], 3.1)

    def test_tcp_reachable_but_http_unhealthy_still_creates_alarm(self):
        tcp_results = iter((_result("UP"), _result("UP")))
        http_results = iter((_result("DOWN"), _result("DOWN")))
        recovery = {"success": True, "recovery_time_seconds": 0.4, "message": "checked"}
        with patch.object(monitoring_controller, "check_host", side_effect=lambda *_, **__: next(tcp_results)), \
             patch.object(monitoring_controller, "check_http_health", side_effect=lambda *_, **__: next(http_results)), \
             patch.object(self.controller.recovery_manager, "recover", return_value=recovery):
            result = self.controller.check_target()

        row = self.controller.alarm_manager.get_all_alarms()[0]
        self.assertEqual(result["tcp_monitoring"]["status"], "UP")
        self.assertEqual(result["monitoring"]["status"], "DOWN")
        self.assertEqual(row["status"], "ACTIVE")
        self.assertEqual(row["recovery_success"], 0)


if __name__ == "__main__":
    unittest.main()
