FROM python:buster

ENV VERSION_ANSIBLE=2.9.2 \
    VERSION_HELM=3.1.1 \
    VERSION_STERN=1.11.0 \
    VERSION_VAGRANT=2.2.9

# vagrant is required for running the vagrant dynamic inventory script from within the container...
ARG VAGRANT_PACKAGE_URL=https://releases.hashicorp.com/vagrant/${VERSION_VAGRANT}/vagrant_${VERSION_VAGRANT}_x86_64.deb

RUN set -x \
 && export CLOUD_SDK_REPO="cloud-sdk-buster" \
 && echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
 && curl -f https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
 && apt-get update \
 && apt-get install --yes --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg2 \
        google-cloud-sdk \
        software-properties-common \
        connect-proxy \
        libvirt-dev \
        ruby-dev \
        rsync \
 && curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - \
 && add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian buster stable" \
 && apt-get update \
 && apt-get install --yes --no-install-recommends docker-ce  \
 && curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash -s -- --version "v${VERSION_HELM}" \
 && pip install --upgrade pip \
 && pip install ansible==${VERSION_ANSIBLE} Jinja2==2.11.1 netaddr==0.7.19 humanfriendly==8.1 openshift==0.11.1 \
 && curl -fo vagrant.deb $VAGRANT_PACKAGE_URL \
 && dpkg -i vagrant.deb \
 && rm -f vagrant.deb \
 && vagrant plugin install vagrant-libvirt \
 && curl -Lo stern https://github.com/wercker/stern/releases/download/${VERSION_STERN}/stern_linux_amd64 \
 && chmod +x stern \
 && mv stern /usr/local/bin/ \
 && curl -fsSL https://dl.minio.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
 && chmod +x /usr/local/bin/mc

ENTRYPOINT []
