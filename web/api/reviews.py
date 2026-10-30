"""Private guest reviews for the public science demo. Secrets stay server-side."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from hashlib import sha256
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
import json
import logging
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import urlsplit

COOKIE = "__Host-spherex-review"
TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
HEX_ID = re.compile(r"^[a-f0-9]{64}$")
KEY_PART = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
STATUSES = {"uncertain", "interesting", "artifact"}
MAX_BODY = 8192
LIMIT = 90
CONTRACT_VERSION = "1.1"
logger = logging.getLogger("review_api")


@lru_cache(maxsize=1)
def manifest():
    return json.loads((Path(__file__).resolve().parents[1] / "data/manifest.json").read_text())


def validate_review(body):
    if not isinstance(body, dict):
        raise ValueError("invalid_review")
    scenes = {s["id"]: s for s in manifest()["scenes"]}
    scene_id, selection, status = body.get("scene_id"), body.get("selection"), body.get("status")
    if not isinstance(scene_id, str) or not isinstance(selection, str) or not isinstance(status, str):
        raise ValueError("invalid_review")
    scene = scenes.get(scene_id)
    if not scene or selection not in {"target", *(c["id"] for c in scene["candidates"])}:
        raise ValueError("unknown_selection")
    if body.get("analysis_sha256") != manifest()["analysis_sha256"]:
        raise ValueError("stale_analysis")
    note = body.get("note", "")
    if status not in STATUSES or not isinstance(note, str) or len(note) > 2000:
        raise ValueError("invalid_review")
    return {"scene_id": scene["id"], "selection": selection, "status": status,
            "note": note, "analysis_sha256": body["analysis_sha256"],
            "input_sha256": [scene["before"]["sha256"], scene["after"]["sha256"]],
            "target_detection": scene["target_detection"]}


def review_id(owner, key):
    return sha256((owner + "\0" + key).encode()).hexdigest()


def session_scope(owner):
    """Non-secret scope label; never usable in place of the session cookie."""
    return sha256(("scope\0" + owner).encode()).hexdigest()


def legacy_key(body):
    if not isinstance(body, dict):
        raise ValueError("invalid_review")
    digest, scene, selection = (body.get(k) for k in ("analysis_sha256", "scene_id", "selection"))
    if not isinstance(digest, str) or not HEX_ID.fullmatch(digest):
        raise ValueError("invalid_review")
    if not all(isinstance(part, str) and KEY_PART.fullmatch(part) for part in (scene, selection)):
        raise ValueError("invalid_review")
    return ":".join((digest, scene, selection))


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
    return origin.scheme == "https" and origin.netloc == headers.get("Host") and not (origin.path or origin.query or origin.fragment)


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body, category="ok"):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Request-ID", self.request_id)
        commit = os.environ.get("VERCEL_GIT_COMMIT_SHA", "")
        if re.fullmatch(r"[0-9a-f]{40}", commit): self.send_header("X-App-Commit", commit)
        if hasattr(self, "rate_remaining"):
            self.send_header("RateLimit-Limit", str(LIMIT))
            self.send_header("RateLimit-Remaining", str(self.rate_remaining))
            self.send_header("RateLimit-Reset", str(self.rate_reset))
        if code == 429:
            self.send_header("Retry-After", str(self.rate_reset))
        if code == 405:
            self.send_header("Allow", "GET, POST, DELETE")
        if getattr(self, "new_token", None):
            self.send_header("Set-Cookie", f"{COOKIE}={self.new_token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=15552000")
        self.end_headers()
        if self.request_method != "OTHER" or self.command != "HEAD":
            self.wfile.write(data)
        logger.warning(json.dumps({"event": "review_request", "request_id": self.request_id,
                                   "method": self.request_method, "status": code,
                                   "category": category, "latency_ms": round((time.monotonic() - self.started) * 1000, 2)}))

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
        if create:
            self.new_token = token  # Renew active guest sessions for 180 days.
        return sha256(token.encode()).hexdigest()

    def dispatch(self, method):
        self.request_id = secrets.token_hex(16)
        self.started = time.monotonic()
        self.request_method = method if method in {"GET", "POST", "DELETE"} else "OTHER"
        if method not in {"GET", "POST", "DELETE"}:
            return self.reply(405, {"error": "method_not_allowed"}, "method")
        try:
            if method != "GET" and not same_origin(self.headers):
                return self.reply(403, {"error": "origin_required"}, "origin")
            owner = self.session(create=method == "GET")
            if not owner:
                return self.reply(401, {"error": "session_required"}, "session")
            if not os.environ.get("MONGODB_URI"):
                return self.reply(503, {"error": "storage_unavailable"}, "configuration")
            from pymongo import ReturnDocument
            db = database()
            now = datetime.now(timezone.utc)
            ip = self.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()
            bucket = sha256((ip + now.strftime("%Y%m%d%H%M")).encode()).hexdigest()
            counter = db.limits.find_one_and_update({"_id": bucket},
                {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now + timedelta(minutes=2)}},
                upsert=True, return_document=ReturnDocument.AFTER)
            self.rate_remaining = max(0, LIMIT - counter["count"])
            self.rate_reset = 60 - now.second
            if counter["count"] > LIMIT:
                return self.reply(429, {"error": "rate_limited"}, "rate_limit")
            if method == "GET":
                rows = list(db.reviews.find({"owner": owner, "expires_at": {"$gt": now}}, {"_id": 0, "owner": 0}).limit(100))
                for row in rows:
                    row["review_id"] = review_id(owner, row["key"])
                    row["expires_at"] = row["expires_at"].isoformat()
                return self.reply(200, {"storage": "mongodb", "contract_version": CONTRACT_VERSION,
                                        "session_scope": session_scope(owner), "reviews": rows})
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                return self.reply(411, {"error": "length_required"}, "validation")
            if not re.fullmatch(r"[0-9]+", raw_length):
                return self.reply(400, {"error": "invalid_review"}, "validation")
            length = int(raw_length)
            if not 0 < length <= MAX_BODY:
                return self.reply(413, {"error": "body_too_large"}, "validation")
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                return self.reply(415, {"error": "json_required"}, "validation")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("short_body")
            body = json.loads(raw)
            if method == "DELETE":
                if isinstance(body, dict) and "review_id" in body:
                    rid = body["review_id"]
                    if not isinstance(rid, str) or not HEX_ID.fullmatch(rid):
                        raise ValueError("invalid_review")
                    # Derive IDs for legacy rows without requiring a database migration.
                    key = next((row["key"] for row in db.reviews.find({"owner": owner}, {"_id": 0, "key": 1})
                                if secrets.compare_digest(review_id(owner, row["key"]), rid)), None)
                else:
                    key = legacy_key(body)
                if key is not None:
                    db.reviews.delete_one({"owner": owner, "key": key})
                return self.reply(200, {"deleted": True})
            item = validate_review(body)
            key = ":".join([item["analysis_sha256"], item["scene_id"], item["selection"]])
            query = {"owner": owner, "key": key}
            live = {"owner": owner, "expires_at": {"$gt": now}}
            if not db.reviews.find_one({**query, "expires_at": {"$gt": now}}, {"_id": 1}) and db.reviews.count_documents(live, limit=100) >= 100:
                return self.reply(409, {"error": "review_limit"}, "review_limit")
            expires = now + timedelta(days=180)
            item["saved_at"] = now.isoformat()
            db.reviews.update_one(query, {"$set": {**item, "expires_at": expires}}, upsert=True)
            return self.reply(200, {"saved": True, "storage": "mongodb", "contract_version": CONTRACT_VERSION,
                                    "session_scope": session_scope(owner),
                                    "review": {**item, "review_id": review_id(owner, key), "expires_at": expires.isoformat()}})
        except (ValueError, TypeError, UnicodeError):
            return self.reply(400, {"error": "invalid_review"}, "validation")
        except Exception:
            return self.reply(503, {"error": "storage_unavailable"}, "dependency_or_internal")

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_PATCH(self):
        self.dispatch("PATCH")

    def do_OPTIONS(self):
        self.dispatch("OPTIONS")

    def do_HEAD(self):
        self.dispatch("HEAD")

    def do_TRACE(self):
        self.dispatch("TRACE")

    def do_CONNECT(self):
        self.dispatch("CONNECT")
