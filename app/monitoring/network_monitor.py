import socket
import time
from datetime import datetime, timezone


def check_host(host: str, port: int, timeout: float = 3.0) -> dict:
    """
    Check whether a TCP service is reachable.

    Args:
        host: Hostname or IP address.
        port: TCP port of the service.
        timeout: Maximum connection time in seconds.

    Returns:
        A dictionary containing the service status and check details.
    """
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
        }


if __name__ == "__main__":
    targets = [
        ("127.0.0.1", 80),
        ("127.0.0.1", 5000),
        ("127.0.0.1", 8080),
    ]

    print("\n=== NETWORK MONITORING SYSTEM ===")

    for host, port in targets:
        result = check_host(host, port)

        print(f"\nTarget: {result['host']}:{result['port']}")
        print(f"Status: {result['status']}")
        print(f"Response time: {result['response_time_ms']} ms")

        if result["error"]:
            print(f"Details: {result['error']}")

    print("\nMonitoring check completed.")
