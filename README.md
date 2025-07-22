# metal-stack deployment

This repository builds the deployment base image that can be used for deploying metal-stack with Ansible.

## Using metal-stack Ansible Roles

In case your deployment depends on Ansible roles that are referenced in a metal-stack release vector (e.g. [releases](https://github.com/metal-stack/releases)), these role dependencies can be dynamically installed through the release vector OCI artifacts by running the following command before playbook execution:

```bash
# requires the metal_stack_release_vector variable to be defined in your ansible variables
$ ansible localhost -m metalstack.base.metal_stack_release_vector
- Installing ansible-common (v0.6.13) to /root/.ansible/roles/ansible-common
- Installing metal-ansible-modules (v0.2.10) to /root/.ansible/roles/metal-ansible-modules
- Installing metal-roles (v0.15.17) to /root/.ansible/roles/metal-roles
```

After that, just as if `ansible-galaxy` was used, the roles referenced in the release vector are installed in `~/.ansible/roles`.
