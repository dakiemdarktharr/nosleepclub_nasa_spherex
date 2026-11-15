# Manual Review Backups

The `scripts/backup_reviews_local.py` tool reads only the existing Atlas database's `reviews` collection in `nosleepclub_nasa_spherex`. This is a manual operation; it does not enable a paid service or scheduled job. It does not back up public image chunks, API counters, or user cookies.

## Run on Windows

Use a Python environment with the current test dependencies (`pymongo`, `cryptography`). Run from the project directory:

```powershell
.venv/Scripts/python.exe -m scripts.backup_reviews_local snapshot
```

Enter the existing Atlas URI at the hidden prompt, or inject `SPHEREX_BACKUP_MONGODB_URI` through a secret manager. Never put the URI in a command, script, terminal history, or Git. The MongoDB account needs permission to read the collection and use snapshot sessions; the backup does not require additional production write permission. The snapshot uses a read-only transaction with snapshot read concern.

The encrypted file is stored at `%LOCALAPPDATA%/SPHEREx/backups/reviews-<UTC>-<random>.spherex.enc`. The Fernet key is stored only as `review-key.dpapi`, protected by Windows DPAPI for the current user. No plaintext BSON file is created. Output contains only the filename, time, record count, and SHA-256 of the ciphertext. The tool does not print the URI, key, review contents, or owner ID.

Encrypted files and the current-user DPAPI-protected key stay outside the repository. Losing the Windows profile or DPAPI key can make these backups unrecoverable. This local mechanism is not an off-device disaster-recovery copy. Do not copy decrypted keys into the repository or CI artifacts. No automatic retention/deletion policy is enabled; keep encrypted copies under the owner's approved retention policy.

```powershell
.venv/Scripts/python.exe -m scripts.backup_reviews_local verify --file reviews-<UTC>-<random>.spherex.enc
```

`verify` decrypts in memory and checks integrity and BSON schema; it **does not prove that MongoDB restored successfully**. Limits: 20,000 records and 128 MiB of plaintext. Exceeding a limit fails the entire operation instead of silently truncating. ObjectId, hexadecimal string IDs, UTC timestamps, Binary, and Int64 values are preserved.

## Isolated restore drill

Prepare a dedicated loopback MongoDB test replica set named `codex-review-test`, using the default port 27027. Do not tunnel to a real system. The tool accepts only `127.0.0.1` and this replica set; there is no command to restore to Atlas.

```powershell
.venv/Scripts/python.exe -m scripts.backup_reviews_local restore-drill --file reviews-<UTC>-<random>.spherex.enc --local-port 27027
```

The drill creates a new `review_backup_dst_<uuid4>` database, refuses an existing target, restores only unexpired documents, checks BSON equality, then restores and verifies the unique owner/key index and TTL index. It does not change the production database or revive expired reviews. A failed drill may leave an isolated target for investigation; the CLI does not delete databases automatically. The target name is reported after a successful drill.

Unexpired records continue to use their original TTL. Restoring reviews does not restore a user's lost cookie or automatically grant a new device access.

## Verification status

Unit tests cover authenticated encryption, BSON types, ID formats, refusal of existing targets and invalid sources, and actual Windows DPAPI key protection. The MongoDB integration test runs only when `REVIEW_TEST_MONGODB_URI` points to the isolated loopback fixture. A skipped test is not a successful restore drill.

The synthetic restore into an isolated MongoDB replica set passed in [GitHub CI run 43582777817](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/actions/runs/43582777817), including BSON equality, indexes, and expiry handling. Windows DPAPI was tested locally. No production snapshot has been taken because the production URI is unavailable locally. Production backup/restore timing, capacity, and recovery objectives remain unmeasured. These tests do not show that production reviews have already been backed up.

References: [Windows current-user DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata), [PyMongo sessions and transactions](https://pymongo.readthedocs.io/en/stable/api/pymongo/client_session.html), [existing fixture-only protocol](BACKUP_RESTORE_PROTOCOL.md).
