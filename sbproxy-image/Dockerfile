FROM ubuntu:24.04

ARG SBPROXY_VERSION=v1.1.0
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tar wget \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64|arm64) arch="${TARGETARCH}" ;; \
      *) echo "unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    asset="sbproxy_linux_${arch}.tar.gz"; \
    base="https://github.com/soapbucket/sbproxy/releases/download/${SBPROXY_VERSION}"; \
    curl -fsSLo "/tmp/${asset}" "${base}/${asset}"; \
    curl -fsSLo "/tmp/${asset}.sha256" "${base}/${asset}.sha256"; \
    cd /tmp; \
    sha256sum -c "${asset}.sha256"; \
    tar -xzf "${asset}"; \
    install -m 0755 sbproxy /usr/local/bin/sbproxy; \
    rm -rf /tmp/*

EXPOSE 8080 9090
ENTRYPOINT ["/usr/local/bin/sbproxy"]
CMD ["serve", "-f", "/etc/sbproxy/sb.yml"]
