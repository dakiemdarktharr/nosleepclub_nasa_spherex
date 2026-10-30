"""Local static site and public observation APIs, bound only to loopback.

This uses the same request handlers as Vercel. Guest MongoDB reviews remain
production-only; local review notes use the browser. No server secrets loaded.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
# Support both documented CLI forms. API helpers remain normal package imports;
# only the direct-script launcher needs its project root on the import path.
if not __package__:
    sys.path.insert(0, str(ROOT))


def api_class(name):
    path = ROOT / "web/api" / (name + ".py")
    spec = importlib.util.spec_from_file_location("local_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.handler


class AppHandler(SimpleHTTPRequestHandler):
    apis = {}

    def do_GET(self):
        name = urlsplit(self.path).path
        if name in self.apis:
            # The API uses its own methods/class with this request's existing
            # streams and state. It does not reparse or reopen the connection.
            cls = self.apis[name]
            delegate = object.__new__(cls)
            delegate.__dict__ = self.__dict__
            cls.do_GET(delegate)
        else:
            super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--check", action="store_true", help="Load the actual API handlers without opening a socket")
    args = parser.parse_args()
    os.environ['SPHEREX_LOCAL_API'] = '1'
    AppHandler.apis = {"/api/observations": api_class("observations"), "/api/frame": api_class("frame")}
    if args.check:
        print("API imports OK: observations, frame", flush=True)
        return
    handler = partial(AppHandler, directory=str(ROOT / "web"))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Sky explorer: http://127.0.0.1:{server.server_port}/#explore", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
