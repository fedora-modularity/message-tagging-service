FROM registry.fedoraproject.org/fedora:29

LABEL maintainer="Factory 2 Team" \
      description="A microservice triggered by specific message to tag a build."

RUN dnf install -y \
        python3-pyyaml \
        python3-fedmsg \
        python3-koji \
        python3-requests \
        python3-qpid-proton \
        krb5-workstation \
    && dnf clean all

RUN sed -i '/default_ccache_name = KEYRING:persistent:%{uid}/d' /etc/krb5.conf

WORKDIR /src

COPY . .
# Delete the default fedmsg configuration files, and rely on the user supplying
# the correct configuration as a mounted volume in /etc/fedmsg.d
RUN rm -rf ./fedmsg.d && rm -rf /etc/fedmsg.d
RUN sed -i '/koji/d' requirements.txt
RUN python3 -m pip install --no-deps .

# Mount to a directory holding config file.
VOLUME /etc/mts
# Mount to a directory holding keytab and probably message bus certs.
VOLUME /etc/secrets
#USER 1001
CMD ["fedmsg-hub-3"]
