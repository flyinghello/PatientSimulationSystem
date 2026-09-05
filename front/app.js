const studySelect = document.getElementById("studySelect");
const startBtn = document.getElementById("startBtn");
const randomBtn = document.getElementById("randomBtn");
const messagesEl = document.getElementById("messages");
const metaEl = document.getElementById("meta");
const personaBar = document.getElementById("personaBar");
const replyForm = document.getElementById("replyForm");
const crcInput = document.getElementById("crcInput");
const sendBtn = document.getElementById("sendBtn");
const detailDialog = document.getElementById("detailDialog");
const detailJson = document.getElementById("detailJson");
const closeDetail = document.getElementById("closeDetail");
const reportPanel = document.getElementById("reportPanel");
const reportBody = document.getElementById("reportBody");
const retryEvalBtn = document.getElementById("retryEvalBtn");

/** @type {string | null} */
let sessionId = null;
/** @type {Map<number, object>} */
const detailByIndex = new Map();

function setBusy(busy) {
  const hasStudy = Boolean(studySelect.value);
  startBtn.disabled = busy || !hasStudy;
  randomBtn.disabled = busy || !hasStudy;
  sendBtn.disabled = busy;
  crcInput.disabled = busy;
  studySelect.disabled = busy;
  retryEvalBtn.disabled = busy;
}

function clearChat() {
  messagesEl.innerHTML = "";
  detailByIndex.clear();
  reportPanel.hidden = true;
  reportBody.innerHTML = "";
  personaBar.hidden = true;
  personaBar.textContent = "";
}

/**
 * @param {"patient"|"crc"|"system"|"error"} role
 * @param {string} text
 * @param {object | null} detail
 */
function appendBubble(role, text, detail = null) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;

  if (role === "patient" || role === "crc") {
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = role === "patient" ? "患者" : "CRC";
    div.appendChild(who);

    const row = document.createElement("div");
    row.className = "row";

    const textEl = document.createElement("div");
    textEl.className = "text";
    textEl.textContent = text;
    row.appendChild(textEl);

    if (role === "patient" && detail) {
      const idx = detailByIndex.size;
      detailByIndex.set(idx, detail);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "detail-btn";
      btn.textContent = "详情";
      btn.addEventListener("click", () => openDetail(idx));
      row.appendChild(btn);
    }

    div.appendChild(row);
  } else {
    div.textContent = text;
  }

  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function openDetail(idx) {
  const detail = detailByIndex.get(idx);
  detailJson.textContent = JSON.stringify(detail ?? {}, null, 2);
  detailDialog.showModal();
}

closeDetail.addEventListener("click", () => detailDialog.close());
detailDialog.addEventListener("click", (e) => {
  if (e.target === detailDialog) detailDialog.close();
});

function showPersona(text) {
  if (!text) {
    personaBar.hidden = true;
    personaBar.textContent = "";
    return;
  }
  personaBar.hidden = false;
  personaBar.innerHTML = "";
  const label = document.createElement("strong");
  label.textContent = "当前人设";
  personaBar.appendChild(label);
  personaBar.appendChild(document.createTextNode(text));
}

function renderReport(evaluation) {
  if (!evaluation) {
    reportPanel.hidden = true;
    reportBody.innerHTML = "";
    return;
  }

  reportPanel.hidden = false;
  reportBody.innerHTML = "";

  if (evaluation.error) {
    const p = document.createElement("p");
    p.className = "report-error";
    p.textContent = evaluation.error || evaluation.summary || "评分失败";
    reportBody.appendChild(p);
    return;
  }

  const scoreRow = document.createElement("div");
  scoreRow.className = "report-score";
  const big = document.createElement("span");
  big.className = "big";
  big.textContent =
    evaluation.overall_score == null ? "—" : `${evaluation.overall_score}`;
  const pass = document.createElement("span");
  pass.className = evaluation.passed ? "pass" : "fail";
  pass.textContent = evaluation.passed ? "合格" : "不合格";
  scoreRow.appendChild(big);
  scoreRow.appendChild(document.createTextNode("分"));
  scoreRow.appendChild(pass);
  reportBody.appendChild(scoreRow);

  if (evaluation.summary) {
    const summary = document.createElement("p");
    summary.className = "report-summary";
    summary.textContent = evaluation.summary;
    reportBody.appendChild(summary);
  }

  const dims = Array.isArray(evaluation.dimensions)
    ? evaluation.dimensions
    : [];
  if (dims.length) {
    const table = document.createElement("table");
    table.className = "dim-table";
    table.innerHTML =
      "<thead><tr><th>类别</th><th>维度</th><th>分数</th><th>判定</th><th>依据</th><th>建议</th></tr></thead>";
    const tbody = document.createElement("tbody");
    for (const d of dims) {
      const tr = document.createElement("tr");
      const cells = [
        d.category || "",
        d.dimension || "",
        d.score == null ? "" : String(d.score),
        d.passed ? "合格" : "不合格",
        d.evidence || "",
        d.suggestion || "",
      ];
      cells.forEach((text, i) => {
        const td = document.createElement("td");
        td.textContent = text;
        if (i === 3) td.className = d.passed ? "ok" : "bad";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    reportBody.appendChild(table);
  }

  const lists = document.createElement("div");
  lists.className = "report-lists";

  if (evaluation.principles && typeof evaluation.principles === "object") {
    const keys = Object.keys(evaluation.principles);
    if (keys.length) {
      const block = document.createElement("div");
      const h = document.createElement("h4");
      h.textContent = "核心原则";
      const ul = document.createElement("ul");
      for (const k of keys) {
        const li = document.createElement("li");
        li.textContent = `${k}：${evaluation.principles[k] || "—"}`;
        ul.appendChild(li);
      }
      block.appendChild(h);
      block.appendChild(ul);
      lists.appendChild(block);
    }
  }

  for (const [title, key] of [
    ["优点", "strengths"],
    ["改进点", "improvements"],
  ]) {
    const items = evaluation[key];
    if (!Array.isArray(items) || !items.length) continue;
    const block = document.createElement("div");
    const h = document.createElement("h4");
    h.textContent = title;
    const ul = document.createElement("ul");
    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item;
      ul.appendChild(li);
    }
    block.appendChild(h);
    block.appendChild(ul);
    lists.appendChild(block);
  }

  if (lists.childNodes.length) reportBody.appendChild(lists);
  reportPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const msg =
      (data && (data.detail || data.message)) || `请求失败 (${res.status})`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

async function loadStudies() {
  const data = await api("/api/studies");
  const studies = (data.studies || []).filter((s) => s.ready);
  studySelect.innerHTML = "";
  if (!studies.length) {
    studySelect.innerHTML = `<option value="">暂无可用研究</option>`;
    startBtn.disabled = true;
    randomBtn.disabled = true;
    return;
  }
  for (const s of studies) {
    const opt = document.createElement("option");
    opt.value = s.stem;
    opt.textContent = s.label;
    studySelect.appendChild(opt);
  }
  startBtn.disabled = false;
  randomBtn.disabled = false;
  studySelect.disabled = false;
}

async function startSession(randomPersona) {
  const study = studySelect.value;
  if (!study) return;
  clearChat();
  setBusy(true);
  metaEl.textContent = randomPersona
    ? `正在随机生成人设并开局：${study}…`
    : `正在创建会话：${study}…`;
  try {
    const data = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ study, random_persona: randomPersona }),
    });
    sessionId = data.session_id;
    metaEl.textContent = `研究：${data.study} · 会话 ${data.session_id}`;
    showPersona(data.persona_text || "");
    replyForm.hidden = false;
    appendBubble("patient", data.patient_line || "（无开局台词）", data.detail);
    crcInput.focus();
  } catch (err) {
    appendBubble("error", String(err.message || err));
    metaEl.textContent = "创建失败";
    sessionId = null;
    replyForm.hidden = true;
  } finally {
    setBusy(false);
  }
}

startBtn.addEventListener("click", () => startSession(false));
randomBtn.addEventListener("click", () => startSession(true));

replyForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!sessionId) return;
  const message = crcInput.value.trim();
  if (!message) return;

  appendBubble("crc", message);
  crcInput.value = "";
  setBusy(true);
  try {
    const data = await api(`/api/sessions/${sessionId}/reply`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    appendBubble("patient", data.patient_line || "（无台词）", data.detail);
    if (data.ended) {
      const reason = data.end_reason || data.action || "会话结束";
      appendBubble("system", `对话结束：${reason}`);
      replyForm.hidden = true;
      metaEl.textContent = `${metaEl.textContent} · 已结束 · 正在生成评分…`;
      if (data.evaluation) {
        renderReport(data.evaluation);
        metaEl.textContent = metaEl.textContent.replace(
          " · 正在生成评分…",
          " · 评分完成",
        );
      } else {
        appendBubble("system", "正在自动评分…");
        try {
          const evalData = await api(`/api/sessions/${sessionId}/evaluate`, {
            method: "POST",
            body: "{}",
          });
          renderReport(evalData.evaluation);
          metaEl.textContent = metaEl.textContent.replace(
            " · 正在生成评分…",
            " · 评分完成",
          );
        } catch (evalErr) {
          appendBubble("error", `自动评分失败：${evalErr.message || evalErr}`);
        }
      }
    }
  } catch (err) {
    appendBubble("error", String(err.message || err));
  } finally {
    setBusy(false);
    if (!replyForm.hidden) crcInput.focus();
  }
});

retryEvalBtn.addEventListener("click", async () => {
  if (!sessionId) return;
  setBusy(true);
  try {
    const data = await api(`/api/sessions/${sessionId}/evaluate`, {
      method: "POST",
      body: "{}",
    });
    renderReport(data.evaluation);
  } catch (err) {
    appendBubble("error", `重新评分失败：${err.message || err}`);
  } finally {
    setBusy(false);
  }
});

loadStudies().catch((err) => {
  studySelect.innerHTML = `<option value="">加载失败</option>`;
  metaEl.textContent = String(err.message || err);
});
