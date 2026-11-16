"""Resolve bundled vendor data by binding; no network or production certification."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PROFILE = Path(__file__).resolve().parents[1] / "profiles/ingramspark.json"


def sha256(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def catalog():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    return [{"id": profile["id"], "name": profile["name"], "version": profile["version"],
             "variants": [{"id": key, "name": value["name"], "binding": value["binding"],
                           "profile": resolve(profile["id"], value["binding"])}
                          for key, value in profile["variants"].items()]}]


def resolve(vendor_id, binding):
    if binding not in ("paperback", "hardcover"):
        raise ValueError("Choose paperback or hardcover.")
    if vendor_id is None:
        return None
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    if vendor_id != profile["id"]:
        raise ValueError("Unknown print-vendor profile.")
    variant = profile.pop("variants")[binding]
    data = {**profile, "variant": variant}
    return {"profile_id": profile["id"], "version": profile["version"], "variant_id": binding,
            "sha256": sha256(data), "data": data}


def validate(proposal):
    selected = proposal["vendor_profile"]
    targets = proposal["edition_brief"]["production_targets"]
    vendor_targets = [t for t in targets if t["vendor_id"] is not None]
    if selected is None:
        if vendor_targets or any(t["vendor_profile_ref"] is not None for t in targets):
            raise ValueError("Vendor targets require the selected vendor profile.")
        return
    expected = resolve(selected["profile_id"], selected["variant_id"])
    if selected != expected or sha256(selected["data"]) != selected["sha256"]:
        raise ValueError("Vendor profile data/hash differs from the bundled version.")
    if not vendor_targets:
        raise ValueError("Include the selected vendor and binding in a production target.")
    page = proposal["design_system"]["page"]
    for target in vendor_targets:
        if target["vendor_id"] != selected["profile_id"] or target["binding"] != selected["variant_id"]:
            raise ValueError("Production target differs from the selected vendor/binding.")
        if target["vendor_profile_ref"] != {"locator": "vendor_profile/data", "sha256": selected["sha256"]}:
            raise ValueError("Production target must reference the exact selected vendor profile.")
        if target["trim_mm"] != page["trim_mm"]:
            raise ValueError("Vendor target trim must match the proposed page trim.")


def design_warnings(proposal):
    selected = proposal["vendor_profile"]
    if selected is None:
        return []
    warnings = []
    page = proposal["design_system"]["page"]
    width, height = page["trim_mm"]["width"] / 25.4, page["trim_mm"]["height"] / 25.4
    ranges = selected["data"]["variant"]["custom_trim_ranges_in"]
    targets = [t for t in proposal["edition_brief"]["production_targets"] if t["vendor_id"]]
    for target in targets:
        candidates = [ranges[target["paper"]]] if target["paper"] in ranges else list(ranges.values())
        if not any(r["width"][0] - 1e-6 <= width <= r["width"][1] + 1e-6
                   and r["height"][0] - 1e-6 <= height <= r["height"][1] + 1e-6 for r in candidates):
            warnings.append("Trim is outside the reviewed custom-trim envelope for this binding/paper. "
                            "Verify an exact standard product or supported custom configuration; "
                            "these ranges are not a complete vendor product catalog.")
    margins = dict(page["margins_mm"])
    margins["inside"] += page["gutter_mm"]
    if any(value < selected["data"]["docx_guidance"]["recommended_safety_mm"] for value in margins.values()):
        warnings.append("Geometry is below the profile's 13 mm safety recommendation on at least one edge. "
                        "This is a recommendation, not an invented vendor minimum.")
    if page["bleed_mm"]:
        warnings.append("Bleed requires edge-specific PDF geometry and a supported producer. "
                        "Verify top/bottom/outside allowance and no bind-edge bleed after rendering.")
    return list(dict.fromkeys(warnings))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", choices=("paperback", "hardcover"), required=True)
    args = parser.parse_args()
    print(json.dumps(resolve("ingramspark", args.binding), indent=2))
