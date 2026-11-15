# Public Data in MongoDB

## Scope and size

Transferred exactly **213 Git blobs** under `web/data/`: 212,215,160 original bytes, 127,478,741 bytes after transport compression. There are 426 parts, up to 512 KiB each. One ignored local diagnostic image is outside the release inventory. Do not import `data/raw/`, raw downloaded FITS, private notes, cookies, or reserved fields. Small FITS/NPZ files already public under `web/data/` retain their original hashes.

Continue using M0 cluster `nosleepclub-spherex`, project `NoSleepClub_NASA_SPHEREx`, database `nosleepclub_nasa_spherex`. Before import, `dbStats` reported 34 bytes of logical data, 126,976 bytes of storage, and 249,856 bytes of indexes. Chunks remain base64 so transfer through the connector/HTTP does not change bytes; about 170 MB logical before overhead remains within the 512 MB limit. There is no evidence that another cluster is needed.

MongoDB applies storage, connection, throughput, and transfer limits to M0; adding a cluster does not automatically increase Vercel bandwidth. Current documentation: [Atlas Free limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/), [cluster capacity](https://www.mongodb.com/docs/atlas/manage-clusters/). Do not create a paid project/cluster or duplicate clusters without measuring a need.

## Read path

`web/api/_data_manifest.json` pins the hash/size/MIME/encoding/chunk for each Git blob. `public_asset_chunks` stores only chunks with `_id = SHA-256(payload)`. The API does not accept collection names or Mongo queries from clients and does not read private reviews.

Unversioned URLs redirect to `v=stored_sha256` and do not cache the redirect. Versioned URLs can be cached by browser/CDN; a stale version that differs from the manifest is rejected instead of returning the wrong bytes. Unversioned metadata and all errors are no-store. JSON/SVG may be gzip-transferred and decompressed by the browser; the original hash remains unchanged. The server verifies each part's length and SHA before returning it.

Vercel limits a function response to 4.5 MB. Direct responses are capped at 4 MiB; three large archives go to a part-download page. The browser verifies each chunk and the complete file before enabling Save. Do not add a download attribute to the link that opens the download page. This is a transport change; it does not rerun or improve science measurements. [Function limits](https://vercel.com/docs/functions/limitations), [CDN caching](https://vercel.com/docs/caching/cache-control-headers).

## Two deployment phases

1. Add the reader/importer and improve UX; keep `/data/` on the CDN. Do not enable `buildCommand`/`outputDirectory` or rewrites before reconciliation.
2. After import, verify hashes through the reader and revoke the capability. Only then run `python build_public.py`, use static output `public/`, and redirect `/data/` by hash to the reader. Static output contains only UI/font/design images; the repository retains datasets for reproduction and rollback. Source checkout/build still downloads the repository, so do not describe this as eliminating all source storage or function bandwidth.

Cutover `7efcf6b` built successfully (static Linux shell: 615,668 bytes), but the wildcard rewrite returned 400 for canonical `/data/manifest.json`. Smoke caught this before creating a QA review; it was rolled back to the preceding static deployment `2f1442a`, and the manifest returned HTTP 200. The exact internal rewrite query set was not determined. The fix uses **213 specific redirects** from the pinned inventory to `/api/data?path=...&v=...`, without passing a wildcard through the rewrite layer. Generator/check and canonical verifier check every mapping. Reader query validation was not relaxed; the first cutover was not counted as successful delivery.

## Import and recovery

`build_data_manifest --write` reads only committed Git blobs, compresses deterministically, and stores downloadable parts in ignored `data/raw/asset-migration/`. Original source/hash is not modified. Atlas connector returned 413 for a batch of about 1.4 MB; this was not counted as imported. Large data therefore used an importer locked by a dedicated random capability. Existing Mongo URI is only in production Vercel; it is not downloaded to local machines/CI/previews.

`migrate_public_data --prepare` creates a local random 32-byte capability and a permit containing only its hash, manifest ID, issue/expiry time (maximum 45 minutes). The operator uses the Atlas connector to place that permit in `public_asset_import_permits`. Import runs only in production, accepts payloads ≤512 KiB with the exact manifest SHA/size, and is insert-only. Existing chunks cannot be overwritten. `--upload` sends to a fixed production domain over TLS; each run has its own receipt, including failures. The entire import can be retried idempotently; do not delete failure receipts or count failed requests as success.

After completion, remove the migration's exact permit through the connector, verify POST is rejected, and delete the local capability created by migration. Requests that passed the permit check may finish before revocation; the capability cannot write bytes outside the manifest. Without a valid permit, the endpoint rejects imports. Do not garbage-collect chunks automatically; before deleting an old version, check every deployment needed for rollback.

Local transfer took 41.312 seconds for a 512 KiB part. The repository owner authorized a temporary public-asset key `SPHEREX_PUBLIC_DATA_IMPORT` in GitHub Actions; the workflow runs manually on main and checks that both the launcher and rerun initiator are owners. The secret is limited to the import step and is not put in artifacts; Mongo URI is not in GitHub. Artifacts retain only import/reconciliation receipts. Delete the Secret and permit after completion; canonical mode only reconciles and does not use the secret.

Import run `41208174465` uploaded all 426 parts; initial reconciliation stopped at an NPZ because the CDN added gzip for clients advertising gzip. The file still decompressed correctly in the browser; the old verifier confused stored bytes with HTTP-compressed bytes. That run remains unchanged. The new verifier negotiates identity for identity products/chunks and gzip for gzip products while checking media type, encoding, and received bytes; it does not skip hash validation.

If import/reader fails, retain the static release. If cutover fails, roll back to the phase-1 release: data remains in Git/CDN and old reviews still use the original database. When logical size exceeds 70% of the limit or measured load causes congestion, assess retention/versioning and binary storage before considering sharding across clusters; multiple M0 clusters are not proven sharding or high availability.

## UX retested

WISE and IRSA use Data → Compare → Check → Record. The IRSA list opens immediately after metadata, even if the first image fails; observations without URLs are skipped and a Retry image button is available. The user can proceed to Check only after two images load. The list labels A/B and shows UTC dates; the date range remains in the URL.

Drafts stay in sessionStorage for the current tab (up to 50, expire after 24 hours), keyed to analysis/selection or query/A/B; they are not uploaded to a server automatically. Reload restores an IRSA draft only after selecting the exact pair again. Closing the tab may lose a draft; export JSON to retain it. WISE export includes saved reviews and unsaved drafts in separate fields; text being edited is not silently omitted. Local saving does not promise synchronization.

Agent-simulated/browser tests do not replace testing with real newcomers. Operational/public results and remaining limits are added in the post-cutover release receipt; do not treat the design document as evidence that migration has completed.
