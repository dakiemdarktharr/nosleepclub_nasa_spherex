"""Private guest reviews for the public science demo. Secrets stay server-side."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from hashlib import sha256
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit

COOKIE = "__Host-spherex-review"
TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
STATUSES = {"uncertain", "interesting", "artifact"}
MAX_BODY = 8192


@lru_cache(maxsize=1)
def manifest():
    return json.loads((Path(__file__).resolve().parents[1] / "data/manifest.json").read_text())


def validate_review(body):
    if not isinstance(body, dict):
        raise ValueError("invalid_review")
    scenes = {s["id"]: s for s in manifest()["scenes"]}
    scene = scenes.get(body.get("scene_id"))
    if not scene or body.get("selection") not in {"target", *(c["id"] for c in scene["candidates"])}:
        raise ValueError("unknown_selection")
    if body.get("analysis_sha256") != manifest()["analysis_sha256"]:
        raise ValueError("stale_analysis")
    note = body.get("note", "")
    if body.get("status") not in STATUSES or not isinstance(note, str) or len(note) > 2000:
        raise ValueError("invalid_review")
    return {"scene_id": scene["id"], "selection": body["selection"], "status": body["status"],
            "note": note, "analysis_sha256": body["analysis_sha256"],
            "input_sha256": [scene["before"]["sha256"], scene["after"]["sha256"]],
            "target_detection": scene["target_detection"]}


@lru_cache(maxsize=1)
def database():
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=4000,
                     connectTimeoutMS=4000, socketTimeoutMS=5000,
                     maxPoolSize=5, tz_aware=True).get_default_database()
    db.reviews.create_index([("owner", 1), ("key", 1)], unique=True)
    db.reviews.create_index("expires_at", expireAfterSeconds=0)
    db.limits.create_index("expires_at", expireAfterSeconds=0)
    return db


def same_origin(headers):
    origin = urlsplit(headers.get("Origin", ""))
    return origin.scheme == "https" and origin.netloc == headers.get("Host")


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Never log bodies, cookies, or the database URI.

    def reply(self, code, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if getattr(self, "new_token", None):
            self.send_header("Set-Cookie", f"{COOKIE}={self.new_token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=15552000")
        self.end_headers()
        self.wfile.write(data)

    def session(self, create=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        token = cookie[COOKIE].value if COOKIE in cookie else ""
        if not TOKEN.fullmatch(token):
            if not create:
                return None
            token = secrets.token_urlsafe(32)
            self.new_token = token
        return sha256(token.encode()).hexdigest()

    def dispatch(self, method):
        if method != "GET" and not same_origin(self.headers):
            return self.reply(403, {"error": "origin_required"})
        owner = self.session(create=method == "GET")
        if not owner:
            return self.reply(401, {"error": "session_required"})
        if not os.environ.get("MONGODB_URI"):
            return self.reply(503, {"error": "storage_unavailable"})
        try:
            from pymongo import ReturnDocument
            db = database()
            now = datetime.now(timezone.utc)
            # Vercel supplies X-Forwarded-For. Store only a digest with a 2-minute TTL.
            ip = self.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()
            bucket = sha256((ip + now.strftime("%Y%m%d%H%M")).encode()).hexdigest()
            counter = db.limits.find_one_and_update({"_id": bucket},
                {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now + timedelta(minutes=2)}},
                upsert=True, return_document=ReturnDocument.AFTER)
            if counter["count"] > 90:
                return self.reply(429, {"error": "rate_limited"})
            if method == "GET":
                rows = list(db.reviews.find({"owner": owner}, {"_id": 0, "owner": 0, "expires_at": 0}).limit(100))
                return self.reply(200, {"storage": "mongodb", "reviews": rows})
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                return self.reply(413, {"error": "body_too_large"})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.reply(415, {"error": "json_required"})
            item = validate_review(json.loads(self.rfile.read(length)))
            key = ":".join([item["analysis_sha256"], item["scene_id"], item["selection"]])
            query = {"owner": owner, "key": key}
            if method == "DELETE":
                db.reviews.delete_one(query)
                return self.reply(200, {"deleted": True})
            if not db.reviews.find_one(query, {"_id": 1}) and db.reviews.count_documents({"owner": owner}, limit=100) >= 100:
                return self.reply(409, {"error": "review_limit"})
            item["saved_at"] = now.isoformat()
            db.reviews.update_one(query, {"$set": {**item, "expires_at": now + timedelta(days=180)}}, upsert=True)
            return self.reply(200, {"saved": True, "storage": "mongodb", "review": item})
        except (ValueError, TypeError, UnicodeError):
            return self.reply(400, {"error": "invalid_review"})
        except Exception:
            return self.reply(503, {"error": "storage_unavailable"})

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_DELETE(self):
        self.dispatch("DELETE")
