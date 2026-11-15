"""Fixed-enum upstream diagnostics; never serialize exception messages."""
from http.client import HTTPException, IncompleteRead
import json
import re
import socket
import ssl
from urllib.error import HTTPError, URLError


_ENDPOINTS = frozenset(('observations', 'frame'))
_STAGES = frozenset(('open', 'headers', 'read', 'parse'))
_CLASSES = frozenset(('contract_error', 'http_error', 'url_error', 'dns_error',
    'tls_certificate_error', 'tls_error', 'timeout', 'connection_reset',
    'connection_refused', 'connection_aborted', 'broken_pipe', 'connection_error',
    'incomplete_read', 'http_exception', 'os_error', 'other', 'none', 'cycle', 'depth_limit'))


def _kind(exc):
    # Subclasses are deliberately mapped to fixed labels, never their names.
    if exc is None:return 'none'
    if isinstance(exc, HTTPError):return 'http_error'
    if isinstance(exc, URLError):return 'url_error'
    if isinstance(exc, ssl.SSLCertVerificationError):return 'tls_certificate_error'
    if isinstance(exc, ssl.SSLError):return 'tls_error'
    if isinstance(exc, socket.gaierror):return 'dns_error'
    if isinstance(exc, TimeoutError):return 'timeout'
    if isinstance(exc, ConnectionResetError):return 'connection_reset'
    if isinstance(exc, ConnectionRefusedError):return 'connection_refused'
    if isinstance(exc, ConnectionAbortedError):return 'connection_aborted'
    if isinstance(exc, BrokenPipeError):return 'broken_pipe'
    if isinstance(exc, ConnectionError):return 'connection_error'
    if isinstance(exc, IncompleteRead):return 'incomplete_read'
    if isinstance(exc, HTTPException):return 'http_exception'
    if isinstance(exc, OSError):return 'os_error'
    return 'other'


def describe(exc, stage):
    """Return safe enums only, following at most four URLError reason links."""
    try:
        if stage not in _STAGES:return None
        result = {'stage': stage, 'exception_class': 'contract_error' if exc is None else _kind(exc)}
        if isinstance(exc, HTTPError) and type(exc.code) is int and 100 <= exc.code <= 599:
            result['upstream_http_status'] = exc.code
        if isinstance(exc, URLError) and not isinstance(exc, HTTPError):
            seen = {id(exc)};current = exc
            for _ in range(4):
                reason = current.reason
                if id(reason) in seen:
                    result['reason_class'] = 'cycle';break
                seen.add(id(reason))
                if not isinstance(reason, URLError) or isinstance(reason, HTTPError):
                    result['reason_class'] = _kind(reason)
                    if isinstance(reason, HTTPError) and type(reason.code) is int and 100 <= reason.code <= 599:
                        result['upstream_http_status'] = reason.code
                    break
                current = reason
            else:
                result['reason_class'] = 'depth_limit'
        return result
    except Exception:
        # Instrumentation must never replace the original API error.
        return None


def emit(logger, endpoint, request_id, diagnostic):
    """Emit one explicitly checked event; logger failure cannot affect response."""
    try:
        if (endpoint not in _ENDPOINTS or not isinstance(request_id, str)
                or not re.fullmatch(r'[a-f0-9]{32}', request_id) or not isinstance(diagnostic, dict)):
            return
        stage = diagnostic.get('stage');kind = diagnostic.get('exception_class')
        if stage not in _STAGES or kind not in _CLASSES:return
        event = {'schema': 'upstream-diagnostic-1', 'event': 'upstream_diagnostic',
                 'endpoint': endpoint, 'request_id': request_id, 'stage': stage,
                 'exception_class': kind}
        reason = diagnostic.get('reason_class')
        if reason in _CLASSES:event['reason_class'] = reason
        status = diagnostic.get('upstream_http_status')
        if type(status) is int and 100 <= status <= 599:event['upstream_http_status'] = status
        logger.error(json.dumps(event, allow_nan=False, separators=(',', ':')))
    except Exception:
        return
