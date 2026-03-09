"""Local HTTP server to catch the OAuth callback."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class _CallbackServer(HTTPServer):
    """HTTPServer subclass that stores the OAuth callback result."""

    auth_code: str | None = None
    auth_error: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    """Handles a single OAuth callback request, then signals the server to stop."""

    server: _CallbackServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        code = params.get("code", [None])[0]
        error = params.get("error", [None])[0]

        if code:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Authentication successful!</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )
            self.server.auth_code = code
        elif error:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            error_desc = params.get("error_description", [error])[0]
            self.wfile.write(
                f"<html><body><h2>Authentication failed</h2>"
                f"<p>{error_desc}</p></body></html>".encode()
            )
            self.server.auth_error = error_desc
        else:
            self.send_response(400)
            self.end_headers()

        # Signal the server to shut down after handling
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default logging."""


def wait_for_callback(port: int = 1455, timeout: float = 120) -> str:
    """Start a local server and wait for the OAuth callback.

    Returns the authorization code.
    Raises RuntimeError on error or timeout.
    """
    server = _CallbackServer(("127.0.0.1", port), _CallbackHandler)
    server.timeout = timeout

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    server_thread.join(timeout=timeout)

    server.shutdown()

    if server.auth_error:
        raise RuntimeError(f"OAuth error: {server.auth_error}")
    if server.auth_code is None:
        raise RuntimeError("Timed out waiting for OAuth callback")

    return server.auth_code
