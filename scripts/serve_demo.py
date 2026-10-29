"""Serve only the public demo directory, bound to localhost."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    web = Path(__file__).resolve().parents[1] / "web"
    handler = partial(SimpleHTTPRequestHandler, directory=str(web))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"WISE 0855 demo: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
