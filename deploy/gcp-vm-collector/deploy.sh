#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/cosyvoice-usage
DATA_DIR=/var/lib/cosyvoice-usage
ENV_FILE=/etc/cosyvoice-usage.env
SERVICE_USER=cosyvoice-usage
HOSTNAME=34-64-223-17.sslip.io

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  sudo useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

sudo install -d -m 0755 "$APP_DIR"
sudo install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0750 "$DATA_DIR"
sudo install -m 0644 app.py requirements.txt "$APP_DIR"/

if [[ ! -x "$APP_DIR/venv/bin/python" ]]; then
  sudo python3 -m venv "$APP_DIR/venv"
fi
sudo "$APP_DIR/venv/bin/pip" install --disable-pip-version-check -r "$APP_DIR/requirements.txt"

if [[ ! -f "$ENV_FILE" ]]; then
  admin_token="$(openssl rand -hex 32)"
  sudo sh -c "umask 077; printf 'DATABASE_PATH=%s/events.db\nADMIN_TOKEN=%s\nRETENTION_DAYS=180\n' '$DATA_DIR' '$admin_token' > '$ENV_FILE'"
fi
if ! sudo grep -q '^RETENTION_DAYS=' "$ENV_FILE"; then
  echo 'RETENTION_DAYS=180' | sudo tee -a "$ENV_FILE" >/dev/null
fi

sudo install -m 0644 cosyvoice-usage.service /etc/systemd/system/cosyvoice-usage.service
sudo install -m 0644 nginx-location.conf /etc/nginx/snippets/cosyvoice-usage-location.conf
sudo tee /etc/nginx/conf.d/cosyvoice-usage-limit.conf >/dev/null <<'EOF'
limit_req_zone $binary_remote_addr zone=cosyvoice_usage:10m rate=30r/m;
EOF
if [[ ! -f /etc/nginx/sites-available/cosyvoice-usage ]]; then
  sudo tee /etc/nginx/sites-available/cosyvoice-usage >/dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $HOSTNAME;
    access_log off;
    include /etc/nginx/snippets/cosyvoice-usage-location.conf;
    location = /cosyvoice-usage/health {
        proxy_pass http://127.0.0.1:8092/health;
    }
}
EOF
fi
sudo ln -sfn /etc/nginx/sites-available/cosyvoice-usage /etc/nginx/sites-enabled/cosyvoice-usage

sudo systemctl daemon-reload
sudo systemctl enable cosyvoice-usage.service
sudo systemctl restart cosyvoice-usage.service
sudo nginx -t
sudo systemctl reload nginx

if ! command -v certbot >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-nginx
fi
if ! sudo test -e "/etc/letsencrypt/live/$HOSTNAME/fullchain.pem"; then
  sudo certbot --nginx -d "$HOSTNAME" --non-interactive --agree-tos \
    --register-unsafely-without-email --redirect
fi

sudo HOSTNAME="$HOSTNAME" python3 - <<'PY'
import os
from pathlib import Path

path = Path("/etc/nginx/sites-available/cosyvoice-usage")
lines = path.read_text(encoding="utf-8").splitlines()
result = []
for index, line in enumerate(lines):
    result.append(line)
    if f"server_name {os.environ['HOSTNAME']};" in line:
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if next_line != "access_log off;":
            result.append("    access_log off;")
path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY

for _ in {1..20}; do
  if curl --fail --silent http://127.0.0.1:8092/health; then
    break
  fi
  sleep 0.5
done
curl --fail --silent http://127.0.0.1:8092/health >/dev/null
sudo nginx -t
sudo systemctl reload nginx
