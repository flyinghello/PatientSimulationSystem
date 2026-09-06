const studySelect = document.getElementById("studySelect");
const startBtn = document.getElementById("startBtn");
const randomBtn = document.getElementById("randomBtn");
const messagesEl = document.getElementById("messages");
const metaEl = document.getElementById("meta");
const personaBar = document.getElementById("personaBar");
const voiceBar = document.getElementById("voiceBar");
const speakOpeningBtn = document.getElementById("speakOpeningBtn");
const pttBtn = document.getElementById("pttBtn");
const voiceStatus = document.getElementById("voiceStatus");
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
/** @type {string} */
let lastPatientLine = "";
/** @type {Map<number, object>} */
const detailByIndex = new Map();

/** @type {MediaStream | null} */
let micStream = null;
/** @type {AudioContext | null} */
let recCtx = null;
/** @type {ScriptProcessorNode | null} */
let processor = null;
/** @type {Float32Array[]} */
let recChunks = [];
let recording = false;
let voiceBusy = false;
/** @type {HTMLAudioElement | null} */
let playing = null;

function setBusy(busy) {
  const hasStudy = Boolean(studySelect.value);
  startBtn.disabled = busy || !hasStudy;
  randomBtn.disabled = busy || !hasStudy;
  sendBtn.disabled = busy || recording;
  crcInput.disabled = busy || recording;
  studySelect.disabled = busy;
  retryEvalBtn.disabled = busy;
  speakOpeningBtn.disabled = busy || !sessionId || recording;
  pttBtn.disabled = busy || !sessionId;
}

function setVoiceStatus(text, live = false) {
  voiceStatus.textContent = text;
  voiceStatus.classList.toggle("live", live);
  pttBtn.classList.toggle("live", live);
}

function clearChat() {
  messagesEl.innerHTML = "";
  detailByIndex.clear();
  reportPanel.hidden = true;
  reportBody.innerHTML = "";
  personaBar.hidden = true;
  personaBar.textContent = "";
  voiceBar.hidden = true;
  lastPatientLine = "";
  stopPlayback();
}

function stopPlayback() {
  if (playing) {
    try {
      playing.pause();
    } catch {
      /* noop */
    }
    playing = null;
  }
}

function playBase64Mp3(b64) {
  if (!b64) return;
  stopPlayback();
  const url = `data:audio/mpeg;base64,${b64}`;
  const audio = new Audio(url);
  playing = audio;
  void audio.play().catch(() => {});
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

function encodeWav(floatChunks, sampleRate) {
  let length = 0;
  for (const c of floatChunks) length += c.length;
  const pcm = new Int16Array(length);
  let offset = 0;
  for (const c of floatChunks) {
    for (let i = 0; i < c.length; i++) {
      const s = Math.max(-1, Math.min(1, c[i]));
      pcm[offset++] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
  }
  const buffer = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(buffer);
  const writeStr = (o, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(o + i, str.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + pcm.length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, pcm.length * 2, true);
  let o = 44;
  for (let i = 0; i < pcm.length; i++, o += 2) {
    view.setInt16(o, pcm[i], true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

function downsampleTo16k(float32, inRate) {
  if (inRate === 16000) return float32;
  const ratio = inRate / 16000;
  const outLen = Math.floor(float32.length / ratio);
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    out[i] = float32[Math.floor(i * ratio)];
  }
  return out;
}

async function startRecording() {
  if (recording || voiceBusy || !sessionId) return;
  stopPlayback();
  recChunks = [];
  micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  recCtx = new AudioContext();
  const source = recCtx.createMediaStreamSource(micStream);
  processor = recCtx.createScriptProcessor(4096, 1, 1);
  processor.onaudioprocess = (e) => {
    if (!recording) return;
    const input = e.inputBuffer.getChannelData(0);
    recChunks.push(new Float32Array(input));
  };
  source.connect(processor);
  processor.connect(recCtx.destination);
  recording = true;
  setVoiceStatus("录音中…松手发送", true);
  setBusy(false);
  pttBtn.textContent = "松开结束";
}

async function stopRecordingAndSend() {
  if (!recording) return;
  recording = false;
  pttBtn.textContent = "按住说话";
  setVoiceStatus("识别与回复中…");

  const rate = recCtx ? recCtx.sampleRate : 48000;
  try {
    if (processor) {
      processor.disconnect();
      processor.onaudioprocess = null;
    }
  } catch {
    /* noop */
  }
  processor = null;
  if (recCtx) {
    try {
      await recCtx.close();
    } catch {
      /* noop */
    }
  }
  recCtx = null;
  if (micStream) {
    micStream.getTracks().forEach((t) => t.stop());
    micStream = null;
  }

  if (!recChunks.length) {
    setVoiceStatus("未采到音频");
    return;
  }

  let mergedLen = 0;
  for (const c of recChunks) mergedLen += c.length;
  const merged = new Float32Array(mergedLen);
  let off = 0;
  for (const c of recChunks) {
    merged.set(c, off);
    off += c.length;
  }
  const pcm16k = downsampleTo16k(merged, rate);
  const blob = encodeWav([pcm16k], 16000);
  recChunks = [];

  voiceBusy = true;
  setBusy(true);
  try {
    const form = new FormData();
    form.append("audio", blob, "speech.wav");
    const res = await fetch(`/api/sessions/${sessionId}/voice/turn`, {
      method: "POST",
      body: form,
    });
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok) {
      const msg =
        (data && (data.detail || data.message)) || `语音回合失败 (${res.status})`;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }

    appendBubble("crc", data.crc_text || "（未识别）");
    lastPatientLine = data.patient_line || "";
    appendBubble("patient", lastPatientLine || "（无台词）", data.detail);
    if (data.audio_base64) {
      playBase64Mp3(data.audio_base64);
    } else if (data.tts_error) {
      appendBubble("system", `患者文本已出，但 TTS 失败：${data.tts_error}`);
    }
    setVoiceStatus("火山语音待命");

    if (data.ended) {
      const reason = data.end_reason || data.action || "会话结束";
      appendBubble("system", `对话结束：${reason}`);
      replyForm.hidden = true;
      voiceBar.hidden = true;
      if (data.evaluation) renderReport(data.evaluation);
      metaEl.textContent = `${metaEl.textContent} · 已结束`;
    }
  } catch (err) {
    appendBubble("error", String(err.message || err));
    setVoiceStatus("失败，可重试");
  } finally {
    voiceBusy = false;
    setBusy(false);
  }
}

function bindPtt() {
  const start = (e) => {
    e.preventDefault();
    void startRecording().catch((err) => {
      appendBubble("error", `无法开麦：${err.message || err}`);
      setVoiceStatus("麦克风失败");
    });
  };
  const stop = (e) => {
    e.preventDefault();
    void stopRecordingAndSend();
  };
  pttBtn.addEventListener("mousedown", start);
  pttBtn.addEventListener("mouseup", stop);
  pttBtn.addEventListener("mouseleave", () => {
    if (recording) void stopRecordingAndSend();
  });
  pttBtn.addEventListener("touchstart", start, { passive: false });
  pttBtn.addEventListener("touchend", stop);
}

speakOpeningBtn.addEventListener("click", async () => {
  if (!lastPatientLine || voiceBusy) return;
  voiceBusy = true;
  setBusy(true);
  setVoiceStatus("朗读开场…");
  try {
    const data = await api("/api/tts", {
      method: "POST",
      body: JSON.stringify({
        text: lastPatientLine,
        session_id: sessionId || undefined,
      }),
    });
    playBase64Mp3(data.audio_base64);
    setVoiceStatus("火山语音待命");
  } catch (err) {
    appendBubble("error", `朗读失败：${err.message || err}`);
    setVoiceStatus("朗读失败");
  } finally {
    voiceBusy = false;
    setBusy(false);
  }
});

bindPtt();

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
    voiceBar.hidden = false;
    setVoiceStatus("火山语音待命");
    lastPatientLine = data.patient_line || "";
    appendBubble("patient", lastPatientLine || "（无开局台词）", data.detail);
    crcInput.focus();
  } catch (err) {
    appendBubble("error", String(err.message || err));
    metaEl.textContent = "创建失败";
    sessionId = null;
    replyForm.hidden = true;
    voiceBar.hidden = true;
  } finally {
    setBusy(false);
  }
}

startBtn.addEventListener("click", () => startSession(false));
randomBtn.addEventListener("click", () => startSession(true));

replyForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!sessionId || recording || voiceBusy) return;
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
    lastPatientLine = data.patient_line || "";
    appendBubble("patient", lastPatientLine || "（无台词）", data.detail);
    // 文字回合也可用火山朗读
    try {
      const tts = await api("/api/tts", {
        method: "POST",
        body: JSON.stringify({
          text: lastPatientLine,
          session_id: sessionId,
          emotion: data.tts_emotion || undefined,
          emotion_scale: data.tts_emotion_scale || undefined,
        }),
      });
      if (tts.audio_base64) playBase64Mp3(tts.audio_base64);
    } catch {
      /* 朗读失败不阻断文字对话 */
    }
    if (data.ended) {
      const reason = data.end_reason || data.action || "会话结束";
      appendBubble("system", `对话结束：${reason}`);
      replyForm.hidden = true;
      voiceBar.hidden = true;
      metaEl.textContent = `${metaEl.textContent} · 已结束 · 正在生成评分…`;
      if (data.evaluation) {
        renderReport(data.evaluation);
        metaEl.textContent = metaEl.textContent.replace(
          " · 正在生成评分…",
          " · 评分完成",
        );
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
