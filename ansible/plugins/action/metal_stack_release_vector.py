#!/usr/bin/python
# -*- coding: utf-8 -*-

import tarfile
import tempfile
import json

from os import path
from io import BytesIO
from pathlib import Path
from yaml import safe_load
from urllib.parse import urlparse
from traceback import format_exc

from ansible.module_utils.urls import open_url
from ansible.plugins.action import ActionBase
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.module_utils._text import to_native
from ansible.playbook.role import Role
from ansible.playbook.role.include import RoleInclude
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


class ActionModule(ActionBase):
    CACHE_FILE = "metal-stack-release-vector-cache.json"

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        super(ActionModule, self).run(tmp, task_vars)
        result = dict()

        self._supports_check_mode = True

        vectors = self._task.args.get('vectors', task_vars.get('metal_stack_release_vector'))
        cache_enabled = boolean(self._task.args.get('cache', task_vars.get('metal_stack_release_vector_cache', True)), strict=False)
        install_roles = boolean(self._task.args.get('install_roles', task_vars.get('metal_stack_release_vector_install_roles', True)), strict=False)

        if not vectors:
            result["skipped"] = True
            return result

        if cache_enabled and path.isfile(self._cache_file_path()):
            result["changed"] = False
            result["ansible_facts"] = json.safe_load(self._cache_file_path())
            return result

        if not isinstance(vectors, list):
            result["failed"] = True
            result["msg"] = "vectors must be a list"
            return result

        result["changed"] = False
        ansible_facts = {}

        for vector in vectors:
            args = task_vars | vector

            resolver = RemoteResolver(module=self, args=args)

            kwargs = dict(
                install_roles=install_roles,
            )
            if vector.get("oci_registry_username"):
                kwargs["oci_registry_username"] = vector.get("oci_registry_username")
            if vector.get("oci_registry_password"):
                kwargs["oci_registry_password"] = vector.get("oci_registry_password")
            if vector.get("oci_registry_scheme"):
                kwargs["oci_registry_scheme"] = vector.get("oci_registry_scheme")

            try:
                data = resolver.resolve(**kwargs)
            except Exception as e:
                result["failed"] = True
                result["msg"] = "error resolving yaml"
                result["error"] = to_native(e)
                result["traceback"] = format_exc()
                return result

            for k, v in data.items():
                if task_vars.get(k) is not None or ansible_facts.get(k) is not None:
                    # skip when already defined
                    continue

                ansible_facts[k] = v

        result["ansible_facts"] = ansible_facts
        if cache_enabled:
            with open(self._cache_file_path(), 'rw') as vector:
                vector.write(json.dumps(ansible_facts))

        return result

    @staticmethod
    def _cache_file_path():
        return path.join(tempfile.gettempdir(), ActionModule.CACHE_FILE)


class RemoteResolver():
    def __init__(self, module, args):
        self._module = module

        _args = args.copy()

        for _, defaults in _args.get("_cached_role_defaults", dict()).items():
            _args = _args | defaults

        self._cached_role_defaults = dict()

        if 'from_role_defaults' in _args:
            if not isinstance(_args["from_role_defaults"], list):
                raise Exception("role defaults must be provided as a list")

            for role_name in _args["from_role_defaults"]:
                if role_name in self._cached_role_defaults:
                    continue

                res = self.load_role_default_vars(module=module, role_name=role_name)
                self._cached_role_defaults[role_name] = res
                _args = _args | res

        meta_var = module._templar.template(_args.pop("meta_var", None))

        if meta_var:
            meta_args = _args.get(meta_var)
            if not meta_args:
                raise Exception("""the meta variable with name "%s" is not defined, please provide it through inventory, role defaults or module args""" % meta_var)

            _args = _args | meta_args

        self._url = module._templar.template(_args.pop("url", None))
        if not self._url:
            raise Exception("url is required")

        self._mapping = _args.pop("mapping", None)
        if not self._mapping:
            raise Exception("mapping is required for %s" % self._url)

        self._nested = _args.pop("nested", list()) if _args.pop("recursive", True) else list()
        self._replacements = _args.pop("replace", list())

        self._args = _args


    @staticmethod
    def resolve(url, module, args, **kwargs):
        loader = ContentLoader(url, **kwargs)

        content = loader.load()

        # setup the ansible-roles
        if kwargs.get('install_roles', True):
            for role_name, spec in content.get("ansible-roles", {}).items():
                role_path = path.join(str(Path.home()), "/.ansible/roles", role_name)

                # TODO: check for overwrites
                role_version = spec.get("version")
                role_ref = spec.get("oci")
                role_repository = spec.get("repository")

                if not role_version:
                    raise Exception("no version specified for role " + role_name)

                if not role_ref and not role_repository:
                    display.display("- %s has no oci ref nor repository defined, skipping" % (role_name), color=C.COLOR_SKIP)
                    continue

                if path.isdir(role_path):
                    display.display("- %s already installed in %s, skipping" % (role_name, role_path), color=C.COLOR_SKIP)
                    continue

                display.display("- Installing %s (%s) to %s" % (role_name, role_version, role_path), color=C.COLOR_CHANGED)

                if role_ref:
                    ContentLoader(url, tar_dest=role_path, **kwargs).install_ansible_role(role_name=role_name, spec=spec)
                else:
                    try:
                        module._execute_module(module_name='ansible.builtin.git', module_args={
                            'repo': role_repository,
                            'dest': role_path,
                        }, task_vars=module.task_vars, tmp=None)
                    except Exception as e:
                        raise Exception("error cloning git repository: %s" % to_native(e))

        resolver = RemoteResolver(module=module, args=args)

        # apply potential replacements
        for r in resolver._replacements:
            if r.get("key") is None or r.get("old") is None or r.get("new") is None:
                raise Exception("replace must contain and dict with the keys for 'key', 'old' and 'new'")
            resolver.replace_key_value(content, r.get("key"), r.get("old"), r.get("new"))

        result = dict()

        # map to variables
        for k, path in resolver._mapping.items():
            try:
                value = resolver.dotted_path(content, path)
            except KeyError as e:
                display.warning(
                    """mapping path %s does not exist in %s: %s""" % (
                        path, resolver._url, to_native(e)))
                continue

            result[k] = value

        # resolve nested vectors
        for n in resolver._nested:
            path = n.pop("url_path", None)
            if not path:
                raise Exception("nested entries must contain an url_path")

            try:
                url = resolver.dotted_path(content, path)
            except KeyError as e:
                raise Exception("""url_path "%s" could not resolved in %s""" % (path, resolver._url))

            args = resolver._args.copy()
            args["meta_var"] = n.pop("meta_var", None)
            args["mapping"] = n.pop("mapping", None)
            args["nested"] = n.pop("nested", list())
            args["recursive"] = n.pop("recursive", True)
            args["replace"] = n.pop("replace", list()) + resolver._replacements
            args["_cached_role_defaults"] = resolver._cached_role_defaults

            results = RemoteResolver.resolve(url=url, module=module, args=args)

            for k, v in results.items():
                if result.get(k) is not None:
                    # nested values do not overwrite the parent values
                    continue

                result[k] = v

        return result


    @staticmethod
    def load_role_default_vars(module, role_name):
        i = RoleInclude.load(role_name, play=module._task.get_play(),
                             current_role_path=module._task.get_path(),
                             variable_manager=module._task.get_variable_manager(),
                             loader=module._task.get_loader(), collection_list=None)

        return Role().load(role_include=i, play=module._task.get_play()).get_default_vars()


    @staticmethod
    def dotted_path(vector, path):
        value = vector
        for p in path.split("."):
            value = value[p]
        return value


    @staticmethod
    def replace_key_value(data, key, old, new):
        if not isinstance(data, dict):
            return

        if key in data:
            to_replace = data[key]
            if isinstance(to_replace, str):
                data[key] = to_replace.replace(old, new)

        for _, v in data.items():
            if isinstance(v, dict):
                RemoteResolver.replace_key_value(v, key, old, new)


class ContentLoader():
    def __init__(self, url, **kwargs):
        if url.startswith(OciLoader.OCI_PREFIX):
            self._loader = OciLoader(url, **kwargs)
        else:
            self._loader = UrlLoader(url)

    def load(self) -> dict:
        display.v("loading remote content from %s" % self._loader._url)
        raw = self._loader.load()
        return safe_load(raw)


class UrlLoader():
    def __init__(self, url, **_):
        self._url = url

    def load(self):
        return open_url(self._url).read()


class OciLoader():
    OCI_PREFIX = "oci://"
    RELEASE_VECTOR_MEDIA_TYPE = "application/vnd.metal-stack.release-vector.v1.tar+gzip"
    ANSIBLE_ROLE_MEDIA_TYPE = "application/vnd.metal-stack.ansible-role.v1.tar+gzip"

    def __init__(self, url, **kwargs):
        self._url = url[len(OciLoader.OCI_PREFIX):]
        self._member = kwargs.get("tar_member_file_name", "release.yaml")
        self._dest = kwargs.get("tar_dest", None)
        self._registry, self._namespace, self._version = self._parse_oci_ref(self._url, scheme=kwargs.get("oci_registry_scheme", "https"))
        self._username = kwargs.get("oci_registry_username")
        self._password = kwargs.get("oci_registry_password")

    def load(self):
        if not HAS_OPENCONTAINERS:
            raise ImportError("opencontainers must be installed in order to resolve metal-stack oci release vectors")

        blob, media_type = self._download_blob()

        if media_type == self.ANSIBLE_ROLE_MEDIA_TYPE:
            if not self._dest:
                raise Exception("tar destination must be specified")
            return self._extract_tar_gzip(blob, dest=self._dest)
        else:
            return self._extract_tar_gzip_file(blob, member=self._member)

    def _download_blob(self):
        opts = [WithDefaultName(self._namespace)]
        if self._username and self._password:
            opts.append(WithUsernamePassword(username=self._username, password=self._password))

        client = NewClient(self._registry,
            *opts
        )

        req = client.NewRequest(
            "GET",
            "/v2/<name>/manifests/<reference>",
            WithReference(self._version),
        ).SetHeader("Accept", opencontainersv1.MediaTypeImageManifest)

        try:
            response = client.Do(req)
            response.raise_for_status()
        except Exception as e:
            raise Exception("the download of the release vector raised an error: %s" % to_native(e))

        manifest = response.json()

        target = None
        for layer in manifest["layers"]:
            if layer["mediaType"] == self.RELEASE_VECTOR_MEDIA_TYPE or layer["mediaType"] == self.ANSIBLE_ROLE_MEDIA_TYPE:
                target = layer
                break

        if not target:
            raise Exception("no layer with media type %s or %s found in oci release vector" % (self.RELEASE_VECTOR_MEDIA_TYPE, self.ANSIBLE_ROLE_MEDIA_TYPE))

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

        return blob.content, layer["mediaType"]


    @staticmethod
    def _parse_oci_ref(full_ref, scheme='https'):
        ref, *tag = full_ref.split(":", 1)
        tag = tag[0] if tag else None
        if tag is None:
            raise Exception("oci ref %s needs to specify a tag" % full_ref)
        url = urlparse("%s://%s" % (scheme, ref))
        return "%s://%s" % (scheme, url.netloc), url.path.removeprefix('/'), tag


    @staticmethod
    def _extract_tar_gzip_file(bytes, member):
        with tarfile.open(fileobj=BytesIO(bytes), mode='r:gz') as tar:
            with tar.extractfile(tar.getmember(member)) as f:
                try:
                    return f.read().decode('utf-8')
                except Exception as e:
                    raise Exception("error extracting tar member from oci layer: %s" % to_native(e))


    @staticmethod
    def _extract_tar_gzip(bytes, dest):
        with tarfile.open(fileobj=BytesIO(bytes), mode='r:gz') as tar:
            try:
                tar.extractall(dest, tar.getmembers())
            except Exception as e:
                raise Exception("error extracting tar from oci layer: %s" % to_native(e))
