#!/usr/bin/python
# -*- coding: utf-8 -*-

import tarfile
import os

from io import BytesIO
from yaml import safe_load
from pathlib import Path
from urllib.parse import urlparse

from ansible.plugins.action import ActionBase
from ansible.module_utils._text import to_native
from ansible import constants as C


HAS_OPENCONTAINERS = True
try:
    from opencontainers.distribution.reggie import NewClient, WithReference, WithDigest, WithDefaultName, WithUsernamePassword # type: ignore[import]
    import opencontainers.image.v1 as opencontainersv1 # type: ignore[import]
except ImportError as ex:
    HAS_OPENCONTAINERS = False


try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()


RELEASE_VECTOR_MEDIA_TYPE = "application/vnd.metal-stack.release-vector.v1.tar+gzip"
ANSIBLE_ROLE_MEDIA_TYPE = "application/vnd.metal-stack.ansible-role.v1.tar+gzip"


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        super(ActionModule, self).run(tmp, task_vars)
        module_args = self._task.args.copy()
        self.task_vars = task_vars
        result = dict()

        if not HAS_OPENCONTAINERS:
            result["failed"] = True
            result["msg"] = "this plugin requires opencontainers"
            return result

        full_ref                       = module_args.get("ref", task_vars.get("metal_stack_release_vector"))
        self._release_vector_file_name = module_args.get("file_name", "release.yaml")
        self._registry_username        = module_args.get("username", task_vars.get("metal_stack_release_vector_registry_username"))
        self._registry_password        = module_args.get("password", task_vars.get("metal_stack_release_vector_registry_password"))
        self._recurse                  = module_args.get("recurse", task_vars.get("metal_stack_release_vector_recurse", True))
        self.registry_scheme           = module_args.get("registry_scheme", "https")
        install_roles                  = module_args.get("install_ansible_roles", True)

        if not full_ref:
            result["failed"] = True
            result["msg"] = "either release vector parameter must be given or metal_stack_release_vector must be defined in the variables"
            return result

        registry, registry_namespace, version = _parse_oci_ref(full_ref, scheme=self.registry_scheme)

        if not version:
            result["failed"] = True
            result["msg"] = "release vector reference must contain a specific version"
            return result

        try:
            release_vectors = self._download_release_vectors(registry, registry_namespace, version)

            if install_roles:
                for vector in release_vectors:
                    self._install_ansible_roles(vector.get("ansible-roles", []))

        except Exception as e:
            result["failed"] = True
            result["msg"] = str(to_native(e))
            return result

        if release_vectors:
            result["content"] = release_vectors[0]

        return result


    def _download_release_vectors(self, registry, namespace, version, vectors=[]):
        display.display("- Resolving release vector %s:%s" % (namespace, version), color=C.COLOR_CHANGED)

        blob = self._download_blob(
            registry,
            namespace,
            version,
            RELEASE_VECTOR_MEDIA_TYPE,
        )

        release_vector = safe_load(_extract_tar_gzip_file(blob.content, self._release_vector_file_name))

        vectors.append(release_vector)

        if self._recurse:
            for vector_name, subvector in release_vector.get("vectors", {}).items():
                ref = subvector.get("oci")

                # FIXME: just for demonstration purposes
                if vector_name == "metal-stack":
                    ref = "ghcr.io/metal-stack/releases:develop"

                if not ref:
                    display.display("- Nested release vector %s has no oci ref, skipping" % (vector_name), color=C.COLOR_SKIP)
                    continue

                registry, registry_namespace, version = _parse_oci_ref(ref, scheme=self.registry_scheme)

                vectors = self._download_release_vectors(registry, registry_namespace, version, vectors)

        return vectors


    def _install_ansible_roles(self, roles):
        base_path = str(Path.home()) + "/.ansible/roles"

        for role_name, v in roles.items():
            role_path = base_path + "/" + role_name
            role_version = v.get("version")
            role_ref = v.get("oci")
            role_repository = v.get("repository")

            # FIXME: just for demonstration purposes
            if role_name == "metal-roles":
                role_ref = "ghcr.io/metal-stack/metal-roles:oci-artifacts"
            if role_name == "metal-extensions-roles":
                role_ref = "r.metal-stack.io/extensions/metal-extensions-roles:oci-artifacts"

            if not role_version:
                raise Exception("no version specified for role " + role_name)

            if not role_ref and not role_repository:
                display.display("- %s has no oci ref nor repository defined, skipping" % (role_name), color=C.COLOR_SKIP)
                continue

            if os.path.isdir(role_path):
                display.display("- %s already installed in %s, skipping" % (role_name, role_path), color=C.COLOR_SKIP)
                continue

            display.display("- Installing %s (%s) to %s" % (role_name, role_version, role_path), color=C.COLOR_CHANGED)

            if role_ref:
                registry, registry_namespace, version = _parse_oci_ref(role_ref, scheme=self.registry_scheme)

                blob = self._download_blob(
                    registry,
                    registry_namespace,
                    version,
                    ANSIBLE_ROLE_MEDIA_TYPE,
                )

                _extract_tar_gzip(blob.content, base_path)

            else:
                try:
                    self._execute_module(module_name='ansible.builtin.git', module_args={
                        'repo': role_repository,
                        'dest': role_path,
                    }, task_vars=self.task_vars, tmp=None)
                except Exception as e:
                    raise Exception("error cloning git repository: %s" % to_native(e))


    def _download_blob(self, address, default_name, reference, layer_media_type):
        # TODO: optional verify signature of the oci artifact with cosign

        opts = [WithDefaultName(default_name)]
        if self._registry_username and self._registry_password:
            opts.append(WithUsernamePassword(username=self._registry_username, password=self._registry_password))

        client = NewClient(address,
            *opts
        )

        req = client.NewRequest(
            "GET",
            "/v2/<name>/manifests/<reference>",
            WithReference(reference),
        ).SetHeader("Accept", opencontainersv1.MediaTypeImageManifest)

        try:
            response = client.Do(req)
            response.raise_for_status()
        except Exception as e:
            raise Exception("the download of the release vector raised an error: %s" % to_native(e))

        manifest = response.json()

        for layer in manifest["layers"]:
            if layer["mediaType"] == layer_media_type:
                target = layer
                break

        if not target:
            raise Exception("no layer with media type %s found in oci release vector" % layer_media_type)

        req = client.NewRequest(
            "GET",
            "/v2/<name>/blobs/<digest>",
            WithDigest(target['digest']),
        )

        req.stream = True

        try:
            blob = client.Do(req)
            blob.raise_for_status()
        except Exception as e:
            raise Exception("the download of the release vector layer raised an error: %s" % to_native(e))

        return blob


def _parse_oci_ref(full_ref, scheme='https'):
    ref, *tag = full_ref.split(":", 1)
    tag = tag[0] if tag else None
    url = urlparse("%s://%s" % (scheme, ref))
    return "%s://%s" % (scheme, url.netloc), url.path.removeprefix('/'), tag


def _extract_tar_gzip_file(bytes, member):
    with tarfile.open(fileobj=BytesIO(bytes), mode='r:gz') as tar:
        with tar.extractfile(tar.getmember(member)) as f:
            try:
                return f.read().decode('utf-8')
            except Exception as e:
                raise Exception("error extracting tar member from oci layer: %s" % to_native(e))


def _extract_tar_gzip(bytes, dest):
    with tarfile.open(fileobj=BytesIO(bytes), mode='r:gz') as tar:
        try:
            tar.extractall(dest, tar.getmembers())
        except Exception as e:
            raise Exception("error extracting tar from oci layer: %s" % to_native(e))
