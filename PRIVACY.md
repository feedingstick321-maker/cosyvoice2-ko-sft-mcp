# Optional Usage Reporting

Inference is local. Usage reporting is disabled by default and cannot be enabled unless the
distribution operator configures `COSYVOICE_USAGE_ENDPOINT` and the user explicitly opts in with
the `configure_usage_reporting` MCP tool.

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

The receiving HTTP service may observe network metadata such as an IP address. Its operator must
publish a retention policy and access controls before enabling the endpoint in a distribution.
Disabling reporting stops new events immediately. Removing `usage-reporting.json` resets the local
installation ID.
