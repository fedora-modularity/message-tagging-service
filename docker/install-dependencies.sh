#!/usr/bin/bash

set -euo pipefail

rcm_tools_repos=${1:-}

# The URL to RCM Tools Fedora repos

dependencies=(
    python3-fedora-messaging
    python3-flask
    python3-gunicorn
    python3-koji
    python3-qpid-proton
    python3-pip
    python3-prometheus_client
    python3-pyyaml
    python3-requests
    krb5-workstation
)

if [ -n "$rcm_tools_repos" ]; then
    repo_file=/etc/yum.repos.d/rcm-tools-fedora.repo
    curl -L -o $repo_file $rcm_tools_repos
    # Since we don't trust any internal CAs at this point, we must connect over
    # http
    sed -i 's/https:/http:/g' $repo_file

    dependencies+=(python3-rhmsg)
fi

dnf install -y \
    --setopt=deltarpm=0 \
    --setopt=install_weak_deps=false \
    --setopt=tsflags=nodocs \
    ${dependencies[@]}

dnf clean all
