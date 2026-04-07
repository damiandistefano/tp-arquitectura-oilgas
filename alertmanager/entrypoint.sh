#!/bin/sh
sed \
  -e "s|\${SLACK_WEBHOOK_URL}|${SLACK_WEBHOOK_URL}|g" \
  -e "s|\${ALERT_EMAIL}|${ALERT_EMAIL}|g" \
  -e "s|\${SMTP_HOST}|${SMTP_HOST}|g" \
  -e "s|\${SMTP_USER}|${SMTP_USER}|g" \
  -e "s|\${SMTP_PASSWORD}|${SMTP_PASSWORD}|g" \
  /etc/alertmanager/alertmanager.yml.tmpl > /etc/alertmanager/alertmanager.yml

exec /bin/alertmanager \
  --config.file=/etc/alertmanager/alertmanager.yml \
  --storage.path=/alertmanager \
  "$@"
