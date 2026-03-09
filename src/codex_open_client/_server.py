"""Local HTTP server to catch the OAuth callback."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class _CallbackServer(HTTPServer):
    """HTTPServer subclass that stores the OAuth callback result."""

    allow_reuse_address = True

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.auth_code: str | None = None
        self.auth_error: str | None = None
        self.got_callback = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    """Handles a single OAuth callback request, then signals the server to stop."""

    server: _CallbackServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        code = params.get("code", [None])[0]
        error = params.get("error", [None])[0]

        if code:
            body = (
                b"<html><body><h2>Authentication successful!</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )
            self._send(200, body)
            self.server.auth_code = code
            self.server.got_callback.set()
        elif error:
            error_desc = params.get("error_description", [error])[0]
            body = (
                f"<html><body><h2>Authentication failed</h2>"
                f"<p>{error_desc}</p></body></html>"
            ).encode()
            self._send(400, body)
            self.server.auth_error = error_desc
            self.server.got_callback.set()
        else:
            # Ignore unrelated requests (favicon, etc.)
            self._send(404, b"")
            return

        # Signal the server to shut down after handling
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default logging."""


def wait_for_callback(port: int = 1455, timeout: float = 120) -> str:
    """Start a local server and wait for the OAuth callback.

    Returns the authorization code.
    Raises RuntimeError on error or timeout.
    """
    server = _CallbackServer(("127.0.0.1", port), _CallbackHandler)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # Wait for the callback to arrive (not for the thread to exit)
        got_it = server.got_callback.wait(timeout=timeout)

        if not got_it:
            raise RuntimeError("Timed out waiting for OAuth callback")
        if server.auth_error:
            raise RuntimeError(f"OAuth error: {server.auth_error}")
        if server.auth_code is None:
            raise RuntimeError("Callback received but no authorization code found")

        return server.auth_code
    finally:
        server.shutdown()
        server.server_close()
