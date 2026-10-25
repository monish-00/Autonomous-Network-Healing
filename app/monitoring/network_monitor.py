import socket
import time
from datetime import datetime, timezone

import requests


def classify_fault(error=None, http_status_code=None, response_body=None):
    """Return a transparent rule-based label for a failed health check."""
    if http_status_code is not None:
        if http_status_code != 200:
            return "HTTP_ERROR"
        if not isinstance(response_body, dict):
            return "INVALID_HEALTH_RESPONSE"
        if response_body.get("status") != "healthy":
            return "UNHEALTHY_RESPONSE"
        return None

    message = str(error or "").lower()
    if "timed out" in message or "timeout" in message:
        return "TIMEOUT"
    if "refused" in message:
        return "CONNECTION_REFUSED"
    if error:
        return "CONNECTION_ERROR"
    return None


def check_host(host: str, port: int, timeout: float = 3.0) -> dict:
    """Check whether a TCP service is reachable."""

    start_time = time.perf_counter()
    checked_at = datetime.now(timezone.utc).isoformat()

    try:
        with socket.create_connection((host, port), timeout=timeout):
            response_time_ms = (time.perf_counter() - start_time) * 1000

            return {
                "host": host,
                "port": port,
                "status": "UP",
                "response_time_ms": round(response_time_ms, 2),
                "checked_at": checked_at,
                "error": None,
                "fault_type": None,
            }

    except (OSError, TimeoutError) as exc:
        response_time_ms = (time.perf_counter() - start_time) * 1000

        return {
            "host": host,
            "port": port,
            "status": "DOWN",
            "response_time_ms": round(response_time_ms, 2),
            "checked_at": checked_at,
            "error": str(exc),
                "fault_type": classify_fault(exc),
        }


def check_http_health(
    host: str,
    port: int,
    path: str = "/health",
    timeout: float = 3.0,
) -> dict:
    """
    Check application health using an HTTP endpoint.

    HTTP 200 with a JSON body containing status='healthy'
    is considered healthy.
    """

    url = f"http://{host}:{port}{path}"
    start_time = time.perf_counter()
    checked_at = datetime.now(timezone.utc).isoformat()

    try:
        response = requests.get(url, timeout=timeout)

        response_time_ms = (time.perf_counter() - start_time) * 1000

        json_valid = True
        try:
            body = response.json()
        except ValueError:
            body = {}
            json_valid = False

        healthy = (
            response.status_code == 200
            and isinstance(body, dict)
            and body.get("status") == "healthy"
        )

        return {
            "host": host,
            "port": port,
            "url": url,
            "status": "UP" if healthy else "DOWN",
            "http_status_code": response.status_code,
            "response_time_ms": round(response_time_ms, 2),
            "checked_at": checked_at,
            "error": None if healthy else "HTTP health check failed",
            "fault_type": None if healthy else (
                "HTTP_ERROR" if response.status_code != 200 else
                "INVALID_HEALTH_RESPONSE" if not json_valid or not isinstance(body, dict) else
                "UNHEALTHY_RESPONSE"
            ),
        }

    except requests.RequestException as exc:
        response_time_ms = (time.perf_counter() - start_time) * 1000

        return {
            "host": host,
            "port": port,
            "url": url,
            "status": "DOWN",
            "http_status_code": None,
            "response_time_ms": round(response_time_ms, 2),
            "checked_at": checked_at,
            "error": str(exc),
            "fault_type": classify_fault(exc),
        }


if __name__ == "__main__":
    targets = [
        ("127.0.0.1", 80),
        ("127.0.0.1", 5000),
        ("127.0.0.1", 8080),
    ]

    print("\n=== TCP MONITORING ===")

    for host, port in targets:
        result = check_host(host, port)

        print(f"\nTarget: {result['host']}:{result['port']}")
        print(f"Status: {result['status']}")
        print(f"Response time: {result['response_time_ms']} ms")

        if result["error"]:
            print(f"Details: {result['error']}")

    print("\n=== HTTP HEALTH MONITORING ===")

    result = check_http_health("127.0.0.1", 8080)

    print(f"\nURL: {result['url']}")
    print(f"Status: {result['status']}")
    print(f"HTTP status code: {result['http_status_code']}")
    print(f"Response time: {result['response_time_ms']} ms")

    if result["error"]:
        print(f"Details: {result['error']}")

    print("\nMonitoring check completed.")
