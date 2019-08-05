#!/usr/bin/bash

set -euo pipefail

rcm_tools_repos=${1:-}

# The URL to RCM Tools Fedora repos

# Pin moksha hub to a known good version until this is fixed:
#   https://github.com/mokshaproject/moksha/issues/69
dependencies=(
    python3-pyyaml
    python3-moksha-hub-1.5.13-1.fc29
    python3-fedmsg
    python3-koji
    python3-requests
    python3-qpid-proton
    python3-gunicorn
    python3-flask
    python3-prometheus_client
    krb5-workstation
)

if [ -n "$rcm_tools_repos" ]; then
    repo_file=/etc/yum.repos.d/rcm-tools-fedora.repo
    curl -L -o $repo_file $rcm_tools_repos
    # Since we don't trust any internal CAs at this point, we must connect over
    # http
    sed -i 's/https:/http:/g' $repo_file

    dependencies+=(python3-rhmsg)
else
    dependencies+=(fedora-packager koji)
fi

dnf install -y \
    --setopt=deltarpm=0 \
    --setopt=install_weak_deps=false \
    --setopt=tsflags=nodocs \
    ${dependencies[@]}

dnf clean all
