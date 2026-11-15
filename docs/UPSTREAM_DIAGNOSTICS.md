# Upstream failure diagnostics

The observations and frame APIs emit a separate structured diagnostic event
for handled upstream or response-parsing failures. The existing response status,
error code, request validation, allowed IRSA endpoint and path, redirect policy,
body limits and timeouts are unchanged. This change does not retry or cache a
request and does not itself resolve a production failure.

`upstream-diagnostic-1` contains only these fields:

| Field | Meaning |
| --- | --- |
| `schema`, `event` | Fixed values `upstream-diagnostic-1`, `upstream_diagnostic`. |
| `endpoint` | `observations` or `frame`. |
| `request_id` | The same 32-character hexadecimal ID as the request event. |
| `stage` | `open`, `headers`, `read`, or `parse`. |
| `exception_class` | Fixed class enum, never an arbitrary exception name or message. |
| `reason_class` | Optional fixed enum for a nested `URLError.reason`. |
| `upstream_http_status` | Numeric status, when available from an HTTP error. |

`open` includes the HTTP opener's connection and header acquisition; `headers`
denotes the frame API's subsequent content-length inspection, not necessarily
the moment headers arrived over the network. `read` covers body streaming and
its existing limits. `parse` covers VOTable/FITS processing. Contract-generated
failures use `contract_error`; distinguish their specific public error codes
using the matching request event. The observations request event now includes
its existing upstream error code; the frame request event already did so.

Class enums distinguish URL wrappers, DNS, certificate verification, other TLS,
direct timeout, connection reset/refused/aborted, broken pipe, other connection
errors, incomplete HTTP reads, other HTTP exceptions, generic OS errors, HTTP
status errors and unknown values. Nested URL reasons are inspected to a bounded
depth with cycle detection. An unknown or wrapped timeout may still map to the
existing `upstream_unavailable` response: the event helps classify what was
observed but does not guarantee a root cause. Logging failures are suppressed
within the diagnostic helper so they do not replace the network failure.

Only the fields above are emitted: never exception messages, URLs, query strings,
headers, cookies, bodies, IP addresses, environment values or arbitrary class
names. Provider log severity can differ from the JSON application severity;
look up the shared request ID across log levels. The existing socket timeout and
elapsed checks are not a guarantee of a hard DNS deadline.

## Historical provenance

The mask audit records a historical `web/api/frame.py` blob from a fixed Git
commit; it is not a hash of the current API implementation. The earlier
reference-presence local-test receipt records its source inventory as it existed
at that time. Neither artifact is changed or rerun by this telemetry update.
A fresh verification inventory should identify these changed API bytes when the
new version is reviewed; historical results must retain their original hashes.

## Offline verification

```powershell
.venv/Scripts/python.exe -m unittest tests.test_upstream_diagnostics tests.test_observations_api tests.test_frame_api tests.test_telemetry tests.test_api_limits -q
```

The tests use simulated failures and in-memory HTTP handlers. They make no live
upstream request and do not establish the cause of earlier production errors.
