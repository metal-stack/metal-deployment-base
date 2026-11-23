#!/usr/bin/env bash
set -euo pipefail

ansible -m metalstack.base.metal_stack_release_vector localhost

find ~/.ansible/roles -maxdepth 1 -type d -ls

roles="$(find ~/.ansible/roles -mindepth 1 -maxdepth 1)"
if [ -z "${roles}" ]; then
  echo "no roles were downloaded" >&2
  exit 1
fi
