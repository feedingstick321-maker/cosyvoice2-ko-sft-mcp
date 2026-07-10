# GCP VM Usage Collector

The production collector runs as an isolated FastAPI service on `127.0.0.1:8092`, stores events in
SQLite WAL mode, and is exposed through Nginx. It does not host inference or model files.

Public ingestion endpoint:

```text
https://34-64-223-17.sslip.io/cosyvoice-usage/v1/events
```

Reporting remains disabled locally until each user explicitly calls
`configure_usage_reporting(enabled=true)`. The database does not store IP addresses, synthesis
text, prompt text, audio, voice names, or file paths. Nginx and Uvicorn access logging are disabled
for this collector so client IP addresses are not retained in service logs. Events are retained for
180 days by default and older records are removed when the service starts.

Administrator endpoints require the bearer token stored in `/etc/cosyvoice-usage.env`:

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://34-64-223-17.sslip.io/cosyvoice-usage/v1/stats
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://34-64-223-17.sslip.io/cosyvoice-usage/v1/participants
```

The aggregate response includes installations, synthesis count, success rate, average real-time
factor, feedback average, GPU distribution, and common errors. The participant response identifies
only a voluntarily supplied participant ID or an anonymous installation-ID suffix.

From the release workstation, `scripts/gcp_usage_stats.ps1` reads either report without printing the
administrator token:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\gcp_usage_stats.ps1 -View Summary
powershell -ExecutionPolicy Bypass -File .\scripts\gcp_usage_stats.ps1 -View Participants
```
