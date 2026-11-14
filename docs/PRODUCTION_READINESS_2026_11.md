# Production-readiness fixes · November 2026

## Scope approved by the owner

Keep the existing visual direction and mobile two-tap navigation. Fix interaction,
reliability and reviewer/viewer issues. Operational decisions: target one class of
about 30 concurrent users; status page only, no notifications; faster public data
reads; block release on unavailable/corrupt data; require desktop/mobile and API
checks; prepare a manual encrypted local backup and an isolated restore drill.

## Delivered behavior

- Earth hit testing, mobile navigation, dialog contrast and visible keyboard focus.
- Retry controls for failed sky metadata and workspace script loading.
- Reloadable comparison links retain observation IDs, detector selections and view;
  A/B panes load independently and preserve the successful pane after a failure.
- English/Vietnamese core workflow, including scientific warnings and downloads.
- Active A/B provenance in Inspect. Full-field preview hashes explicitly cover
  downloaded byte ranges, not complete FITS files. Science image bytes unchanged.
- Guided image-reading tour points to verified orange, bright and dark pixels.
  Each answer immediately receives a verdict and explanation. Display brightness
  alone is not a source identification, distance or motion measurement.
- Bounded public-byte cache and duplicate-work sharing within each API process;
  atomic per-IP/global admission prevents rejected clients spending global quota.
- `/status.html` shows one live public-asset probe and sparse recent API success/error
  timestamps. It is not continuous uptime monitoring, and sends no notifications.
- Production build verifies every pinned public asset and its stored/source hashes
  directly from MongoDB. A failed build cannot replace the running release.

## Release procedure

1. Run Python, all Node tests and browser smoke checks. CI uses the same Python
   major/minor as `web/.python-version`; browser dependencies are development-only.
2. Keep Vercel automatic production-domain assignment disabled. Build a production
   candidate with production environment variables and the read-only data gate.
3. Verify the exact candidate commit, guided activity, scientific image sources,
   status API and key desktop/mobile flows before promotion.
4. Promote that verified production build, then verify the canonical domain.
   Promotion may re-enable automatic assignment: disable it again to keep the gate
   for subsequent releases. Never promote a preview with different environment data.

## Measured scope and remaining limits

The 30-user tests use deterministic upstream fixtures: identical requests within
one process share one fetch/render and one quota admission. This is not a measured
production capacity or latency guarantee. Different processes still depend on CDN
caching and shared Mongo quotas. Existing limits on distinct uncached queries remain.
IRSA can fail independently; successful pixels, masks and provenance must remain
usable when another frame fails.

The public status probe covers one metadata file. Recent activity is sampled at
most once per endpoint/minute for success and every 15 seconds for server errors
in each process, with a bounded write budget. Missing activity means unknown,
not healthy. Request logs remain the detailed diagnostic record; filter their JSON
`level`, not just the platform's outer log severity.

Backup preparation and synthetic restore tests do not establish that production
reviews have been backed up. The existing sensitive Mongo credential cannot be
read back from Vercel and is not present locally. A live snapshot needs the operator
to supply that credential through a protected local input. No credential should be
placed in Git, a command argument, a CI artifact or a chat message. Local backups
and Windows-protected keys do not survive loss of the entire machine.

Scientific interpretation remains qualified: visual differences, mask changes and
bright pixels are not confirmed astronomical detections or motion measurements.

## Verification commands

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
Get-ChildItem tests -Filter *.test.cjs | ForEach-Object { node $_.FullName }
.venv/Scripts/python.exe scripts/browser_smoke.py
.venv/Scripts/python.exe scripts/serve_app.py
```

Local preview: <http://127.0.0.1:8767/>. Browser smoke uses a separate loopback
server and blocks live IRSA/review requests. Physical-device Safari/Firefox and
long-running production load are separate acceptance milestones.
