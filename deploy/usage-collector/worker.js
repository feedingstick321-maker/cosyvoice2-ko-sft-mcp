const MAX_BODY_BYTES = 16 * 1024;
const ALLOWED_EVENTS = new Set([
  "reporting_enabled",
  "synthesis_finished",
  "quality_feedback",
]);

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function text(value, maxLength) {
  if (value === null || value === undefined) return null;
  return String(value).slice(0, maxLength);
}

function number(value) {
  return Number.isFinite(value) ? value : null;
}

async function ingest(request, env) {
  const length = Number(request.headers.get("content-length") || 0);
  if (length > MAX_BODY_BYTES) return jsonResponse({ error: "payload too large" }, 413);

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: "invalid json" }, 400);
  }
  if (body.schema_version !== 1 || !ALLOWED_EVENTS.has(body.event)) {
    return jsonResponse({ error: "unsupported event" }, 400);
  }

  const client = body.client || {};
  const properties = body.properties || {};
  const eventId = text(body.event_id, 64);
  const installId = text(body.install_id, 64);
  if (!eventId || !installId) return jsonResponse({ error: "missing id" }, 400);

  await env.DB.prepare(`
    INSERT OR IGNORE INTO usage_events (
      event_id, received_at, event_time, event_name, install_id, participant_id,
      client_version, operating_system, python_version, gpu, vram_gib, cuda_available,
      success, elapsed_sec, duration_sec, text_chars_bucket, error_type,
      feedback_score, feedback_category, feedback_comment
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    eventId,
    Math.floor(Date.now() / 1000),
    number(body.timestamp) || Math.floor(Date.now() / 1000),
    body.event,
    installId,
    text(body.participant_id, 100),
    text(client.version, 32),
    text(client.os, 32),
    text(client.python, 16),
    text(client.gpu, 120),
    number(client.vram_gib),
    client.cuda_available === true ? 1 : client.cuda_available === false ? 0 : null,
    properties.success === true ? 1 : properties.success === false ? 0 : null,
    number(properties.elapsed_sec),
    number(properties.duration_sec),
    text(properties.text_chars_bucket, 16),
    text(properties.error_type, 80),
    number(properties.score),
    text(properties.category, 40),
    text(properties.comment, 500),
  ).run();
  return jsonResponse({ accepted: true }, 202);
}

async function stats(request, env) {
  const expected = `Bearer ${env.ADMIN_TOKEN || ""}`;
  if (!env.ADMIN_TOKEN || request.headers.get("authorization") !== expected) {
    return jsonResponse({ error: "unauthorized" }, 401);
  }
  const summary = await env.DB.prepare(`
    SELECT
      COUNT(DISTINCT install_id) AS installations,
      COUNT(DISTINCT CASE WHEN participant_id IS NOT NULL THEN participant_id END) AS identified_participants,
      SUM(CASE WHEN event_name = 'synthesis_finished' THEN 1 ELSE 0 END) AS syntheses,
      ROUND(100.0 * AVG(CASE WHEN event_name = 'synthesis_finished' THEN success END), 2) AS success_rate_pct,
      ROUND(AVG(CASE WHEN duration_sec > 0 THEN elapsed_sec / duration_sec END), 3) AS average_rtf,
      ROUND(AVG(CASE WHEN event_name = 'quality_feedback' THEN feedback_score END), 2) AS feedback_average
    FROM usage_events
  `).first();
  const gpus = await env.DB.prepare(`
    SELECT gpu, COUNT(DISTINCT install_id) AS installations
    FROM usage_events WHERE gpu IS NOT NULL
    GROUP BY gpu ORDER BY installations DESC LIMIT 20
  `).all();
  const errors = await env.DB.prepare(`
    SELECT error_type, COUNT(*) AS occurrences
    FROM usage_events WHERE success = 0 AND error_type IS NOT NULL
    GROUP BY error_type ORDER BY occurrences DESC LIMIT 20
  `).all();
  return jsonResponse({ summary, gpus: gpus.results, errors: errors.results });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/v1/events") {
      return ingest(request, env);
    }
    if (request.method === "GET" && url.pathname === "/v1/stats") {
      return stats(request, env);
    }
    return jsonResponse({ service: "cosyvoice-ko-usage", status: "ok" });
  },
};
