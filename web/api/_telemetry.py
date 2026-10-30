"""Bounded request diagnostics without request bodies, URLs, cookies or IPs."""
import json
import logging
import math
import re
import sys


class _BelowWarning(logging.Filter):
    def filter(self, record):
        return record.levelno < logging.WARNING


def request_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        success = logging.StreamHandler(sys.stdout)
        success.addFilter(_BelowWarning())
        failures = logging.StreamHandler(sys.stderr)
        failures.setLevel(logging.WARNING)
        logger.addHandler(success)
        logger.addHandler(failures)
    logger.propagate = False
    return logger


def emit_request(logger, event):
    # Only allow explicitly declared metadata. Logging must not copy HTTP input.
    if not isinstance(event, dict):
        return
    name = event.get('event')
    if not isinstance(name, str) or name not in {'review_request', 'observations_request', 'frame_request'}:
        return
    status, latency = event.get('status'), event.get('latency_ms')
    if (type(status) is not int or not 100 <= status <= 599
            or type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0):
        return
    request_id, category = event.get('request_id'), event.get('category')
    if (not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9]{32}', request_id)
            or not isinstance(category, str) or not re.fullmatch(r'[a-z_]{1,48}', category)):
        return
    level = logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO
    result = {key: event[key] for key in ['event', 'request_id', 'status', 'category', 'latency_ms']}
    result['level'] = logging.getLevelName(level).lower()
    method = event.get('method')
    if isinstance(method, str) and method in {'GET', 'POST', 'DELETE', 'HEAD', 'PUT', 'PATCH', 'OPTIONS', 'OTHER'}:
        result['method'] = method
    code = event.get('error_code')
    if isinstance(code, str) and re.fullmatch(r'[a-z0-9_]{1,80}', code):
        result['error_code'] = code
    upstream = event.get('upstream_http_status')
    if type(upstream) is int and 100 <= upstream <= 599:
        result['upstream_http_status'] = upstream
    logger.log(level, json.dumps(result, allow_nan=False))
