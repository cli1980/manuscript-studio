"""Historic composed-run fixtures, not the production Work-version entry point."""

import contextlib
import copy
import json
from pathlib import Path

from workflow.src import registry


@contextlib.contextmanager
def inline_intake_templates(directory):
    """Keep existing intake/run-engine regressions distinct from Work lifecycle tests."""
    previous = dict(registry._registered)
    preparation = registry.get("work-preparation-v1")
    try:
        for template_id in ("literary-editing-v1", "literary-translation-v1"):
            template = copy.deepcopy(registry.get(template_id))
            template["prepared_input"] = False
            template["agents"].update(copy.deepcopy(preparation["agents"]))
            stages = copy.deepcopy(preparation["stages"][:3])
            stages[0]["owns"] = ["prepared/", "source/", "manuscript/", "editorial/"]
            template["stages"] = stages + template["stages"]
            path = Path(directory) / "inline-intake-fixtures" / template_id / "template.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(template), encoding="utf-8", newline="\n")
            registry.register(path)
        yield
    finally:
        registry._registered.clear()
        registry._registered.update(previous)
