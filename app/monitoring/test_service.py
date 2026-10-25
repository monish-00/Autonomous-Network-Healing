from http.server import BaseHTTPRequestHandler, HTTPServer
import os


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[SERVICE] {args[0]}")


if __name__ == "__main__":
    host = os.environ.get("TEST_SERVICE_HOST", "127.0.0.1")
    port = int(os.environ.get("TEST_SERVICE_PORT", "8080"))

    server = HTTPServer((host, port), HealthHandler)

    print(f"Test service running at http://{host}:{port}")
    print("Health endpoint: /health")
    print("Press CTRL+C to stop the service.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nTest service stopped.")
    finally:
        server.server_close()
