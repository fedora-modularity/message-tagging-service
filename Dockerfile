FROM registry.fedoraproject.org/fedora:29

LABEL maintainer="Factory 2 Team" \
      description="A microservice triggered by specific message to tag a build."

# This is an argument for a URL to a DNF repo file of a repo that contains python3-rhmsg
ARG rcm_tools_repo_file
ADD $rcm_tools_repo_file /etc/yum.repos.d/rcm-tools-fedora.repo
# Since we don't trust any internal CAs at this point, we must connect over http
RUN sed -i 's/https:/http:/g' /etc/yum.repos.d/rcm-tools-fedora.repo

RUN dnf install -y \
        --setopt=deltarpm=0 \
        --setopt=install_weak_deps=false \
        --setopt=tsflags=nodocs \
        python3-pyyaml \
        python3-fedmsg \
        python3-koji \
        python3-requests \
        python3-qpid-proton \
        python3-rhmsg \
        krb5-workstation \
    && dnf clean all

RUN sed -i '/default_ccache_name = KEYRING:persistent:%{uid}/d' /etc/krb5.conf

WORKDIR /src

# This will allow a non-root user to install a custom root CA at run-time
RUN chmod 777 /etc/pki/tls/certs/ca-bundle.crt
COPY . .
# Delete the default fedmsg configuration files, and rely on the user supplying
# the correct configuration as a mounted volume in /etc/fedmsg.d
RUN rm -rf ./fedmsg.d && rm -rf /etc/fedmsg.d
RUN sed -i '/koji/d' requirements.txt
RUN python3 -m pip install --no-deps .

# Mount to a directory holding the MTS config file
VOLUME /etc/mts
# Mount to a directory holding the fedmsg config file(s)
VOLUME /etc/fedmsg.d
USER 1001
CMD ["/usr/bin/bash", "-c", "docker/install-ca.sh && exec fedmsg-hub-3"]
