FROM alpine:3.19 AS envsubst-builder
RUN apk add --no-cache gettext

FROM prom/alertmanager:v0.27.0
COPY --from=envsubst-builder /usr/bin/envsubst /usr/bin/envsubst
COPY alertmanager.yml /etc/alertmanager/alertmanager.yml.tmpl
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
