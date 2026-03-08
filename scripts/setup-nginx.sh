#!/usr/bin/env bash
set -euo pipefail

# --- Config ---
DOMAIN="thepccoach.com"
WWW_DOMAIN="www.thepccoach.com"
NGINX_CONF="/etc/nginx/sites-available/$DOMAIN"

# --- Root check ---
if [[ $EUID -ne 0 ]]; then
  echo "Error: this script must be run as root (use sudo or log in as root)." >&2
  exit 1
fi

# --- Email for Certbot ---
if [[ -z "${CERTBOT_EMAIL:-}" ]]; then
  read -rp "Enter your email for SSL certificate notifications: " CERTBOT_EMAIL
  if [[ -z "$CERTBOT_EMAIL" ]]; then
    echo "Error: email is required for Certbot." >&2
    exit 1
  fi
fi

# --- Check containers are running ---
echo "==> Checking containers..."
if ! docker ps --format '{{.Names}}' | grep -q "pccoach-backend"; then
  echo "Error: backend container is not running. Run 'make up' first." >&2
  exit 1
fi
if ! docker ps --format '{{.Names}}' | grep -q "pccoach-frontend"; then
  echo "Error: frontend container is not running. Run 'make up' first." >&2
  exit 1
fi

# --- Install ---
echo "==> Installing Nginx and Certbot..."
apt update -qq
apt install -y nginx certbot python3-certbot-nginx

# --- Disable default site ---
echo "==> Disabling default Nginx site..."
rm -f /etc/nginx/sites-enabled/default

# --- Write config ---
echo "==> Writing Nginx config..."
cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $DOMAIN $WWW_DOMAIN;

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# --- Enable site ---
echo "==> Enabling site..."
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/"$DOMAIN"

# --- Test and reload ---
echo "==> Testing Nginx config..."
nginx -t

echo "==> Reloading Nginx..."
systemctl reload nginx

# --- SSL ---
echo "==> Obtaining SSL certificate..."
certbot --nginx -d "$DOMAIN" -d "$WWW_DOMAIN" \
  --non-interactive --agree-tos --redirect \
  --email "$CERTBOT_EMAIL"

# --- Final health check ---
echo ""
echo "==> Testing HTTPS endpoint..."
curl -sf "https://$DOMAIN/health" && echo " <- health check passed" || echo " <- health check failed (run: make logs)"
