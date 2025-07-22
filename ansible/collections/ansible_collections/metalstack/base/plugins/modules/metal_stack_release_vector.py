#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_stack_release_vector
short_description: Downloads the metal-stack release vector OCI artifact
version_added: "2.15"
description:
    - This module downloads the metal-stack release vector OCI artifact.
options:
    version:
        description:
            - The release version reference to download.
        required: true
author:
    - metal-stack
notes:
    - This module depends on the [opencontainers]("https://github.com/vsoch/oci-python") library.
'''

EXAMPLES = '''
- name: download metal-stack release vector
  metal_stack_release_vector:
    version: v0.25.14
  register: release_vector
'''
