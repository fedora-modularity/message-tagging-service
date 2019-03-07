FROM registry.fedoraproject.org/fedora:29

LABEL maintainer="Factory 2 Team" \
      description="A microservice triggered by specific message to tag a build."

# This is an argument for a URL to a DNF repo file of a repo that contains
# python3-rhmsg.
# This argument could be omitted when build image for Fedora.
ARG rcm_tools_repo_file

RUN sed -i '/default_ccache_name = KEYRING:persistent:%{uid}/d' /etc/krb5.conf

RUN chmod 777 /etc/pki/tls/certs/ca-bundle.crt

WORKDIR /src

# This will allow a non-root user to install a custom root CA at run-time
COPY . .

RUN docker/install-dependencies.sh $rcm_tools_repo_file

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
EXPOSE 8080
ENTRYPOINT ["docker/entrypoint.sh"]
