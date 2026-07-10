CREATE TABLE IF NOT EXISTS usage_events (
  event_id TEXT PRIMARY KEY,
  received_at INTEGER NOT NULL,
  event_time INTEGER NOT NULL,
  event_name TEXT NOT NULL,
  install_id TEXT NOT NULL,
  participant_id TEXT,
  client_version TEXT,
  operating_system TEXT,
  python_version TEXT,
  gpu TEXT,
  vram_gib REAL,
  cuda_available INTEGER,
  success INTEGER,
  elapsed_sec REAL,
  duration_sec REAL,
  text_chars_bucket TEXT,
  error_type TEXT,
  feedback_score INTEGER,
  feedback_category TEXT,
  feedback_comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_usage_events_time ON usage_events(received_at);
CREATE INDEX IF NOT EXISTS idx_usage_events_install ON usage_events(install_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_name ON usage_events(event_name);
