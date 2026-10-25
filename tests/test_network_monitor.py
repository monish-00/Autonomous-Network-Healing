import socket
import unittest
from unittest.mock import Mock, patch

from app.monitoring.network_monitor import check_host, check_http_health


class NetworkMonitorTests(unittest.TestCase):
    @patch("app.monitoring.network_monitor.requests.get")
    def test_healthy_http_response_is_accepted(self, get):
        response = Mock(status_code=200)
        response.json.return_value = {"status": "healthy"}
        get.return_value = response
        result = check_http_health("127.0.0.1", 8080)
        self.assertEqual(result["status"], "UP")
        self.assertIsNone(result["fault_type"])
        self.assertIsNone(result["error"])

    @patch("app.monitoring.network_monitor.socket.create_connection")
    def test_tcp_connection_refused_is_reported(self, create_connection):
        create_connection.side_effect = ConnectionRefusedError("Connection refused")
        result = check_host("127.0.0.1", 8080, timeout=0.1)
        self.assertEqual(result["status"], "DOWN")
        self.assertEqual(result["fault_type"], "CONNECTION_REFUSED")
        self.assertGreaterEqual(result["response_time_ms"], 0)

    @patch("app.monitoring.network_monitor.socket.create_connection")
    def test_tcp_timeout_is_reported(self, create_connection):
        create_connection.side_effect = socket.timeout("timed out")
        result = check_host("127.0.0.1", 8080, timeout=0.1)
        self.assertEqual(result["status"], "DOWN")
        self.assertEqual(result["fault_type"], "TIMEOUT")

    @patch("app.monitoring.network_monitor.requests.get")
    def test_http_unhealthy_json_and_http_error_are_classified(self, get):
        response = Mock(status_code=200)
        response.json.return_value = {"status": "degraded"}
        get.return_value = response
        unhealthy = check_http_health("127.0.0.1", 8080)
        self.assertEqual(unhealthy["status"], "DOWN")
        self.assertEqual(unhealthy["fault_type"], "UNHEALTHY_RESPONSE")

        response.status_code = 503
        failed_status = check_http_health("127.0.0.1", 8080)
        self.assertEqual(failed_status["fault_type"], "HTTP_ERROR")

    @patch("app.monitoring.network_monitor.requests.get")
    def test_http_invalid_json_and_connection_failure_are_classified(self, get):
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("invalid JSON")
        get.return_value = response
        invalid = check_http_health("127.0.0.1", 8080)
        self.assertEqual(invalid["fault_type"], "INVALID_HEALTH_RESPONSE")

        get.side_effect = __import__("requests").exceptions.ConnectTimeout("timed out")
        unavailable = check_http_health("127.0.0.1", 8080)
        self.assertEqual(unavailable["status"], "DOWN")
        self.assertEqual(unavailable["fault_type"], "TIMEOUT")


if __name__ == "__main__":
    unittest.main()
