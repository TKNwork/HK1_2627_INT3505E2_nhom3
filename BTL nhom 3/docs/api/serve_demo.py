"""Serve Swagger UI and forward /api/v1 requests to local Prism."""

from functools import partial
from http.client import HTTPConnection
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class DemoHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/v1/"):
            self.forward_to_prism()
        else:
            super().do_GET()

    def forward_to_prism(self):
        if not self.path.startswith("/api/v1/"):
            self.send_error(404)
            return

        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        headers = {
            name: self.headers[name]
            for name in ("Accept", "Authorization", "Content-Type", "Idempotency-Key", "Prefer")
            if name in self.headers
        }
        upstream = HTTPConnection("127.0.0.1", 4010, timeout=10)
        try:
            upstream.request(self.command, self.path.removeprefix("/api/v1"), body, headers)
            response = upstream.getresponse()
            payload = response.read()
        except OSError:
            self.send_error(502, "Start Prism on 127.0.0.1:4010")
            return
        finally:
            upstream.close()

        self.send_response(response.status)
        for name in ("Content-Type", "Location", "Preference-Applied", "WWW-Authenticate"):
            value = response.getheader(name)
            if value is not None:
                self.send_header(name, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_POST = forward_to_prism
    do_PATCH = forward_to_prism
    do_DELETE = forward_to_prism


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parents[2]
    handler = partial(DemoHandler, directory=project_dir)
    with ThreadingHTTPServer(("127.0.0.1", 8012), handler) as server:
        print("Swagger UI: http://127.0.0.1:8012/docs/api/", flush=True)
        server.serve_forever()
