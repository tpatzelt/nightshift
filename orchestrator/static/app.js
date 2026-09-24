/* NIGHTSHIFT dashboard. Polls /api/overview; every mutation is a queued file the
   orchestrator drains, so this page can never race the loop for state.json. */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const POLL_MS = 5000;

const state = { data: null, tab: "board", repos: [], rawMode: false, goals: [] };

function el(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v === null || v === undefined) continue;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
}

async function api(path, options) {
  const res = await fetch(`/api/${path}`, {
    headers: { "Content-Type": "application/json" }, ...options,
  });
  const body = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
  if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
  return body;
}

const money = (n) => `$${(Number(n) || 0).toFixed(2)}`;
const short = (s, n = 90) => (!s ? "" : s.length > n ? s.slice(0, n - 1) + "…" : s);

function ago(iso) {
  if (!iso) return "—";
  const secs = (Date.now() - new Date(iso).getTime()) / 1000;
  if (Number.isNaN(secs)) return "—";
  if (secs < 90) return `${Math.max(0, Math.round(secs))}s ago`;
  if (secs < 5400) return `${Math.round(secs / 60)}m ago`;
  if (secs < 172800) return `${Math.round(secs / 3600)}h ago`;
  return `${Math.round(secs / 86400)}d ago`;
}

/* ----------------------------------------------------------------- header */
function runStatus(d) {
  if (d.stopped) return { cls: "stopped", label: "stopped" };
  if (d.state.paused) return { cls: "paused", label: "paused" };
  if (!d.armed) return { cls: "idle", label: d.queue.length ? "arming next" : "idle" };
  if (d.state.limit_until) return { cls: "paused", label: "rate limited" };
  if (d.state.current_task) return { cls: "running", label: "working" };
  return { cls: "running", label: "armed" };
}

function renderHeader(d) {
  const run = d.run || {};
  const line = d.armed
    ? `Run ${run.run_no ?? "?"} — ${run.title || "charter"} · ${(run.goals || []).join(" ")}`
    : d.queue.length
      ? `no charter armed · ${d.queue.length} queued`
      : "no charter armed · queue one below";
  $("#run-line").textContent = line;

  const st = runStatus(d);
  const pill = $("#status-pill");
  pill.className = `pill ${st.cls}`;
  pill.textContent = st.label;

  const controls = $("#controls");
  controls.replaceChildren();
  if (d.read_only) {
    controls.append(el("span", { class: "pill" }, "read-only"));
    return;
  }
  const button = (label, cmd, cls = "ghost", confirmText) =>
    el("button", {
      class: cls,
      onclick: async () => {
        if (confirmText && !window.confirm(confirmText)) return;
        try {
          await api("control", { method: "POST", body: JSON.stringify({ cmd }) });
          $("#footer-note").textContent = `sent "${cmd}" — the loop picks it up within a few seconds`;
          refresh();
        } catch (err) { alert(err.message); }
      },
    }, label);

  if (d.state.paused || d.stopped) controls.append(button("Resume", "resume"));
  else controls.append(button("Pause", "pause"));
  controls.append(button("Stop", "stop", "danger",
    "Stop kills the running agent container and halts the loop. Continue?"));
  if (d.armed) {
    controls.append(button("Plan now", "plan-now"));
    controls.append(button("Finish run", "finish", "ghost",
      "Finish archives this run under charters/ and arms the next queued charter. Continue?"));
  }
}

/* ------------------------------------------------------------------ tiles */
function renderTiles(d) {
  const s = d.stats;
  const dl = d.deadline || {};
  const hb = d.health.heartbeat_min;
  const tiles = [
    ["merged", s.merges, `${s.tasks.backlog} in backlog`],
    ["parked", s.tasks.parked, `${d.state.consecutive_failures || 0} in a row`,
      d.state.consecutive_failures >= 2 ? "warn" : ""],
    ["spend", money(s.cost_usd), `${s.agent_runs} agent runs`],
    ["deadline", dl.hours_left === null || dl.hours_left === undefined
      ? (dl.hours ? "—" : "none")
      : `${dl.hours_left}h`, dl.ends ? dl.ends.replace("T", " ") : "no deadline",
      dl.hours_left !== null && dl.hours_left !== undefined && dl.hours_left < 4 ? "warn" : ""],
    ["queued", d.queue.length, d.queue.length ? short(d.queue[0].title, 26) : "nothing waiting"],
    ["heartbeat", hb === null ? "—" : `${hb}m`, "since last progress",
      hb !== null && hb > 30 ? "bad" : ""],
    ["disk free", `${d.health.disk_free_gb}G`, "on /data",
      d.health.disk_free_gb < 10 ? "warn" : ""],
    ["decisions", s.decisions, "planner ADRs"],
  ];
  $("#tiles").replaceChildren(...tiles.map(([k, v, sub, cls]) =>
    el("div", { class: "tile" },
      el("div", { class: "k" }, k),
      el("div", { class: `v ${cls || ""}` }, String(v)),
      el("div", { class: "s" }, sub || ""))));
}

/* -------------------------------------------------------------------- now */
function renderNow(d) {
  const card = $("#now-card");
  const cur = d.current;
  if (!cur || !cur.task) {
    let why = "Nothing running.";
    if (d.state.paused) why = `Paused — ${d.state.pause_reason || "no reason recorded"}.`;
    else if (!d.armed) why = d.queue.length
      ? "Between runs: the next queued charter is armed within a minute."
      : "No charter armed. Queue one under Charters.";
    else if (d.state.limit_until) why = "Waiting out a rate limit.";
    else if (d.state.idle_planner_streak) why =
      `Backlog empty — ${d.state.idle_planner_streak} planner run(s) added nothing.`;
    card.replaceChildren(el("div", { class: "card" },
      el("div", { class: "now-head" }, el("span", { class: "title" }, "Idle")),
      el("div", { class: "meta", style: "color:var(--ink-3);font-size:12.5px;margin-top:4px" }, why)));
    return;
  }
  const t = cur.task;
  card.replaceChildren(el("div", { class: "card" },
    el("div", { class: "now-head" },
      el("span", { class: "id" }, t.id),
      el("span", { class: "title" }, t.title || ""),
      el("span", { class: "meta" },
        `${t.charter_goal || ""} · ${t.roadmap_ref || ""} · attempt ${(t.attempts || 0) + 1} of 2`)),
    el("ul", { class: "feed" }, (cur.activity || []).slice().reverse().map((item) =>
      el("li", { class: item.kind },
        el("span", { class: "tag" }, item.kind === "say" ? "says" : item.kind),
        el("span", { class: "body" }, short(item.text, 400)))))));
}

/* ------------------------------------------------------------------ board */
async function renderBoard() {
  const data = await api("tasks");
  const lane = (name, items, cls) => el("div", { class: "lane" },
    el("h3", {}, name, " ", el("span", {}, String(items.length))),
    items.slice().reverse().map((t) => el("div", {
      class: `task ${cls}`, onclick: () => openTask(t.id),
    },
      el("div", { class: "id" }, t.id),
      el("div", { class: "t" }, short(t.title, 110)),
      el("div", { class: "m" },
        t.goal && el("span", { class: "badge" }, t.goal),
        t.milestone && el("span", {}, t.milestone),
        t.merged_sha && el("span", {}, `merged ${t.merged_sha}`),
        t.attempts ? el("span", {}, `${t.attempts} attempt${t.attempts > 1 ? "s" : ""}`) : null,
        t.park_reason && el("span", {}, short(t.park_reason, 60))))));
  $("#board").replaceChildren(
    lane("Ready", data.backlog, "ready"),
    lane("Merged", data.done, "done"),
    lane("Parked", data.parked, "parked"));
}

async function openTask(id) {
  const body = $("#drawer-body");
  body.replaceChildren(el("p", { class: "hint" }, "loading…"));
  $("#drawer").hidden = false;
  try {
    const d = await api(`tasks/${id}`);
    const t = d.task;
    const rows = [
      ["status", t.status], ["goal", t.charter_goal], ["milestone", t.roadmap_ref],
      ["project", t.project], ["attempts", t.attempts ?? 0],
      ["merged", t.merged_sha ? `${t.merged_sha} · ${t.merged_at || ""}` : "—"],
      ["limits", `${t.max_diff_lines} diff lines · ${t.timeout_min}m · ${t.max_turns} turns`],
    ];
    body.replaceChildren(
      el("h3", {}, `${t.id}: ${t.title}`),
      el("p", { class: "hint" }, t.why || ""),
      el("dl", {}, rows.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, String(v ?? "—"))])),
      el("h2", {}, "Acceptance"),
      el("ul", {}, (t.acceptance || []).map((c) => el("li", {}, el("code", {}, c)))),
      el("h2", {}, "Paths"),
      el("ul", {}, [
        el("li", {}, "allowed: ", (t.allowed_paths || []).join(", ") || "—"),
        el("li", {}, "protected: ", (t.protected_paths || []).join(", ") || "—")]),
      t.park_reason ? el("h2", {}, "Parked because") : null,
      t.park_reason ? el("p", { class: "hint" }, t.park_reason) : null,
      (d.gates || []).length ? el("h2", {}, "Gate runs") : null,
      el("ul", {}, (d.gates || []).map((g) =>
        el("li", {}, `attempt ${g.attempt}: ${g.ok ? "passed" : "failed"}`,
          (g.failures || []).length ? el("ul", {}, g.failures.map((f) => el("li", {}, f))) : null))),
      (t.notes || []).length ? el("h2", {}, "Notes") : null,
      el("ul", {}, (t.notes || []).map((n) => el("li", {}, n))),
      (d.activity || []).length ? el("h2", {}, "Last transcript") : null,
      el("ul", { class: "feed" }, (d.activity || []).slice(-60).reverse().map((item) =>
        el("li", { class: item.kind },
          el("span", { class: "tag" }, item.kind),
          el("span", { class: "body" }, short(item.text, 400))))));
  } catch (err) {
    body.replaceChildren(el("p", { class: "msg err" }, err.message));
  }
}

/* --------------------------------------------------------------- charters */
function renderQueue(d) {
  const list = $("#queue-list");
  if (!d.queue.length) {
    list.replaceChildren(el("p", { class: "hint" }, "Nothing queued."));
    return;
  }
  list.replaceChildren(...d.queue.map((q, i) => el("div", { class: "q" },
    el("div", { class: "n" }, String(i + 1)),
    el("div", { class: "body" },
      el("div", { class: "t" }, q.title),
      el("div", { class: "m" },
        `${(q.goals || []).join(" ")} · ${Object.keys(q.projects || {}).join(", ")} · `,
        q.run_until_hours ? `${q.run_until_hours}h · ` : "no deadline · ",
        `queued ${ago(q.created)}`)),
    d.read_only ? null : el("div", { class: "acts" },
      el("button", { class: "ghost", title: "move up",
        onclick: () => move(q.id, -1) }, "↑"),
      el("button", { class: "ghost", title: "move down",
        onclick: () => move(q.id, 1) }, "↓"),
      el("button", { class: "danger", title: "remove",
        onclick: () => removeEntry(q.id, q.title) }, "×")))));
}

async function move(id, delta) {
  try {
    await api(`queue/${id}/move`, { method: "POST", body: JSON.stringify({ delta }) });
    refresh();
  } catch (err) { alert(err.message); }
}

async function removeEntry(id, title) {
  if (!window.confirm(`Remove "${title}" from the queue?`)) return;
  try {
    await api(`queue/${id}`, { method: "DELETE" });
    refresh();
  } catch (err) { alert(err.message); }
}

/* -- the charter builder ---------------------------------------------- */
function goalRow(index) {
  const gid = `G${index + 1}`;
  const row = el("div", { class: "goal-row" },
    el("button", { class: "rm", type: "button", title: "remove",
      onclick: (ev) => { ev.preventDefault(); state.goals.splice(index, 1); drawGoals(); } }, "remove"),
    el("div", { class: "gid" }, gid),
    el("label", {}, "What must be true",
      el("textarea", { rows: "2", "data-goal": index, "data-field": "text",
        placeholder: "The triage path explains every decision it makes." })),
    el("label", {}, "Definition of done ",
      el("span", { class: "sub" }, "the command or observation that proves it"),
      el("textarea", { rows: "2", "data-goal": index, "data-field": "done",
        placeholder: "uv run pytest -q tests/test_triage_reasons.py passes and every result carries a reason." })));
  $("textarea[data-field=text]", row).value = state.goals[index].text;
  $("textarea[data-field=done]", row).value = state.goals[index].done;
  return row;
}

function drawGoals() {
  if (!state.goals.length) state.goals.push({ text: "", done: "" });
  $("#goals").replaceChildren(...state.goals.map((_, i) => goalRow(i)));
  updatePreview();
}

function collectForm() {
  const form = $("#charter-form");
  const data = Object.fromEntries(new FormData(form).entries());
  state.goals = state.goals.map((g, i) => ({
    text: ($(`textarea[data-goal="${i}"][data-field=text]`)?.value || "").trim(),
    done: ($(`textarea[data-goal="${i}"][data-field=done]`)?.value || "").trim(),
  }));
  return data;
}

function buildCharter() {
  const f = collectForm();
  const goals = state.goals.filter((g) => g.text);
  const lines = (text) => (text || "").split("\n").map((s) => s.trim()).filter(Boolean);
  const ids = goals.map((_, i) => `G${i + 1}`);
  const out = [
    `# ${f.title || "Untitled charter"}`, "",
    "Charter  (immutable — agents must not edit)", "",
    "## Goals",
    ...goals.map((g, i) => `- G${i + 1}: ${g.text}`), "",
    "## Non-goals",
    ...(lines(f.non_goals).length ? lines(f.non_goals).map((s) => `- ${s}`)
      : ["- No changes to deployment, CI configuration or dependency lockfiles.",
         "- No reformatting or renaming that a task does not require."]), "",
    "## Constraints",
    ...(lines(f.constraints).length ? lines(f.constraints).map((s) => `- ${s}`)
      : [`- \`${f.test_cmd}\` must stay green.`,
         "- No secrets, no API keys and no personal data in the repository."]), "",
    "## Definition of done per goal",
    ...goals.map((g, i) => `- G${i + 1}: ${g.done || "the goal above is demonstrably met."}`), "",
    "## Priority order",
    ids.join(" > ") || "G1", "",
    "## Projects",
    `- repo: ${f.repo || "repo"}   goals: [${ids.join(", ")}]   test_cmd: "${f.test_cmd}"`,
    "",
  ];
  return out.join("\n");
}

function charterText() {
  return state.rawMode ? $("#raw-charter").value : buildCharter();
}

function updatePreview() {
  if (!state.rawMode) $("#charter-preview").textContent = buildCharter();
}

async function loadRepos() {
  try {
    const { repos } = await api("repos");
    state.repos = repos;
    const select = $("#repo-select");
    select.replaceChildren(...repos.map((r) =>
      el("option", { value: r.name }, `${r.name}${r.seeded ? " (seeded)" : ""}`)));
    if (!repos.length) select.replaceChildren(el("option", { value: "" }, "no repositories found"));
    onRepoChange();
  } catch { /* the form still works with a hand-typed charter */ }
}

function onRepoChange() {
  const repo = state.repos.find((r) => r.name === $("#repo-select").value);
  const refs = repo ? repo.branches : [];
  $("#ref-select").replaceChildren(
    ...refs.map((b) => el("option", { value: b, selected: repo && b === repo.head }, b)));
  $("#fresh-wrap").hidden = !(repo && repo.seeded);
  updatePreview();
}

async function submitCharter(validateOnly) {
  const msg = $("#form-msg");
  msg.className = "msg";
  msg.textContent = "…";
  const f = collectForm();
  const charter = charterText();
  try {
    if (validateOnly) {
      const res = await api("validate", {
        method: "POST", body: JSON.stringify({ charter_md: charter }) });
      if (!res.ok) throw new Error(res.error);
      msg.className = "msg ok";
      msg.textContent = `Valid: goals ${res.goals.join(", ")} · projects ${Object.keys(res.projects).join(", ")}`;
      return;
    }
    const sources = {};
    if (f.repo) {
      const repo = state.repos.find((r) => r.name === f.repo);
      sources[f.repo] = {
        source: repo ? repo.source : f.repo,
        ref: f.ref || "HEAD",
        fresh_clone: Boolean(f.fresh_clone),
      };
    }
    const body = {
      title: f.title, charter_md: charter, sources,
      run_until_hours: Number(f.run_until_hours || 0),
    };
    const res = await api("queue", { method: "POST", body: JSON.stringify(body) });
    msg.className = "msg ok";
    msg.textContent = `Queued "${res.queued.title}" at position ${res.queued.position}.`;
    state.goals = [{ text: "", done: "" }];
    $("#charter-form").reset();
    $("#raw-charter").value = "";
    drawGoals();
    await loadRepos();
    refresh();
  } catch (err) {
    msg.className = "msg err";
    msg.textContent = err.message;
  }
}

/* --------------------------------------------------------------- progress */
function renderGoals(d) {
  const panel = $("#goals-panel");
  if (!d.goals.length) {
    panel.replaceChildren(el("p", { class: "hint" }, "No charter armed."));
    return;
  }
  const max = Math.max(1, ...d.goals.map((g) => g.merges));
  panel.replaceChildren(...d.goals.map((g) => el("div", { class: "goal" },
    el("div", { class: "h" },
      el("span", { class: "gid" }, g.id),
      el("span", { class: "n" }, `${g.merges} merged`)),
    el("div", { class: "txt" }, g.text),
    el("div", { class: "bar" }, el("i", { style: `width:${(g.merges / max) * 100}%` })))));
}

/* Two single-series charts, never one with two scales: merges are a count and
   spend is money, and a shared axis would only invent a relationship.

   SVG nodes must be created in the SVG namespace - document.createElement("svg")
   yields an unknown HTML element that renders nothing at all, with no error. */
const SVG_NS = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

const VIEW = { w: 320, h: 96, pad: 16, foot: 16 };

function barChart(days, wrap) {
  const { w, h, pad, foot } = VIEW;
  const max = Math.max(1, ...days.map((d) => d.merges));
  const step = (w - pad * 2) / days.length;
  const width = Math.max(2, Math.min(20, step - 2));      // 2px surface gap
  const root = svg("svg", { viewBox: `0 0 ${w} ${h}`, role: "img",
                            "aria-label": `merges per day, peak ${max}` });
  days.forEach((d, i) => {
    const height = (d.merges / max) * (h - foot - 12);
    const x = pad + i * step + (step - width) / 2;
    const y = h - foot - height;
    const bar = svg("rect", {
      x, y: d.merges ? y : h - foot - 2, width,
      height: d.merges ? Math.max(height, 2) : 2,
      rx: 4, fill: d.merges ? "var(--series-1)" : "var(--line)",
    });
    bar.addEventListener("pointerenter",
      () => tip(wrap, x + width / 2, y, `${d.day}\n${d.merges} merged`));
    bar.addEventListener("pointerleave", () => untip(wrap));
    root.append(bar);
    if (d.merges === max) {                                // selective direct label
      root.append(svg("text", { x: x + width / 2, y: y - 4, "text-anchor": "middle",
                                class: "axis" }, String(max)));
    }
  });
  root.append(svg("text", { x: pad, y: h - 2, class: "axis" }, days[0].day.slice(5)));
  root.append(svg("text", { x: w - pad, y: h - 2, "text-anchor": "end", class: "axis" },
                  days.at(-1).day.slice(5)));
  return root;
}

function lineChart(days, wrap) {
  const { w, h, pad, foot } = VIEW;
  const max = Math.max(0.01, ...days.map((d) => d.cumulative_usd));
  const px = (i) => (days.length === 1 ? w / 2 : pad + (i * (w - pad * 2)) / (days.length - 1));
  const py = (v) => h - foot - (v / max) * (h - foot - 12);
  const points = days.map((d, i) => [px(i), py(d.cumulative_usd)]);
  const path = points.map((p, i) => `${i ? "L" : "M"}${p[0]},${p[1]}`).join(" ");
  const root = svg("svg", { viewBox: `0 0 ${w} ${h}`, role: "img",
                            "aria-label": `cumulative spend, ${money(max)} total` });
  const area = [`M${points[0][0]},${h - foot}`,
                ...points.map((p) => `L${p[0]},${p[1]}`),
                `L${points.at(-1)[0]},${h - foot}`, "Z"].join(" ");
  root.append(svg("path", { d: area, fill: "var(--series-2)", opacity: ".16" }));
  root.append(svg("path", { d: path, fill: "none", stroke: "var(--series-2)",
                            "stroke-width": "2", "stroke-linejoin": "round",
                            "stroke-linecap": "round" }));
  const dot = svg("circle", { r: "4.5", fill: "var(--series-2)",
                              stroke: "var(--surface-1)", "stroke-width": "2",
                              opacity: "0" });
  root.append(dot);
  root.addEventListener("pointermove", (ev) => {           // crosshair tooltip
    const box = root.getBoundingClientRect();
    const rel = ((ev.clientX - box.left) / box.width) * w;
    let best = 0;
    points.forEach((p, i) => {
      if (Math.abs(p[0] - rel) < Math.abs(points[best][0] - rel)) best = i;
    });
    dot.setAttribute("cx", points[best][0]);
    dot.setAttribute("cy", points[best][1]);
    dot.setAttribute("opacity", "1");
    tip(wrap, points[best][0], points[best][1],
      `${days[best].day}\n${money(days[best].cumulative_usd)} total\n` +
      `${money(days[best].cost_usd)} that day`);
  });
  root.addEventListener("pointerleave", () => {
    dot.setAttribute("opacity", "0");
    untip(wrap);
  });
  root.append(svg("text", { x: pad, y: h - 2, class: "axis" }, days[0].day.slice(5)));
  root.append(svg("text", { x: w - pad, y: h - 2, "text-anchor": "end", class: "axis" },
                  days.at(-1).day.slice(5)));
  return root;
}

function tip(wrap, xViewBox, yViewBox, text) {
  untip(wrap);
  const node = el("div", { class: "tip" }, ...text.split("\n").flatMap((t, i) =>
    i ? [el("br"), t] : [t]));
  node.style.left = `${Math.max(0, Math.min(72, (xViewBox / VIEW.w) * 100 - 8))}%`;
  node.style.top = `${Math.max(-6, (yViewBox / VIEW.h) * 100 - 22)}%`;
  wrap.append(node);
}
const untip = (wrap) => $$(".tip", wrap).forEach((n) => n.remove());

async function renderProgress(d) {
  renderGoals(d);
  const { days } = await api("usage");
  const charts = $("#charts");
  if (!days.length) {
    charts.replaceChildren(el("p", { class: "hint" }, "No agent runs recorded yet."));
  } else {
    const merges = days.reduce((a, b) => a + b.merges, 0);
    const wrapA = el("div", { class: "chart-wrap" });
    const wrapB = el("div", { class: "chart-wrap" });
    wrapA.append(barChart(days, wrapA));
    wrapB.append(lineChart(days, wrapB));
    charts.replaceChildren(
      el("div", { class: "chart" }, el("h3", {}, "Tasks merged per day"),
        el("div", { class: "total" }, String(merges)), wrapA),
      el("div", { class: "chart" }, el("h3", {}, "Spend, cumulative"),
        el("div", { class: "total" }, money(days.at(-1).cumulative_usd)), wrapB));
  }

  const dig = $("#digest");
  if (d.digest) {
    dig.replaceChildren(el("div", { class: "card" },
      el("div", { class: "now-head" },
        el("span", { class: "title" }, `Digest ${d.digest.date}`),
        el("span", { class: "meta" }, `drift ${d.digest.drift_score}/10`)),
      el("p", { class: "hint", style: "margin-top:8px;white-space:pre-wrap" }, d.digest.digest || ""),
      el("ul", {}, (d.digest.findings || []).slice(0, 8).map((f) => el("li", {}, f)))));
  } else {
    dig.replaceChildren(el("p", { class: "hint" }, "No digest yet — the auditor writes one daily."));
  }

  const { decisions } = await api("decisions");
  $("#decisions").replaceChildren(...decisions.slice(0, 25).map((dec) =>
    el("div", { class: "row", onclick: () => openDecision(dec.name) },
      el("span", {}, short(dec.title, 70)),
      el("span", { class: "m" }, dec.ts.slice(0, 8)))));
}

async function openDecision(name) {
  $("#drawer").hidden = false;
  $("#drawer-body").replaceChildren(el("p", { class: "hint" }, "loading…"));
  const d = await api(`decisions/${encodeURIComponent(name)}`);
  $("#drawer-body").replaceChildren(el("pre", { style: "white-space:pre-wrap;font:12.5px/1.6 var(--mono);color:var(--ink-2)" }, d.text));
}

/* ------------------------------------------------------------------- runs */
async function renderRuns() {
  const { runs: list } = await api("runs");
  $("#runs-list").replaceChildren(...(list.length
    ? list.map((r) => el("div", { class: "row", onclick: () => openRun(r.name) },
        el("span", {}, `Run ${r.run_no} — ${short(r.title, 60)}`),
        el("span", { class: "m" }, r.merges !== undefined
          ? `${r.merges} merged · ${money(r.cost_usd || 0)}` : "archived")))
    : [el("p", { class: "hint" }, "No finished runs yet.")]));
}

async function openRun(name) {
  const doc = $("#run-doc");
  doc.replaceChildren(el("p", { class: "hint" }, "loading…"));
  const d = await api(`runs/${encodeURIComponent(name)}`);
  $("#run-doc-title").textContent = name;
  const files = d.files || {};
  doc.replaceChildren(...Object.entries(files).map(([file, text]) =>
    el("details", { open: file === "RESULT.md" },
      el("summary", {}, file), el("pre", {}, text))));
}

/* -------------------------------------------------------------------- log */
async function renderLog() {
  const { lines } = await api("logs?lines=400");
  const node = $("#log");
  const stuck = node.scrollTop + node.clientHeight >= node.scrollHeight - 30;
  node.textContent = lines.join("\n");
  if (stuck) node.scrollTop = node.scrollHeight;
}

/* ------------------------------------------------------------------- wire */
const TABS = ["board", "charters", "progress", "runs", "log"];

function setTab(name, push = true) {
  if (!TABS.includes(name)) name = "board";
  state.tab = name;
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".tab").forEach((s) => s.classList.toggle("active", s.id === `tab-${name}`));
  // The tab lives in the URL, so a view worth coming back to can be bookmarked.
  if (push && window.location.hash.slice(1) !== name) window.location.hash = name;
  refreshTab();
}

async function refreshTab() {
  try {
    if (state.tab === "board") await renderBoard();
    else if (state.tab === "progress" && state.data) await renderProgress(state.data);
    else if (state.tab === "runs") await renderRuns();
    else if (state.tab === "log") await renderLog();
  } catch (err) {
    $("#footer-note").textContent = `refresh failed: ${err.message}`;
  }
}

async function refresh() {
  try {
    const data = await api("overview");
    state.data = data;
    renderHeader(data);
    renderTiles(data);
    renderNow(data);
    renderQueue(data);
    await refreshTab();
    $("#footer-note").textContent =
      `updated ${new Date().toLocaleTimeString()} · polling every ${POLL_MS / 1000}s`;
  } catch (err) {
    $("#footer-note").textContent = `cannot reach the API: ${err.message}`;
  }
}

function init() {
  $$("#tabs button").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));
  $("#drawer-close").addEventListener("click", () => { $("#drawer").hidden = true; });
  $("#drawer").addEventListener("click", (ev) => {
    if (ev.target.id === "drawer") $("#drawer").hidden = true;
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") $("#drawer").hidden = true;
  });
  $("#add-goal").addEventListener("click", () => {
    collectForm();
    state.goals.push({ text: "", done: "" });
    drawGoals();
  });
  $("#charter-form").addEventListener("input", updatePreview);
  $("#charter-form").addEventListener("submit", (ev) => ev.preventDefault());
  $("#repo-select").addEventListener("change", onRepoChange);
  $("#validate-btn").addEventListener("click", () => submitCharter(true));
  $("#queue-btn").addEventListener("click", () => submitCharter(false));
  $("#mode-form").addEventListener("click", () => {
    state.rawMode = false;
    $("#mode-form").classList.add("active"); $("#mode-raw").classList.remove("active");
    $("#charter-form").hidden = false; $("#raw-wrap").hidden = true;
  });
  $("#mode-raw").addEventListener("click", () => {
    if (!$("#raw-charter").value.trim()) $("#raw-charter").value = buildCharter();
    state.rawMode = true;
    $("#mode-raw").classList.add("active"); $("#mode-form").classList.remove("active");
    $("#charter-form").hidden = true; $("#raw-wrap").hidden = false;
  });
  window.addEventListener("hashchange",
    () => setTab(window.location.hash.slice(1), false));
  state.goals = [{ text: "", done: "" }];
  drawGoals();
  loadRepos();
  setTab(window.location.hash.slice(1) || "board", false);
  refresh();
  setInterval(refresh, POLL_MS);
}

document.addEventListener("DOMContentLoaded", init);
