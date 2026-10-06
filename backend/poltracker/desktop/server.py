"""Run the local server on a background thread of the app's own process (so quitting the app can never leave it behind)."""

import logging
import socket
import threading
import time
import urllib.error
import urllib.request

import uvicorn

log = logging.getLogger(__name__)
HOST = "127.0.0.1"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


class LocalServer:
    def __init__(self, app, port: int | None = None):
        self.port = port or find_free_port()
        config = uvicorn.Config(
            app, host=HOST, port=self.port, log_config=None, access_log=False, log_level="warning", lifespan="on"
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, name="poltracker-server", daemon=True)

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.port}"

    def start(self) -> None:
        self._thread.start()

    def wait_ready(self, timeout: float = 30.0) -> float:
        """Poll /health until it answers; returns the seconds it took. Raises if the server does not come up."""
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            if not self._thread.is_alive():
                raise RuntimeError("The local server stopped while starting. See the log for details.")
            try:
                with urllib.request.urlopen(f"{self.url}/health", timeout=1) as response:
                    if response.status == 200:
                        return time.monotonic() - started
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(0.05)
        raise TimeoutError(f"The local server did not answer /health within {timeout:.0f} seconds.")

    def stop(self, timeout: float = 10.0) -> None:
        self._server.should_exit = True  # runs the app's shutdown, which stops the refresh service
        self._thread.join(timeout)
        if self._thread.is_alive():
            log.warning("server thread did not stop within %.0fs", timeout)
