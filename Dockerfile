FROM python:3.13-slim AS minimal

ENV VERSION_CT=0.9.0 \
    VERSION_HELM=3.18.4

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
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash -s -- --version "v${VERSION_HELM}" \
 && helm plugin install https://github.com/databus23/helm-diff \
 && python3 -m pip install --disable-pip-version-check --no-cache-dir \
        ansible-core==2.18.7 \
        ansible==11.7.0 \
        bcrypt==4.3.0 \
        humanfriendly==10.0 \
        Jinja2==3.1.3 \
        jmespath==1.0.1 \
        kubernetes==33.1.0 \
        netaddr==1.1.0 \
        passlib==1.7.4 \
        pyjwt==2.10.1 \
 && curl -Lo ct https://github.com/coreos/container-linux-config-transpiler/releases/download/v${VERSION_CT}/ct-v${VERSION_CT}-x86_64-unknown-linux-gnu \
 && chmod +x ct \
 && mv ct /usr/local/bin/

COPY ansible.cfg /etc/ansible/ansible.cfg
COPY gai.conf /etc/gai.conf

ENTRYPOINT []

FROM minimal AS gcloud

ENV CLOUD_SDK_VERSION=530.0.0

ENV PATH=/google-cloud-sdk/bin:$PATH

RUN curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz \
 && tar xzf google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz \
 && rm google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz \
 && gcloud config set core/disable_usage_reporting true \
 && gcloud config set component_manager/disable_update_check true \
 && gcloud config set metrics/environment github_docker_image \
 && gcloud components install gke-gcloud-auth-plugin \
 && rm -rf /google-cloud-sdk/.install/.backup \
 && gcloud --version
