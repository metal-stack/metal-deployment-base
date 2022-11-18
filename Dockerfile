FROM python:3.9.15-slim

ENV VERSION_ANSIBLE=6.6.0 \
    VERSION_CT=0.9.0 \
    VERSION_HELM=3.10.2

ENV PATH /google-cloud-sdk/bin:$PATH

RUN set -x \
 && apt-get update \
 && apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        connect-proxy \
        git \
        make \
        openssh-client \
        rsync \
 && apt clean \
 && apt autoclean \
 && curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash -s -- --version "v${VERSION_HELM}" \
 && python3 -m pip install --upgrade pip \
 && python3 -m pip install ansible==${VERSION_ANSIBLE} Jinja2==3.0.1 netaddr==0.8.0 humanfriendly==9.2 kubernetes==25.3.0 pyjwt==2.6.0 google-auth \
 && curl -Lo ct https://github.com/coreos/container-linux-config-transpiler/releases/download/v${VERSION_CT}/ct-v${VERSION_CT}-x86_64-unknown-linux-gnu \
 && chmod +x ct \
 && mv ct /usr/local/bin/ \
 && curl -fsSL https://dl.minio.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
 && chmod +x /usr/local/bin/mc \
 && rm -rf /var/cache/apt/* /tmp/*

COPY ansible.cfg /etc/ansible/ansible.cfg

ENTRYPOINT []
