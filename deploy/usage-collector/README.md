# Usage Collector Deployment

This optional Cloudflare Worker stores explicitly opted-in usage events in D1. It does not host
inference or model files.

```bash
cd deploy/usage-collector
npx wrangler d1 create cosyvoice-ko-usage
cp wrangler.toml.example wrangler.toml
# Put the returned database_id in wrangler.toml.
npx wrangler d1 execute cosyvoice-ko-usage --remote --file schema.sql
npx wrangler secret put ADMIN_TOKEN
npx wrangler deploy
```

Set the deployed ingestion URL in the MCP environment:

```text
COSYVOICE_USAGE_ENDPOINT=https://your-worker.workers.dev/v1/events
```

Reporting still remains disabled until each user calls `configure_usage_reporting(enabled=true)`.
Read aggregate statistics with:

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://your-worker.workers.dev/v1/stats
```

The response reports installations, voluntarily identified participants, synthesis count, success
rate, average real-time factor, feedback average, GPU distribution, and common exception classes.
Keep `ADMIN_TOKEN` out of source control and publish a retention period before enabling collection.
