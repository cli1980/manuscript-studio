# Formattor placement: workflow package or standalone tool

**Date:** 2026-11-15

**Status:** comparison requested by IDP-C22; standalone tool location, Python API
and CLI approved by IDP-C23. This supersedes the initial `workflow/src/formattor`
location in IDP-R19/C21. The three-part design and default DOCX implementation
remain unchanged. Documentation is relocated; executable packaging and
generation are not implemented.

Related:
[component design](formattor-package-design.md),
[production gaps](proposal-to-docx-gap-analysis.md), and
[requirements/decisions](interior-design-and-production.md).

## 1. Recommendation

The selected design is an independently installable **library plus CLI** under
`tools/formattor/`, with workflow as one consumer.
Keep both entry points over the same intake, engine and implementations.

This does not require a separate Git repository, a service, dynamic plugins, or
a second generator. It does require proper packaging, public contracts, explicit
version/build identity and a clean dependency direction.

An internal `workflow/src/formattor` package is reasonable if formatting is
expected to remain exclusively a Studio/workflow feature. It can still be
well-factored and exposed through a CLI, but an independent distribution boundary
is less natural. A directory name alone proves neither independence nor reuse.

## 2. Evidence from the current repository

- At comparison time there was no root `tools/` project or tracked
  `pyproject.toml` establishing a standalone formatter convention. The tool's
  documentation home now exists, but executable packaging remains new work.
- [Workflow requirements](../../../workflow/requirements.txt) reference preparation
  skill requirements. [DOCX requirements](../../../workflow/requirements-docx.txt)
  include workflow requirements before adding document/rendering dependencies.
  Copying that dependency chain into a tool would not make it independent.
- [The existing adapters](../../../workflow/src/document_adapters.py) import workflow
  storage hashing and derive a repository root. Word rendering invokes
  `python -m workflow.src.document_adapters` with that repository as its working
  directory. These paths must change for a clean installed tool.
- [The registry](../../../workflow/src/registry.py), `_source_hash`, hashes every Python
  file below `workflow/src`. A formatter located there joins the parent workflow
  engine identity; changes can make existing runs outdated even without changing
  their literary work.
- An external tool is not automatically covered by that source hash. Its
  implementation/resources must instead be explicitly bound to production jobs,
  including editable-development changes where a version string may not change.
- Proposal/preparation identity is already expressed in portable files/hashes.
  Intake does not fundamentally need a workflow run database or Studio.

The current code location and imports need migration, not just a folder move.

## 3. Comparison

| Criterion | Inside `workflow/src/formattor` | Standalone project under `tools/formattor` |
| --- | --- | --- |
| Initial integration | Simpler imports and one existing environment | Packaging, installation and adapter work required |
| Standalone use | Possible, but users tend to acquire the workflow namespace/source tree | Direct install and CLI/API use without workflow or Studio |
| Ownership | Naturally treated as part of workflow internals | Formatting is a domain tool; workflow is a client |
| Dependencies | Easier to accidentally import storage, runtime or skill helpers | Independent dependency declaration makes coupling visible |
| Version/build identity | Formatter changes enter the current broad workflow hash | Explicit tool/contract/resource identity required; can evolve separately |
| Native environments | Usually shares the application environment | Can share it through an API or use an isolated CLI environment |
| Future InDesign | Supported by a good protocol, regardless of location | Clearer native-tool/dependency boundary, but no automatic InDesign capability |
| Testing | Easy to rely on workflow fixtures/state | Clean-install and no-workflow tests establish genuine independence |
| Resource distribution | Repository-relative paths are tempting | Schemas/profiles must work as installed package resources |
| Maintenance cost | Lower packaging cost initially; extraction cost later | More setup now; public contracts and version coordination remain ongoing work |

Both locations can preserve implementation independence. The stronger argument
for the external tool is its intended consumers and lifecycle, not an assumption
that DOCX or InDesign technically requires a top-level tools directory.

## 4. Proposed standalone shape

```text
tools/formattor/
    pyproject.toml
    src/formattor/
        __init__.py          public library API
        cli.py               thin CLI over that API
        contracts.py         shared versioned data/protocols
        intake.py            proposal/source validation and normalization
        engine.py            implementation-independent preparation/production
        resources/           canonical schemas/profiles/policies
        implementations/
            docx/            default native implementation and render strategies
    tests/

workflow/src/
    interior.py              host coordination and human-gate adapter
    ...                      imports the installed public tool API
```

The module and CLI names are illustrative; retain `formattor` unless the owner
chooses a different name. The independent project can stay in this repository
and CI. Do not split its three internal parts into separately released projects.

An installed client imports `formattor`, not `tools.formattor` or
`workflow.src.formattor`. Development can use an editable install; do not rely
on modifying `sys.path`, running from the repository root, or manually copying
source into another environment.

Canonical resources and executable validation belong to the tool. Skills can
consume its public validation/resource interface and versioned authoring
exports; they must not maintain another formatter or editable duplicate schema.

## 5. Library API versus invoking a subprocess

Use the same domain API and data contracts through both entry points.
Suggested CLI operations are validate, prepare and build; these names do not
describe implemented commands.

| Integration | Benefit | Cost / appropriate use |
| --- | --- | --- |
| Python API in the workflow environment | Typed results/errors, direct cancellation/progress, no stdout protocol overhead | Runtime dependencies share the process; recommended initial adapter if environments are compatible |
| CLI subprocess in a selected tool environment | Process/dependency isolation and bounded execution | Needs explicit executable identity, versioned machine-readable I/O, cancellation/cleanup and structured errors; useful when native environments differ |
| Separate service | Remote or centrally managed execution | Authentication, deployment, storage and distributed-job complexity; not justified just to achieve standalone use |

Do not make workflow parse human log output. A CLI transport should separate
structured results from diagnostics/progress, use meaningful failure statuses,
and validate request/response contract versions. Both transports call the same
implementation; no second normalization or generation path.

The default DOCX backend remains separate from Word/LibreOffice rendering.
An eventual InDesign backend can use its own runtime/export path without
requiring the common engine or workflow to imitate its native object model.

## 6. What standalone must mean

### Portable inputs and explicit outputs

The tool accepts a bound proposal, verified preparation/metadata/assets, selected
profile/target, implementation/environment and policy. It produces prepared-plan
data, diagnostics, candidate documents and manifests in an explicitly owned job
directory. It must not need a Studio work index, workflow run ID, Codex/Pi
runtime, workflow skill snapshot or parent publication library.

Preparation verification is a real remaining dependency: the standalone CLI
needs the authoritative verifier through an installable/shared contract
boundary. A workflow-only callback is insufficient for independent use.
Do not solve this by copying a partial validator and calling its result ready.

### Standalone authorization is not a workflow receipt

The tool cannot require a Studio-specific approval record to function.
Recommended distinction:

- `validate`/`prepare` do not authorize generation or modify the manuscript.
- Standalone construction requires explicit caller authorization of the exact
  resolved plan. A CLI can record that command authorization without claiming
  the user read every value or reviewed any pages.
- The workflow adapter continues to require its own current human-gate receipt
  for the same prepared identity; the tool must not fabricate that receipt.
- Generated files are identifiable candidates, not automatic workflow
  publication, human page approval or print certification.

The CLI is another host of the same engine, not a new literary-editing workflow.
It can return files/reports for manual review without implementing another GUI.
Studio's embedded path still owns its page-review/finalization policy. A future
standalone approval/publication interface would be separate scope.

### No workflow dependency in the tool

The dependency direction is:

```text
Studio / workflow ----+
Standalone CLI -------+--> public formattor API --> intake / engine
Skill validation -----+                              --> implementations
```

The reverse import is prohibited. The tool must own/reuse neutral utilities
without importing `workflow.src.storage`, resolving the repository root, or
executing a module in the workflow namespace.

This is compatible with keeping formatting embedded in Studio's editing/
translation workflows. A standalone generator executable does not require
restoring the retired public formatting-workflow template.

## 7. Additional work and risks of external placement

1. **Packaging and dependency ownership.** Declare tool dependencies once;
   workflow installs a compatible tool distribution rather than duplicating its
   library list. Keep native backends optional where practical. Installing a
   Python package does not install Word/InDesign, licenses or usable fonts.
2. **Identity and drift.** Record tool build identity, contract/resources,
   implementation/native tools/fonts and QA policy with the effective spec.
   A package version alone is insufficient in editable development. Removing
   code from the workflow hash must not make production changes invisible.
3. **Compatibility policy.** Version contracts and reject incompatible inputs
   clearly. Before the first release, prefer coordinated clean changes rather
   than maintaining duplicate old APIs/validators.
4. **Cross-process native resource ownership.** Standalone and workflow calls
   must honor the same application-resource locking and cleanup rules.
   Workflow's in-process queue alone cannot serialize a separate terminal.
   Cancellation must not terminate an unrelated user application.
5. **Installed resources and subprocesses.** Resolve package data independently
   of the working directory. Native worker subprocesses use the selected tool
   installation/environment, not a hard-coded repository module path.
6. **Manifests and safe filesystem access.** Use portable, versioned job/artifact
   contracts and job-relative outputs. Preserve input bytes, reject unapproved
   external resources, and do not overwrite existing user data by default.

External placement addresses coupling, not the underlying source mapping,
style semantics, missing DOCX features or final-output checks in the gap
assessment. Those remain work inside the same three-part architecture.

## 8. Suggested acceptance and migration

Before calling the tool standalone, demonstrate:

- An installed distribution validates/prepares inputs from outside this checkout,
  with no workflow/Studio/agent package on the import path.
- Schemas, both IngramSpark variants, verification adapters and example data are
  available through the installed distribution, not repository-relative paths.
- API and CLI use the same normalized semantics and failure diagnostics.
- Workflow and CLI builds record the same effective inputs/implementation facts;
  do not demand byte-identical ZIP/PDF files across runs or different renderers.
- Actual native DOCX/rendering tests run where their required environment exists;
  core/fake-backend tests remain independent of those installations.
- Tool/environment drift, stale plans and cross-process resource contention are
  detected rather than silently reusing an old candidate/approval.

Recommended migration for the selected standalone option:

1. Establish the public contracts/package boundary and independent preparation
   verification/distribution path.
2. Move canonical intake/resources and reusable formatting primitives once;
   change clients to the installed API, without permanent compatibility copies.
3. Add the thin CLI and tool-owned native worker entry points.
4. Connect the workflow adapter to its existing queue, receipts and page review.
5. Complete the previously identified DOCX/QA capabilities; do not treat
   extraction or packaging as completed formatting functionality.

## 9. Decision status

**Approved location and exposure:** standalone installable library plus CLI under
`tools/formattor/`, with a thin workflow adapter.

**Not yet decided:** the final distribution/command names, exact initial
deliverables, and any InDesign
deployment or functionality.

IDP-C22 requested this evaluation; IDP-C23 resolves IDP-D09. Related design/gap
documents now live under `tools/formattor/docs`. No executable Python package,
CLI, dependency installation or application behavior is implemented by this
documentation change.
