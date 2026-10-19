"use strict";
const $ = id => document.getElementById(id);
let csrf = "", skills = [], passages = [], current = null, dirty = false;
let activeJudgment = null;
let pendingWorkspace = null;
let submissionVersion = null;
let reviewer = "";
let reviewerLabelRequired = true;
const text = (id, value) => { $(id).textContent = value ?? ""; };
const show = (id, visible) => { $(id).hidden = !visible; };
const nullable = value => value.trim() || null;
const field = (form, name) => form.elements.namedItem(name);

function notice(message, error = false) {
  text("notice", message); $("notice").classList.toggle("error", error); show("notice", true);
}
function canLeave() { return !dirty || window.confirm("Discard unsaved changes?"); }
function option(value, label) { const element = document.createElement("option"); element.value = value; element.textContent = label; return element; }
function run(action) { return async event => { if (event) event.preventDefault(); try { await action(event); } catch (error) { notice(error.message, true); } }; }
async function api(path, method = "GET", data) {
  const headers = {};
  if (method !== "GET") { headers["Content-Type"] = "application/json"; headers["X-CSRF-Token"] = csrf; }
  const response = await fetch(path, {method, headers, credentials: "same-origin", body: data === undefined ? undefined : JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401) { show("workspace", false); show("logout", false); show("session-reviewer", false); show("login-panel", true); reviewer = ""; }
    const error = new Error(result.detail || "Request failed.");
    error.status = response.status;
    throw error;
  }
  if (method !== "GET" && path.startsWith("/api/") && path !== "/api/workspace/submit") await refreshWorkspace();
  return result;
}
async function refreshWorkspace() {
  pendingWorkspace = await api("/api/workspace");
  const {pending_files, cases} = pendingWorkspace;
  text("workspace-state", pending_files ? `${cases.length} case(s) have pending assessments.` : "No pending changes.");
  $("submit-changes").disabled = !pending_files;
}
function setTab(name) {
  show("cases-view", name === "cases"); show("passages-view", name === "passages");
  $("cases-tab").classList.toggle("active", name === "cases"); $("passages-tab").classList.toggle("active", name === "passages");
}
async function enter() {
  await loadLoginConfig();
  [skills, passages] = await Promise.all([api("/api/skills"), api("/api/passages")]);
  $("skill-filter").replaceChildren(...skills.map(s => option(s.id, s.label)));
  $("skill-filter").value = "literary-translation";
  populateSources();
  show("login-panel", false); show("workspace", true); show("logout", true);
  text("session-reviewer", `Signed in as ${reviewer}`); show("session-reviewer", true);
  text("reviewer-policy", "Your reviewer label is fixed for this server run across all browser sessions. Changed reviews preserve their earlier versions in history.");
  collapseCase(); setTab("cases"); await loadCases(); renderPassages(); await refreshWorkspace();
}
function populateSources() {
  const works = new Map(passages.map(p => [p.group_id, p.work?.title || p.group_id]));
  $("work-filter").replaceChildren(option("", "All works"), ...Array.from(works, ([id, label]) => option(id, label)));
  $("language-filter").replaceChildren(option("", "All languages"), ...Array.from(new Set(passages.map(p => p.source_language))).map(l => option(l, l)));
}
async function refreshPassages() { passages = await api("/api/passages"); populateSources(); renderPassages(); }
async function loadCases(selectId) {
  const skill = skills.find(s => s.id === $("skill-filter").value);
  const cases = await api(`/api/cases?skill=${encodeURIComponent(skill.id)}`);
  text("skill-note", skill.supported ? `${cases.length} case${cases.length === 1 ? "" : "s"} · Judge the supplied text through scores, comments, and issue annotations.` : "An assessment form has not been defined for this skill yet.");
  $("case-list").replaceChildren();
  for (const c of cases) {
    const status = skill.supported
      ? reviewStatus(await api(`/api/cases/${encodeURIComponent(c.case_id)}`))
      : "Review unavailable";
    const button = document.createElement("button");
    button.textContent = caseSummary(c, status);
    button.dataset.caseId = c.case_id;
    button.addEventListener("click", run(async () => { if (canLeave()) await openCase(c.case_id); }));
    button.disabled = !skill.supported;
    $("case-list").append(button);
  }
  if (!cases.length) { const empty = document.createElement("p"); empty.textContent = "No cases yet."; $("case-list").append(empty); }
  if (selectId) await openCase(selectId);
  return cases;
}
async function openCase(id) {
  current = await api(`/api/cases/${encodeURIComponent(id)}`);
  renderCase();
}
function collapseCase(message = "Select a case to compare its source and translation.") {
  current = null;
  activeJudgment = null;
  dirty = false;
  show("case-detail", false);
  show("review-conflict", false);
  text("case-empty", message);
  show("case-empty", true);
  for (const button of $("case-list").querySelectorAll("button")) button.classList.remove("selected");
}
function renderCase() {
  const c = current.metadata, p = current.source.metadata;
  dirty = false;
  show("review-conflict", false);
  show("case-empty", false); show("case-detail", true);
  for (const button of $("case-list").querySelectorAll("button")) {
    const selected = button.dataset.caseId === c.case_id;
    button.classList.toggle("selected", selected);
    if (selected) button.textContent = caseSummary(c, reviewStatus(current));
  }
  text("case-title", c.case_id);
  text("case-subtitle", `${p.work?.title || p.group_id} · source revision ${c.source_revision} · case revision ${c.revision} · ${reviewStatus(current)}`);
  text("source-heading", `Original · ${c.source_language}`); text("translation-heading", `Translation · ${c.target_language}`);
  text("source-text", current.source.text); $("source-text").lang = c.source_language;
  text("translation-text", current.translation); $("translation-text").lang = c.target_language;
  text("source-context", `Source origin: ${p.provenance?.source_origin || "Unspecified"}. Source rights: ${p.provenance?.usage_rights || "pending"}. ${p.context?.background || ""}`);
  text("case-brief", `Translation brief: ${c.context?.brief || "Not specified"}`);
  text("case-provenance", `Translation origin: ${c.provenance?.translation_origin || "Unspecified"}. Translation rights: ${c.provenance?.usage_rights || "pending"}. Case status: ${c.status}.`);
  const superseded = new Set(current.judgments.map(j => j.supersedes_judgment_id).filter(Boolean));
  activeJudgment = currentReview(current);
  loadAssessment();
  renderHistory(superseded);
}
function currentReview(caseData) {
  const metadata = caseData.metadata;
  const superseded = new Set(caseData.judgments.map(j => j.supersedes_judgment_id).filter(Boolean));
  const eligible = [...caseData.judgments].reverse().filter(j =>
    !superseded.has(j.judgment_id) && j.case_revision === metadata.revision && j.source_revision === metadata.source_revision
    && (!j.rubric_version || j.rubric_version === caseData.rubric?.rubric_id));
  return eligible.find(j => j.rater_id === reviewer) || eligible.find(isEmptyPlaceholder) || null;
}
function reviewStatus(caseData) {
  const review = currentReview(caseData);
  if (!review || review.rater_id !== reviewer) return "Not reviewed";
  return review.status === "complete" ? "Completed" : "Draft";
}
function caseSummary(metadata, status) {
  return `${metadata.case_id}\n${metadata.source_language || "—"} → ${metadata.target_language || "—"} · ${status}`;
}
async function advanceAfterCompletion(completedId) {
  collapseCase("Review complete. Looking for your next unfinished case…");
  const cases = await loadCases();
  const position = cases.findIndex(c => c.case_id === completedId);
  const ordered = [...cases.slice(position + 1), ...cases.slice(0, position + 1)];
  for (const candidate of ordered) {
    if (candidate.case_id === completedId) continue;
    const next = await api(`/api/cases/${encodeURIComponent(candidate.case_id)}`);
    if (currentReview(next)?.status === "complete") continue;
    current = next;
    renderCase();
    $("case-title").scrollIntoView({block: "start"});
    notice(`Assessment saved. Opened your next unfinished case: ${candidate.case_id}. Submit changes to publish your reviews.`);
    return;
  }
  const skill = skills.find(s => s.id === $("skill-filter").value);
  collapseCase(`You have completed all cases for ${skill.label}. You can reopen a case from the list to review it again.`);
  notice(`Assessment saved. You have completed all cases for ${skill.label}. Submit changes to publish your reviews.`);
  $("case-empty").scrollIntoView({block: "nearest"});
}
function isEmptyPlaceholder(j) {
  return j.rater_id == null && j.status === "pending" && j.overall_score == null
    && Object.values(j.dimension_scores || {}).every(value => value == null)
    && !j.rationale?.trim() && !(j.issues || []).length;
}
function loadAssessment() {
  const j = activeJudgment, form = $("judgment-form");
  for (const element of form.elements) element.disabled = false;
  text("assessment-info", j && !isEmptyPlaceholder(j)
    ? `${j.status === "complete" ? "Your latest completed review" : "Your draft review"}. Edit your scores or comments below; earlier versions are preserved.`
    : "You have not reviewed this version of the case yet. Enter your scores and comments below.");
  text("assessment-reviewer", reviewer);
  text("assigned-rubric", current.rubric?.label || "No unique matching rubric is configured. Ask the dataset maintainer before completing this assessment.");
  field(form, "overall_score").value = j?.overall_score ?? "";
  for (const dimension of ["fidelity", "english_naturalness", "literary_voice"]) field(form, dimension).value = j?.dimension_scores?.[dimension] ?? "";
  field(form, "rationale").value = j?.rationale || "";
  $("issues").replaceChildren();
  for (const issue of j?.issues || []) addIssue(issue);
  renderGuidance();
  form.querySelector('[value="complete"]').disabled = !current.rubric;
  dirty = false;
}
function renderHistory(superseded) {
  const reviews = [...current.judgments].reverse().filter(j =>
    !isEmptyPlaceholder(j) && j.judgment_id !== activeJudgment?.judgment_id);
  const container = $("review-history-list");
  container.replaceChildren();
  $("review-history").open = false;
  show("review-history", reviews.length > 0);
  text("review-history-summary", `Review history (${reviews.length})`);
  function line(parent, value, className = "history-text") {
    const paragraph = document.createElement("p");
    paragraph.className = className; paragraph.textContent = value; parent.append(paragraph);
  }
  for (const j of reviews) {
    const entry = document.createElement("details"); entry.className = "history-entry";
    const summary = document.createElement("summary");
    const kind = superseded.has(j.judgment_id) ? "Earlier version" : j.rater_id === reviewer ? "Earlier review" : "Other reviewer";
    summary.textContent = `${j.rater_id || "Unassigned"} · ${j.status === "complete" ? "Complete" : "Draft"} · overall ${j.overall_score ?? "unset"} · ${kind}`;
    entry.append(summary);
    line(entry, `Case revision ${j.case_revision} · source revision ${j.source_revision} · rubric ${j.rubric_version || "unset"}${j.created_at ? ` · ${new Date(j.created_at).toLocaleString()}` : ""}`, "muted");
    for (const [dimension, label] of [["fidelity", "Fidelity"], ["english_naturalness", "English naturalness"], ["literary_voice", "Literary voice"]]) {
      line(entry, `${label}: ${j.dimension_scores?.[dimension] ?? "unset"}`);
    }
    line(entry, `Comments: ${j.rationale || "None"}`);
    for (const issue of j.issues || []) {
      const box = document.createElement("div"); box.className = "issue";
      line(box, `${issue.dimension.replaceAll("_", " ")} · ${issue.severity}`);
      if (issue.source_quote) line(box, `Source quote: ${issue.source_quote}`);
      if (issue.translation_quote) line(box, `Translation quote: ${issue.translation_quote}`);
      line(box, `Explanation: ${issue.explanation || "None"}`);
      entry.append(box);
    }
    container.append(entry);
  }
}
function renderGuidance() {
  const rubric = current.rubric;
  $("rubric-guidance").replaceChildren();
  if (!rubric) { text("rubric-guidance", "Scoring guidance must be configured by the dataset maintainer. You can still save a draft assessment."); return; }
  const guidance = document.createElement("p"); guidance.textContent = rubric.guidance; $("rubric-guidance").append(guidance);
  for (const [score, anchor] of Object.entries(rubric.scale.anchors)) { const row = document.createElement("p"); row.textContent = `${score} — ${anchor}`; $("rubric-guidance").append(row); }
  for (const [name, description] of Object.entries(rubric.dimensions)) { const row = document.createElement("p"); row.textContent = `${name.replaceAll("_", " ")} — ${description}`; $("rubric-guidance").append(row); }
}
function addIssue(issue = {}, disabled = false) {
  const box = document.createElement("div"); box.className = "issue";
  const controls = [
    ["dimension", "Dimension", ["fidelity", "english_naturalness", "literary_voice"]],
    ["severity", "Severity", ["minor", "major", "critical"]],
    ["source_quote", "Source quote"], ["translation_quote", "Translation quote"], ["explanation", "Explanation"]
  ];
  for (const [name, label, choices] of controls) {
    const wrapper = document.createElement("label"); wrapper.textContent = label;
    const control = document.createElement(choices ? "select" : "textarea");
    control.dataset.field = name; control.disabled = disabled;
    if (choices) control.replaceChildren(...choices.map(v => option(v, v.replaceAll("_", " "))));
    else { control.rows = 2; control.maxLength = 10000; }
    if (issue[name] !== undefined) control.value = issue[name];
    wrapper.append(control); box.append(wrapper);
  }
  const remove = document.createElement("button"); remove.type = "button"; remove.className = "quiet"; remove.textContent = "Remove issue"; remove.disabled = disabled;
  remove.addEventListener("click", () => { box.remove(); dirty = true; }); box.append(remove); $("issues").append(box);
}
function renderPassages() {
  const filtered = passages.filter(p => (!$("work-filter").value || p.group_id === $("work-filter").value) && (!$("language-filter").value || p.source_language === $("language-filter").value));
  $("passage-list").replaceChildren();
  for (const p of filtered) {
    const button = document.createElement("button");
    button.textContent = `${p.work?.title || p.group_id}\n${p.passage_id} · ${p.source_language} · rev ${p.revision}`;
    button.addEventListener("click", run(async () => { if (canLeave()) { dirty = false; await openPassage(p.passage_id, p.revision); } }));
    $("passage-list").append(button);
  }
  if (!filtered.length) { const empty = document.createElement("p"); empty.textContent = "No matching passages."; $("passage-list").append(empty); }
}
async function openPassage(id, revision) {
  const passage = await api(`/api/passages/${encodeURIComponent(id)}?revision=${revision}`);
  const p = passage.metadata;
  show("passage-detail", true);
  text("passage-title", p.work?.title || p.passage_id);
  text("passage-info", `${p.group_id} · ${p.passage_id} · ${p.source_language} · revision ${p.revision} · ${p.work?.author || "Author unspecified"}`);
  text("passage-text", passage.text); $("passage-text").lang = p.source_language;
  text("passage-context", `Origin: ${p.provenance?.source_origin || "Unspecified"}. Rights: ${p.provenance?.usage_rights || "pending"}. ${p.context?.background || ""}`);
}

for (const select of document.querySelectorAll("select.score")) select.replaceChildren(option("", "Unset"), ...[1,2,3,4,5].map(n => option(n, String(n))));
$("login-form").addEventListener("submit", run(async () => {
  const credentials = {key: $("access-key").value};
  if (reviewerLabelRequired) credentials.rater_id = $("reviewer-label").value;
  let auth;
  try { auth = await api("/auth/login", "POST", credentials); }
  catch (error) { await loadLoginConfig(); throw error; }
  $("access-key").value = ""; csrf = auth.csrf_token; reviewer = auth.rater_id; await enter(); show("notice", false);
}));
$("logout").addEventListener("click", run(async () => {
  if (!canLeave()) return;
  await api("/auth/logout", "POST", {});
  csrf = ""; reviewer = ""; current = null; dirty = false;
  show("workspace", false); show("login-panel", true); show("logout", false); show("session-reviewer", false); notice("Signed out.");
  await loadLoginConfig();
}));
$("cases-tab").addEventListener("click", () => { if (canLeave()) { dirty = false; setTab("cases"); } });
$("passages-tab").addEventListener("click", run(async () => { if (canLeave()) { dirty = false; setTab("passages"); await refreshPassages(); } }));
$("skill-filter").addEventListener("change", run(async () => {
  if (!canLeave()) { $("skill-filter").value = current?.skill || "literary-translation"; return; }
  collapseCase(); await loadCases();
}));
$("load-latest-review").addEventListener("click", run(async () => {
  if (canLeave()) { await openCase(current.metadata.case_id); await refreshWorkspace(); notice("Latest saved review loaded."); }
}));
$("add-issue").addEventListener("click", () => { if ($("issues").children.length >= 50) { notice("An assessment supports at most 50 issues.", true); return; } addIssue(); dirty = true; });
$("judgment-form").addEventListener("submit", run(async event => {
  const form = $("judgment-form"), value = name => field(form, name).value;
  const score = name => value(name) === "" ? null : Number(value(name));
  const issues = Array.from($("issues").children).map(box => Object.fromEntries(Array.from(box.querySelectorAll("[data-field]")).map(control => [control.dataset.field, control.value])));
  const status = event.submitter?.value || "pending";
  $("workspace").inert = true;
  try {
    current = await api(`/api/cases/${encodeURIComponent(current.metadata.case_id)}/judgments`, "POST", {
      version: current.version, supersedes_judgment_id: activeJudgment?.judgment_id || null,
      status, overall_score: score("overall_score"),
      dimension_scores: {fidelity: score("fidelity"), english_naturalness: score("english_naturalness"), literary_voice: score("literary_voice")},
      rationale: nullable(value("rationale")), issues
    });
    if (status === "complete") {
      try { await advanceAfterCompletion(current.metadata.case_id); }
      catch (error) {
        collapseCase("Your review was saved. Select a case from the list to continue.");
        throw new Error(`Your review was saved, but the next case could not be loaded: ${error.message}`);
      }
    } else {
      renderCase();
      notice("Assessment saved in the temporary workspace. Submit changes to update the source files.");
    }
  } catch (error) {
    if (error.status === 409) show("review-conflict", true);
    throw error;
  } finally {
    $("workspace").inert = false;
  }
}));
for (const id of ["work-filter", "language-filter"]) $(id).addEventListener("change", renderPassages);
$("submit-changes").addEventListener("click", run(async () => {
  if (dirty) { notice("Save your form changes to the temporary workspace before submitting.", true); return; }
  await refreshWorkspace();
  if (!pendingWorkspace.pending_files) return;
  $("pending-records").replaceChildren();
  for (const id of pendingWorkspace.cases) { const item = document.createElement("li"); item.textContent = `Assessments for ${id}`; $("pending-records").append(item); }
  text("submit-result", "");
  submissionVersion = pendingWorkspace.version;
  $("confirm-submit").disabled = false;
  $("submit-dialog").showModal();
}));
$("cancel-submit").addEventListener("click", () => $("submit-dialog").close());
$("confirm-submit").addEventListener("click", async () => {
  $("confirm-submit").disabled = true;
  try {
    await api("/api/workspace/submit", "POST", {version: submissionVersion});
    $("submit-dialog").close();
    await refreshWorkspace();
    notice("Changes submitted to the original evaluation files.");
  } catch (error) {
    text("submit-result", `${error.message} Close this dialog and review the current changes before trying again.`);
  }
});
for (const form of document.querySelectorAll("#workspace form")) form.addEventListener("input", () => { dirty = true; });
window.addEventListener("beforeunload", event => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
async function loadLoginConfig() {
  const config = await api("/auth/config");
  reviewerLabelRequired = config.reviewer_label_required;
  show("reviewer-entry", reviewerLabelRequired); show("fixed-reviewer-note", !reviewerLabelRequired);
  $("reviewer-label").required = reviewerLabelRequired;
  $("reviewer-label").disabled = !reviewerLabelRequired;
}
(async () => {
  try {
    await loadLoginConfig();
    const auth = await api("/auth/session");
    csrf = auth.csrf_token; reviewer = auth.rater_id; await enter();
  } catch (error) { if (!error.message.includes("Sign in")) notice(error.message, true); }
})();
