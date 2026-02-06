const state = {
  apiBase: "http://localhost:8000",
  sessionId: null,
  roles: [],
  question: null,
  timer: null,
  timerRemaining: 60,
  mediaRecorder: null,
  audioChunks: [],
  micStream: null,
  audioMimeType: null,
  audioDiscard: false,
  timerExpiredSent: false,
  introTimer: null,
  autoRecordDelayTimer: null,
  autoRecordStopTimer: null,
  micReady: false,
  reportData: null,
  audioContext: null,
  analyser: null,
  meterRaf: null,
};

const PREP_SECONDS = 10;
const RECORD_SECONDS = 60;

const el = {
  resumeFile: document.getElementById("resumeFile"),
  analyzeBtn: document.getElementById("analyzeBtn"),
  resumeMessage: document.getElementById("resumeMessage"),
  rolesList: document.getElementById("rolesList"),
  startBtn: document.getElementById("startBtn"),
  endBtn: document.getElementById("endBtn"),
  sessionMessage: document.getElementById("sessionMessage"),
  questionText: document.getElementById("questionText"),
  questionTag: document.getElementById("questionTag"),
  questionRole: document.getElementById("questionRole"),
  questionDifficulty: document.getElementById("questionDifficulty"),
  audioStatus: document.getElementById("audioStatus"),
  audioPlayback: document.getElementById("audioPlayback"),
  micMeterFill: document.getElementById("micMeterFill"),
  timer: document.getElementById("timer"),
  feedbackText: document.getElementById("feedbackText"),
  scoreBadge: document.getElementById("scoreBadge"),
  reportBtn: document.getElementById("reportBtn"),
  reportOutput: document.getElementById("reportOutput"),
  downloadAnswersBtn: document.getElementById("downloadAnswersBtn"),
  downloadReportBtn: document.getElementById("downloadReportBtn"),
};

const toast = (message, type = "info") => {
  el.sessionMessage.textContent = message;
  el.sessionMessage.style.color =
    type === "error" ? "#ff8b8b" : type === "success" ? "#6fffe9" : "#b8c1e3";
};

const resumeToast = (message, type = "info") => {
  el.resumeMessage.textContent = message;
  el.resumeMessage.style.color =
    type === "error" ? "#ff8b8b" : type === "success" ? "#6fffe9" : "#b8c1e3";
};

const apiFetch = async (path, options = {}) => {
  const base = state.apiBase.replace(/\/$/, "");
  const response = await fetch(`${base}${path}`, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return null;
  return response.json();
};

const setAudioStatus = (message, type = "info") => {
  if (!el.audioStatus) return;
  el.audioStatus.textContent = message;
  el.audioStatus.style.color =
    type === "error" ? "#ff8b8b" : type === "success" ? "#6fffe9" : "#b8c1e3";
};

const getSupportedMimeType = () => {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
  ];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
};

const resetAudioUI = () => {
  if (el.audioPlayback) {
    el.audioPlayback.hidden = true;
    el.audioPlayback.src = "";
  }
  if (el.micMeterFill) {
    el.micMeterFill.style.width = "0%";
  }
  setAudioStatus("Mic idle.");
};

const resetFeedback = () => {
  el.feedbackText.textContent = "Feedback will appear here.";
  el.scoreBadge.textContent = "Score: --%";
  el.scoreBadge.classList.add("pill-muted");
};

const downloadJSON = (data, filename) => {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

const speakText = (text) => {
  if (!text || !window.speechSynthesis) return;
  const utter = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
};

const speakTextAsync = (text) =>
  new Promise((resolve) => {
    if (!text || !window.speechSynthesis) {
      resolve();
      return;
    }
    const utter = new SpeechSynthesisUtterance(text);
    utter.onend = () => resolve();
    utter.onerror = () => resolve();
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  });

const renderRoles = () => {
  if (!state.roles.length) {
    el.rolesList.classList.add("empty");
    el.rolesList.textContent = "No roles detected yet.";
    return;
  }
  el.rolesList.classList.remove("empty");
  el.rolesList.innerHTML = "";
  state.roles.forEach((role) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = `${role.name} (${(role.confidence * 100).toFixed(0)}%)`;
    el.rolesList.appendChild(chip);
  });
};

const stopAndReleaseStream = () => {
  if (state.meterRaf) {
    cancelAnimationFrame(state.meterRaf);
    state.meterRaf = null;
  }
  if (state.audioContext) {
    state.audioContext.close();
    state.audioContext = null;
  }
  if (state.micStream) {
    state.micStream.getTracks().forEach((track) => track.stop());
    state.micStream = null;
    state.micReady = false;
  }
};

const stopRecorderOnly = () => {
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
  }
};

const clearAutoRecordTimers = () => {
  if (state.autoRecordDelayTimer) {
    clearTimeout(state.autoRecordDelayTimer);
    state.autoRecordDelayTimer = null;
  }
  if (state.autoRecordStopTimer) {
    clearTimeout(state.autoRecordStopTimer);
    state.autoRecordStopTimer = null;
  }
};

const uploadAudioAnswer = async (blob) => {
  if (!state.sessionId || !state.question) return;
  const ext = blob.type.includes("ogg") ? "ogg" : "webm";
  const formData = new FormData();
  formData.append("file", blob, `answer.${ext}`);
  try {
    const data = await apiFetch(
      `/interview/${state.sessionId}/answer/audio?question_id=${encodeURIComponent(
        state.question.id
      )}`,
      {
        method: "POST",
        body: formData,
      }
    );
    await handlePostAnswerFlow(data);
  } catch (err) {
    setAudioStatus(`Audio upload failed: ${err.message}`, "error");
  }
};

const startRecording = async () => {
  if (!state.question) return;
  try {
    state.audioDiscard = false;
    state.audioChunks = [];
    state.audioMimeType = getSupportedMimeType();
    const stream = state.micStream;
    if (!stream) {
      setAudioStatus("Microphone is not ready.", "error");
      return;
    }
    const options = state.audioMimeType ? { mimeType: state.audioMimeType } : undefined;
    const recorder = new MediaRecorder(stream, options);
    state.mediaRecorder = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        state.audioChunks.push(event.data);
      }
    };
    recorder.onstop = () => {
      if (state.audioDiscard) {
        state.audioDiscard = false;
        resetAudioUI();
        return;
      }
      const blob = new Blob(state.audioChunks, {
        type: recorder.mimeType || state.audioMimeType || "audio/webm",
      });
      if (!blob.size) {
        setAudioStatus("Recorded audio was empty.", "error");
        resetAudioUI();
        return;
      }
      if (el.audioPlayback) {
        el.audioPlayback.src = URL.createObjectURL(blob);
        el.audioPlayback.hidden = false;
      }
      uploadAudioAnswer(blob);
      resetAudioUI();
    };
    recorder.start();
    setAudioStatus("Recording... speak now.", "success");
    state.autoRecordStopTimer = setTimeout(() => {
      stopRecording();
    }, RECORD_SECONDS * 1000);
  } catch (err) {
    setAudioStatus(`Mic error: ${err.message}`, "error");
  }
};

const stopRecording = () => {
  if (!state.mediaRecorder || state.mediaRecorder.state === "inactive") {
    return;
  }
  setAudioStatus("Processing recording...", "info");
  if (state.autoRecordStopTimer) {
    clearTimeout(state.autoRecordStopTimer);
    state.autoRecordStopTimer = null;
  }
  state.mediaRecorder.stop();
};

const startTimer = () => {
  clearInterval(state.timer);
  state.timerRemaining = PREP_SECONDS + RECORD_SECONDS;
  el.timer.textContent = `${state.timerRemaining}s`;
  state.timer = setInterval(() => {
    state.timerRemaining -= 1;
    el.timer.textContent = `${state.timerRemaining}s`;
    if (state.timerRemaining <= 0) {
      clearInterval(state.timer);
      if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
        return;
      }
      if (!state.timerExpiredSent) {
        state.timerExpiredSent = true;
        submitTimeoutAnswer();
      }
    }
  }, 1000);
};

const setQuestion = (question) => {
  if (state.introTimer) {
    clearTimeout(state.introTimer);
    state.introTimer = null;
  }
  clearAutoRecordTimers();
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.audioDiscard = true;
    stopRecorderOnly();
  }
  state.question = question;
  state.timerExpiredSent = false;
  el.questionText.textContent = question ? question.question : "No question available.";
  el.questionTag.textContent = question ? "Live" : "Waiting";
  el.questionRole.textContent = `Role: ${question ? question.role : "--"}`;
  el.questionDifficulty.textContent = `Difficulty: ${question ? question.difficulty : "--"}`;
  resetFeedback();
  resetAudioUI();
  if (question) {
    startTimer();
    speakText(question.question);
    setAudioStatus(`Question read. Recording starts in ${PREP_SECONDS}s...`, "info");
    state.autoRecordDelayTimer = setTimeout(() => {
      state.autoRecordDelayTimer = null;
      startRecording();
    }, PREP_SECONDS * 1000);
  }
};

const startIntro = async () => {
  const roleNames = state.roles.map((r) => r.name).join(", ");
  const introText =
    `Hello! I'm your interviewer today. ` +
    `We'll go through a quick warm-up and then technical questions for ${roleNames}. ` +
    `Please answer out loud. You have 60 seconds for each response. ` +
    `We'll begin in a moment.`;
  el.questionText.textContent = "Interview starting... The interviewer is introducing the session.";
  el.questionTag.textContent = "Intro";
  el.questionRole.textContent = "Role: --";
  el.questionDifficulty.textContent = "Difficulty: --";
  resetFeedback();
  resetAudioUI();
  speakText(introText);
  toast("Interviewer introduction in progress. Starting questions in 20 seconds...", "info");
  state.introTimer = setTimeout(async () => {
    state.introTimer = null;
    el.questionText.textContent = "Loading first question...";
    el.questionTag.textContent = "Loading";
    await loadNextQuestion();
  }, 20000);
};

const initMicStream = async () => {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setAudioStatus("Browser does not support audio recording.", "error");
    return;
  }
  try {
    setAudioStatus("Requesting microphone access...", "info");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.micStream = stream;
    state.micReady = true;
    if (!state.audioContext) {
      state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    state.analyser = state.audioContext.createAnalyser();
    const source = state.audioContext.createMediaStreamSource(stream);
    source.connect(state.analyser);
    state.analyser.fftSize = 1024;
    const data = new Uint8Array(state.analyser.fftSize);
    const updateMeter = () => {
      if (!state.analyser || !el.micMeterFill) return;
      state.analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i += 1) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / data.length);
      const percent = Math.min(100, Math.max(4, Math.round(rms * 220)));
      el.micMeterFill.style.width = `${percent}%`;
      state.meterRaf = requestAnimationFrame(updateMeter);
    };
    updateMeter();
    setAudioStatus("Microphone ready. Recording will start automatically.", "success");
  } catch (err) {
    setAudioStatus(`Mic access denied: ${err.message}`, "error");
  }
};

const renderFeedback = (payload) => {
  el.feedbackText.textContent = payload.reasoning || "No reasoning provided.";
  el.scoreBadge.textContent = "Feedback";
  el.scoreBadge.classList.remove("pill-muted");
};

const handlePostAnswerFlow = async (data) => {
  renderFeedback(data);
  if (!data.has_more_questions) {
    toast("Interview completed. Generate the report.", "success");
    stopAndReleaseStream();
    return;
  }
  toast("Answer submitted. Next question in 20 seconds...", "success");
  speakText(el.feedbackText.textContent);
  setTimeout(async () => {
    await loadNextQuestion();
  }, 20000);
};

el.analyzeBtn.addEventListener("click", async () => {
  const file = el.resumeFile.files[0];
  if (!file) {
    resumeToast("Please select a resume file.", "error");
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  resumeToast("Analyzing resume...", "info");
  try {
    const data = await apiFetch("/resume/analyze", {
      method: "POST",
      body: formData,
    });
    state.roles = data.roles || [];
    renderRoles();
    resumeToast("Roles detected. You can start the interview.", "success");
    el.startBtn.disabled = state.roles.length === 0;
  } catch (err) {
    resumeToast(`Analyze failed: ${err.message}`, "error");
  }
});

el.startBtn.addEventListener("click", async () => {
  if (!state.roles.length) {
    toast("No roles detected yet.", "error");
    return;
  }
  toast("Starting interview...", "info");
  try {
    const payload = {
      roles: state.roles.map((role) => ({
        name: role.name,
        confidence: role.confidence,
        rationale: role.rationale || "",
      })),
    };
    const data = await apiFetch("/interview/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.sessionId = data.session_id;
    el.endBtn.disabled = false;
    el.reportBtn.disabled = false;
    state.reportData = null;
    if (el.downloadReportBtn) el.downloadReportBtn.disabled = true;
    if (el.downloadAnswersBtn) el.downloadAnswersBtn.disabled = true;
    toast(`Interview started. ${data.total_questions} questions queued.`, "success");
    await initMicStream();
    await startIntro();
  } catch (err) {
    toast(`Start failed: ${err.message}`, "error");
  }
});

const loadNextQuestion = async () => {
  if (!state.sessionId) return;
  try {
    const data = await apiFetch(`/interview/${state.sessionId}/question`);
    if (!data) {
      setQuestion(null);
      toast("Interview completed.", "success");
      stopAndReleaseStream();
      return;
    }
    setQuestion(data);
  } catch (err) {
    toast(`Question fetch failed: ${err.message}`, "error");
  }
};

const submitTimeoutAnswer = async () => {
  if (!state.question || !state.sessionId) return;
  try {
    const payload = {
      question_id: state.question.id,
      answer_text: "(No answer - time expired)",
    };
    const data = await apiFetch(`/interview/${state.sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await handlePostAnswerFlow(data);
  } catch (err) {
    toast(`Timeout submit failed: ${err.message}`, "error");
  }
};

el.reportBtn.addEventListener("click", async () => {
  if (!state.sessionId) return;
  try {
    const data = await apiFetch(`/interview/${state.sessionId}/report`);
    const roles = data.roles || [];
    const lines = [];
    if (typeof data.overall_score_percent === "number") {
      lines.push(`Overall: ${data.overall_score_percent}%`);
      lines.push("");
    }
    roles.forEach((role) => {
      lines.push(`${role.role_name}: ${role.score_percent}%`);
      lines.push("");
    });
    if (data.final_summary) {
      lines.push("Summary:");
      lines.push(data.final_summary);
      lines.push("");
    }
    lines.push(`Total questions: ${data.total_questions}`);
    el.reportOutput.textContent = lines.join("\n");
    state.reportData = data;
    if (el.downloadReportBtn) el.downloadReportBtn.disabled = false;
    if (el.downloadAnswersBtn) el.downloadAnswersBtn.disabled = false;
    toast("Report generated.", "success");
  } catch (err) {
    toast(`Report failed: ${err.message}`, "error");
  }
});

if (el.downloadReportBtn) {
  el.downloadReportBtn.addEventListener("click", () => {
    if (!state.reportData) {
      toast("Generate the report first.", "error");
      return;
    }
    downloadJSON(state.reportData, "interview_report.json");
  });
}

if (el.downloadAnswersBtn) {
  el.downloadAnswersBtn.addEventListener("click", async () => {
    if (!state.sessionId) return;
    try {
      const data = await apiFetch(`/interview/${state.sessionId}/export`);
      downloadJSON(data, "interview_answers.json");
    } catch (err) {
      toast(`Download failed: ${err.message}`, "error");
    }
  });
}

el.endBtn.addEventListener("click", async () => {
  if (!state.sessionId) return;
  try {
    await apiFetch(`/interview/${state.sessionId}`, { method: "DELETE" });
    toast("Session deleted.", "success");
    state.sessionId = null;
    el.endBtn.disabled = true;
    el.reportBtn.disabled = true;
    if (el.downloadReportBtn) el.downloadReportBtn.disabled = true;
    if (el.downloadAnswersBtn) el.downloadAnswersBtn.disabled = true;
    clearAutoRecordTimers();
    stopAndReleaseStream();
    resetAudioUI();
    setQuestion(null);
  } catch (err) {
    toast(`End failed: ${err.message}`, "error");
  }
});

resetFeedback();
resetAudioUI();
