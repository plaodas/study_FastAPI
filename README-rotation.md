**Log Rotation**

- **Purpose:** entrypoint rotates logs in `/app/logs` (host `backend/logs`) when they exceed a configured size.

- **Files rotated:** any `*.log` inside `/app/logs` (e.g. `startup.log`, `uvicorn.log`). Rotated archives are gzipped and named `<basename>-YYYYmmddTHHMMSSZ.log.gz`.
- **Config (environment variables, set in `compose.yaml`):**
  - `STARTUP_ROTATE_MAX_BYTES` — max bytes before rotation (default `5242880` = 5MB)
  - `STARTUP_ROTATE_KEEP` — how many rotated archives to keep per log (default `7`)
  - `STARTUP_ROTATE_INTERVAL` — rotation check interval in seconds (default `300`)

- **How uvicorn logs are captured:** `compose.yaml` runs uvicorn with stdout/stderr redirected to `/app/logs/uvicorn.log` so the entrypoint rotation covers it.

- **Quick test:** (from project root, PowerShell)
```powershell
python .\tools\test_rotation.py
```

If the script exits with code `0` it detected rotated `startup-*.log.gz` and `uvicorn-*.log.gz` in `backend/logs`.
