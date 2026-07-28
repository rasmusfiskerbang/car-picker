"""PROTOTYPE ONLY: serve the private comparison UI from the repository root."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOST = "127.0.0.1"
PORT = 4173


class PrototypeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=ROOT, **kwargs)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), PrototypeHandler)
    print(
        f"Private comparison prototype: http://{HOST}:{PORT}/prototype/private-comparison/?variant=A"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPrototype stopped.")
