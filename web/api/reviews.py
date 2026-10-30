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
import time
from urllib.parse import urlsplit

try:
    from api._telemetry import emit_request, request_logger
except ModuleNotFoundError as exc:
    if exc.name not in ('api', 'api._telemetry'):
        raise
    from web.api._telemetry import emit_request, request_logger

COOKIE = "__Host-spherex-review"
TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
HEX_ID = re.compile(r"^[a-f0-9]{64}$")
KEY_PART = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
STATUSES = {"uncertain", "interesting", "artifact"}
MAX_BODY = 8192
LIMIT = 90
POST_GLOBAL_LIMIT = 60
OWNER_REVIEW_LIMIT = 100
GLOBAL_REVIEW_LIMIT = 20000
DB_TIMEOUT_SECONDS = 10
MAX_TRANSACTION_ATTEMPTS = 4
MAX_COMMIT_ATTEMPTS = 3
CONTRACT_VERSION = "1.1"
logger = request_logger("review_api")


class ReviewQuota(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class CommitOutcomeUnknown(Exception):
    pass


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
    note.encode("utf-8")  # Reject lone JSON surrogates before any storage access.
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


def save_review(db, owner, key, item, now):
    """Serialize every POST before counting; retries have no external side effects."""
    from pymongo.errors import DuplicateKeyError, PyMongoError
    from pymongo.read_concern import ReadConcern
    from pymongo.write_concern import WriteConcern

    # Create the common guard outside the transaction for existing deployments.
    # Two cold instances may race to insert it; an existing _id is sufficient.
    try:
        db.review_guard.update_one({"_id": "global"}, {"$setOnInsert": {"version": 0}}, upsert=True)
    except DuplicateKeyError:
        pass
    query = {"owner": owner, "key": key}
    expires = now + timedelta(days=180)
    saved = {**item, "saved_at": now.isoformat(), "expires_at": expires}
    with db.client.start_session() as session:
        for attempt in range(MAX_TRANSACTION_ATTEMPTS):
            session.start_transaction(read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"))
            try:
                guard = db.review_guard.update_one({"_id": "global"}, {"$inc": {"version": 1}}, session=session)
                if guard.matched_count != 1:
                    raise RuntimeError("review_guard_missing")
                existing = db.reviews.find_one(query, {"expires_at": 1}, session=session)
                live = existing is not None and existing.get("expires_at") is not None and existing["expires_at"] > now
                if not live and db.reviews.count_documents({"owner": owner, "expires_at": {"$gt": now}},
                                                          limit=OWNER_REVIEW_LIMIT, session=session) >= OWNER_REVIEW_LIMIT:
                    raise ReviewQuota("review_limit")
                if existing is None and db.reviews.count_documents({}, limit=GLOBAL_REVIEW_LIMIT,
                                                                   hint="_id_", session=session) >= GLOBAL_REVIEW_LIMIT:
                    raise ReviewQuota("storage_limit")
                db.reviews.update_one(query, {"$set": saved}, upsert=True, session=session)
            except Exception as exc:
                if session.in_transaction:
                    try:
                        session.abort_transaction()
                    except PyMongoError:
                        pass
                if isinstance(exc, PyMongoError) and exc.has_error_label("TransientTransactionError") and attempt + 1 < MAX_TRANSACTION_ATTEMPTS:
                    continue
                raise
            commit_uncertain = False
            for commit_attempt in range(MAX_COMMIT_ATTEMPTS):
                try:
                    session.commit_transaction()
                    return saved
                except PyMongoError as exc:
                    if exc.has_error_label("UnknownTransactionCommitResult"):
                        commit_uncertain = True
                        if commit_attempt + 1 < MAX_COMMIT_ATTEMPTS:
                            continue
                        raise CommitOutcomeUnknown() from exc
                    if commit_uncertain:
                        raise CommitOutcomeUnknown() from exc
                    if exc.has_error_label("TransientTransactionError") and attempt + 1 < MAX_TRANSACTION_ATTEMPTS:
                        break
                    raise
                except Exception as exc:
                    if commit_uncertain:
                        raise CommitOutcomeUnknown() from exc
                    raise
        raise RuntimeError("transaction_retry_exhausted")


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
        emit_request(logger, {"event": "review_request", "request_id": self.request_id,
                              "method": self.request_method, "status": code,
                              "category": category, "latency_ms": round((time.monotonic() - self.started) * 1000, 2)})

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
            body = item = None
            if method != "GET":
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
                if method == "POST":
                    item = validate_review(body)
                elif isinstance(body, dict) and "review_id" in body:
                    if not isinstance(body["review_id"], str) or not HEX_ID.fullmatch(body["review_id"]):
                        raise ValueError("invalid_review")
                else:
                    legacy_key(body)
            if not os.environ.get("MONGODB_URI"):
                return self.reply(503, {"error": "storage_unavailable"}, "configuration")
            from pymongo import timeout
            with timeout(DB_TIMEOUT_SECONDS):
                return self.process_storage(method, owner, body, item)
        except ReviewQuota as exc:
            return self.reply(409, {"error": exc.code}, exc.code)
        except CommitOutcomeUnknown:
            return self.reply(503, {"error": "save_outcome_unknown"}, "commit_unknown")
        except (ValueError, TypeError, UnicodeError):
            return self.reply(400, {"error": "invalid_review"}, "validation")
        except Exception:
            return self.reply(503, {"error": "storage_unavailable"}, "dependency_or_internal")

    def process_storage(self, method, owner, body, item):
        from pymongo import ReturnDocument
        db = database()
        now = datetime.now(timezone.utc)
        ip = self.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()
        minute = now.strftime("%Y%m%d%H%M")
        bucket = sha256((ip + minute).encode()).hexdigest()
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
        if method == "DELETE":
            if "review_id" in body:
                rid = body["review_id"]
                key = next((row["key"] for row in db.reviews.find({"owner": owner}, {"_id": 0, "key": 1})
                            if secrets.compare_digest(review_id(owner, row["key"]), rid)), None)
            else:
                key = legacy_key(body)
            if key is not None:
                db.reviews.delete_one({"owner": owner, "key": key})
            return self.reply(200, {"deleted": True})
        global_counter = db.limits.find_one_and_update({"_id": "review-post-global:" + minute},
            {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now + timedelta(minutes=2)}},
            upsert=True, return_document=ReturnDocument.AFTER)
        if global_counter["count"] > POST_GLOBAL_LIMIT:
            return self.reply(429, {"error": "rate_limited"}, "global_rate_limit")
        key = ":".join([item["analysis_sha256"], item["scene_id"], item["selection"]])
        saved = save_review(db, owner, key, item, now)
        saved["expires_at"] = saved["expires_at"].isoformat()
        return self.reply(200, {"saved": True, "storage": "mongodb", "contract_version": CONTRACT_VERSION,
                                "session_scope": session_scope(owner),
                                "review": {**saved, "review_id": review_id(owner, key)}})

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
