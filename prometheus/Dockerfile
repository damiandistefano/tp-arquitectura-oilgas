FROM prom/prometheus:v2.52.0

USER root
COPY prometheus.yml /etc/prometheus/prometheus.yml
COPY rules/ /etc/prometheus/rules/
RUN chmod 644 /etc/prometheus/prometheus.yml /etc/prometheus/rules/*
USER nobody
