#!/usr/bin/env bash
set -euo pipefail

DOMAIN="thepccoach.com"
WWW_DOMAIN="www.thepccoach.com"
NGINX_CONF="/etc/nginx/sites-available/$DOMAIN"

echo "==> Installing Nginx and Certbot..."
apt update -qq
apt install -y nginx certbot python3-certbot-nginx

echo "==> Writing Nginx config..."
cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $DOMAIN $WWW_DOMAIN;

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

echo "==> Enabling site..."
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/"$DOMAIN"

echo "==> Testing Nginx config..."
nginx -t

echo "==> Reloading Nginx..."
systemctl reload nginx

echo "==> Obtaining SSL certificate..."
certbot --nginx -d "$DOMAIN" -d "$WWW_DOMAIN" --non-interactive --agree-tos --redirect \
  --email "$(git config user.email 2>/dev/null || echo 'admin@thepccoach.com')"

echo ""
echo "Done. Testing HTTPS endpoint..."
curl -sf https://"$DOMAIN"/health && echo " <- health check passed" || echo " <- health check failed (check logs)"
