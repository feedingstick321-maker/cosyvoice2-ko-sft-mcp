# Optional Usage Reporting

Inference is local. Usage reporting is disabled by default and starts only after the user explicitly
opts in with the `configure_usage_reporting` MCP tool. The release has a project-operated GCP HTTPS
endpoint configured; `COSYVOICE_USAGE_ENDPOINT` can replace or disable it.

## Sent after opt-in

- random installation ID
- optional participant ID entered by the user
- package version, operating system, Python version
- GPU model, VRAM size, and whether CUDA is available
- synthesis success or failure, elapsed time, output duration, text-length bucket
- exception class on failure
- an explicit 1-5 quality score, category, and optional comment submitted through
  `report_feedback`

## Never sent

- synthesis text or prompt text
- reference or generated audio
- voice profile names
- local file names or paths
- IP address collected by this application

The production GCP collector disables Nginx and Uvicorn access logs and does not retain client IP
addresses. Other operators must publish a retention policy and access controls before replacing the
default endpoint. The project-operated collector retains events for 180 days by default. Disabling
reporting stops new events immediately. Removing
`usage-reporting.json` resets the local installation ID.
