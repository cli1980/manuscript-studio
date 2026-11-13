"""Explicit harness registration; profiles bind a factory once at startup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .pi_runtime import PiRuntime
from .runtime import CodexRuntime


@dataclass(frozen=True)
class Harness:
    factory: Callable
    default_command: tuple[str, ...]
    sandbox: str
    uses_endpoints: bool = False
    requires_trust: bool = False

    def validate(self, data):
        if self.requires_trust and not data.get("trusted_local_execution"):
            raise ValueError("This harness has no OS sandbox. Set trusted_local_execution=true only for trusted local use.")
        for model in data["models"]:
            if self.uses_endpoints and model.get("endpoint") not in data.get("endpoints", {}):
                raise ValueError(f"Model {model['key']} requires a configured endpoint.")
            if not self.uses_endpoints and model.get("endpoint"):
                raise ValueError("This harness uses its installed provider configuration, not profile endpoints.")


def _codex(profile, model):
    return CodexRuntime(list(profile.command), profile.timeout)


def _pi(profile, model):
    endpoint = profile._endpoints[model.endpoint]
    key = profile._secrets[model.endpoint]
    if not key:
        raise ValueError(f"Missing credential environment variable: {endpoint['api_key_env']}.")
    return PiRuntime(profile.command, profile.timeout, endpoint=endpoint, model=model.model, api_key=key)


HARNESSES = {
    "codex": Harness(_codex, ("codex", "app-server"), "workspace-write"),
    "pi": Harness(_pi, ("pi",), "none (trusted local POC)", uses_endpoints=True, requires_trust=True),
}


def resolve_harness(name):
    try:
        return HARNESSES[name]
    except KeyError:
        raise ValueError("Unknown execution harness; register a supported harness before startup.") from None
