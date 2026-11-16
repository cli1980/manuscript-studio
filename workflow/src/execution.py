"""Startup-only execution configuration. Public descriptions never contain credentials."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

from .harnesses import resolve_harness

PROFILE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["name", "harness", "models", "default_model"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "harness": {"type": "string", "minLength": 1},
        "command": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
        "timeout": {"type": "number", "exclusiveMinimum": 0},
        "trusted_local_execution": {"type": "boolean"},
        "default_model": {"type": "string", "minLength": 1},
        "endpoints": {
            "type": "object", "additionalProperties": {
                "type": "object", "additionalProperties": False,
                "required": ["base_url", "api", "api_key_env"],
                "properties": {
                    "base_url": {"type": "string"},
                    "api": {"enum": ["openai-completions", "openai-responses", "anthropic-messages"]},
                    "api_key_env": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
                },
            },
        },
        "models": {
            "type": "array", "minItems": 1, "items": {
                "type": "object", "additionalProperties": False, "required": ["key", "model"],
                "properties": {
                    "key": {"type": "string", "minLength": 1},
                    "model": {"type": "string", "minLength": 1},
                    "endpoint": {"type": "string", "minLength": 1},
                    "workflows": {"type": "array", "minItems": 1,
                                  "items": {"type": "string", "minLength": 1}},
                },
            },
        },
    },
}

USER_PROFILE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {key: PROFILE_SCHEMA["properties"][key]
                   for key in ("endpoints", "models", "default_model")},
}


def validate(data, schema, label):
    error = next(Draft202012Validator(schema).iter_errors(data), None)
    if error:
        raise ValueError(f"Invalid {label} at {'/'.join(map(str, error.path)) or 'root'} "
                         f"({error.validator}).")


def unique_objects(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object keys are not permitted in execution profiles.")
        result[key] = value
    return result


def read_profile(path, label):
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_objects)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {label} JSON at line {exc.lineno}, column {exc.colno}.") from None


def models_by_key(models):
    result = {model["key"]: model for model in models}
    if len(result) != len(models):
        raise ValueError("Execution model keys must be unique within each profile.")
    return result


@dataclass(frozen=True)
class Model:
    key: str
    model: str
    endpoint: str | None
    workflows: tuple[str, ...]


class ExecutionProfile:
    """Snapshot the file and its credential values once, never reload during execution."""

    def __init__(self, data, *, directory=None):
        validate(data, PROFILE_SCHEMA, "execution profile")
        data = copy.deepcopy(data)
        self.name, self.harness = data["name"], data["harness"]
        self._adapter = resolve_harness(self.harness)
        self._adapter.validate(data)
        self.revision = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        self.timeout = data.get("timeout", 900)
        self.default_model = data["default_model"]
        self.models = tuple(Model(m["key"], m["model"], m.get("endpoint"), tuple(m.get("workflows", ())))
                            for m in data["models"])
        if len({m.key for m in self.models}) != len(self.models):
            raise ValueError("Execution model keys must be unique.")
        self._endpoints = data.get("endpoints", {})
        self._secrets = {}
        for name, endpoint in self._endpoints.items():
            if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
                raise ValueError("Endpoint names must be lowercase identifiers.")
            url = urlsplit(endpoint["base_url"])
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("Endpoint base URLs must use HTTPS without credentials, queries, or fragments.")
            self._secrets[name] = os.environ.get(endpoint["api_key_env"], "")
        self.select(None)
        command = data.get("command", self._adapter.default_command)
        base = Path(directory or Path.cwd())
        self.command = tuple(str((base / part).resolve()) if part.startswith(".") else part for part in command)

    @classmethod
    def load(cls, path, user_path=None):
        if path is None:
            if user_path is not None:
                raise ValueError("--user-execution-profile requires --execution-profile.")
            return None
        path = Path(path).expanduser().resolve()
        data = read_profile(path, "project execution profile")
        if user_path is not None:
            validate(data, {**PROFILE_SCHEMA, "required": ["name", "harness"]}, "project execution profile")
            user = read_profile(Path(user_path).expanduser().resolve(), "user execution profile")
            validate(user, USER_PROFILE_SCHEMA, "user execution profile")
            models = models_by_key(data.get("models", []))
            models.update(models_by_key(user.get("models", [])))
            # Replace complete named entries; never inherit an old endpoint's credential reference.
            data["models"] = list(models.values())
            if user.get("endpoints"):
                data["endpoints"] = {**data.get("endpoints", {}), **user["endpoints"]}
            if "default_model" in user:
                data["default_model"] = user["default_model"]
        return cls(data, directory=path.parent)

    def select(self, key, workflow=None):
        key = key or self.default_model
        model = next((m for m in self.models if m.key == key), None)
        if model is None:
            raise ValueError("The selected model is unavailable in the startup profile; no fallback was applied.")
        if workflow and model.workflows and workflow not in model.workflows:
            raise ValueError(f"Model {model.key} is not enabled for workflow {workflow}.")
        return model

    def describe(self, key=None):
        model = self.select(key)
        endpoint = self._endpoints.get(model.endpoint, {})
        return {"profile": self.name, "revision": self.revision, "harness": self.harness,
                "model_key": model.key, "model": model.model, "endpoint": model.endpoint,
                "base_url": endpoint.get("base_url"), "api": endpoint.get("api"),
                "sandbox": self._adapter.sandbox}

    def public(self):
        return {"name": self.name, "revision": self.revision, "harness": self.harness,
                "default_model": self.default_model,
                "models": [{**self.describe(m.key), "workflows": list(m.workflows)} for m in self.models]}

    def runtime(self):
        return ProfileRuntime(self)

    def create_adapter(self, model):
        return self._adapter.factory(self, model)

    def redact(self, value):
        if isinstance(value, str):
            for secret in self._secrets.values():
                if secret:
                    value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, dict):
            return {k: self.redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        return value


class ProfileRuntime:
    def __init__(self, profile):
        self.profile = profile

    def describe(self, model, workflow=None):
        self.profile.select(model, workflow)
        return self.profile.describe(model)

    def run(self, request, on_event, on_thread):
        profile = self.profile
        model = profile.select(request.model)
        try:
            runtime = profile.create_adapter(model)
            return profile.redact(runtime.run(
                replace(request, model=model.model),
                lambda kind, payload: on_event(kind, profile.redact(payload)), on_thread))
        except (Exception, KeyboardInterrupt) as exc:
            if isinstance(exc, KeyboardInterrupt):
                raise
            raise RuntimeError(profile.redact(str(exc))) from None
