FROM python:3.11-slim AS minimal

ENV VERSION_CT=0.9.0 \
    VERSION_HELM=3.16.4 \
    METAL_ROLES_VERSION=metal-stack-release-vector-module

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
        ansible-core==2.15.4 \
        ansible==8.4.0 \
        bcrypt==4.3.0 \
        humanfriendly==10.0 \
        Jinja2==3.1.3 \
        jmespath==1.0.1 \
        kubernetes==25.3.0 \
        netaddr==1.1.0 \
        opencontainers==0.0.14 \
        passlib==1.7.4 \
        pyjwt==2.8.0 \
 && curl -Lo ct https://github.com/coreos/container-linux-config-transpiler/releases/download/v${VERSION_CT}/ct-v${VERSION_CT}-x86_64-unknown-linux-gnu \
 && chmod +x ct \
 && mv ct /usr/local/bin/

RUN mkdir -p /usr/share/ansible/collections/ansible_collections/metalstack/base/plugins \
 && cd /usr/share/ansible/collections/ansible_collections/metalstack/base/plugins \
 && mkdir action modules \
 && curl -Lo action/metal_stack_release_vector.py https://raw.githubusercontent.com/metal-stack/ansible-common/${METAL_ROLES_VERSION}/action_plugins/metal_stack_release_vector.py \
 && curl -Lo modules/metal_stack_release_vector.py https://raw.githubusercontent.com/metal-stack/ansible-common/${METAL_ROLES_VERSION}/library/metal_stack_release_vector.py \
 && chmod +x action/metal_stack_release_vector.py modules/metal_stack_release_vector.py

COPY ansible.cfg /etc/ansible/ansible.cfg
COPY gai.conf /etc/gai.conf

ENTRYPOINT []

FROM minimal AS gcloud

ENV CLOUD_SDK_VERSION=507.0.0

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
