FROM ubuntu:jammy
LABEL maintainer=rasmus.toftdahl.olesen@gmail.com
RUN apt-get update \
    && apt-get install -y \
    curl \
    sudo \
    make \
    ca-certificates \
    gettext-base \
    git \
    gpg \
    && curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | tee /etc/apt/sources.list.d/kubernetes.list \
    && curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | tee /etc/apt/sources.list.d/helm-stable-debian.list \
    && apt-get update && apt-get install -y \
    kubectl \
    helm \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSLo sops.deb https://github.com/mozilla/sops/releases/download/v3.7.3/sops_3.7.3_amd64.deb \
    && dpkg -i sops.deb \
    && rm -f sops.deb


ADD entrypoint.sh /
RUN chmod a+x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
