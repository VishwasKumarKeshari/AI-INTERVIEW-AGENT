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
  stopRequested: false,
  camStream: null,
  camVideoLoopRaf: null,
  faceMesh: null,
  faceMeshBusy: false,
  gazeMonitorTimer: null,
  gazeLastResultAt: 0,
  gazeIsOnScreen: true,
  gazeAwaySince: 0,
  lastGazeWarningAt: 0,
  gazeWarnings: 0,
  maxGazeWarnings: 5,
  interviewLocked: false,
  codingSubmitting: false,
};

const PREP_SECONDS = 10;
const RECORD_SECONDS = 60;
const CODING_SECONDS = 10 * 60;

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
  gazeStatus: document.getElementById("gazeStatus"),
  gazeVideo: document.getElementById("gazeVideo"),
  gazeWarningBadge: document.getElementById("gazeWarningBadge"),
  timer: document.getElementById("timer"),
  stopAnswerBtn: document.getElementById("stopAnswerBtn"),
  answerCard: document.querySelector(".answer-card"),
  workspace: document.querySelector(".workspace"),
  codingCard: document.getElementById("codingRoundCard"),
  codingTimer: document.getElementById("codingTimer"),
  audioModeSection: document.getElementById("audioModeSection"),
  codingModeSection: document.getElementById("codingModeSection"),
  codingAnswerInput: document.getElementById("codingAnswerInput"),
  submitCodingBtn: document.getElementById("submitCodingBtn"),
  reportBtn: document.getElementById("reportBtn"),
  reportOutput: document.getElementById("reportOutput"),
  downloadAnswersBtn: document.getElementById("downloadAnswersBtn"),
  downloadReportBtn: document.getElementById("downloadReportBtn"),
};

const ensureCodingUI = () => {
  if (el.codingCard && el.codingAnswerInput && el.submitCodingBtn) return;
  if (!el.workspace) return;

  let codingCard = document.getElementById("codingRoundCard");
  if (!codingCard) {
    codingCard = document.createElement("div");
    codingCard.id = "codingRoundCard";
    codingCard.className = "card coding-card";
    codingCard.setAttribute("hidden", "");
    codingCard.style.display = "none";
    codingCard.innerHTML = `
      <div class="card-header">
        <h3>Coding Round</h3>
        <span id="codingTimer" class="timer">10:00</span>
      </div>
      <label class="label" for="codingAnswerInput">Write your coding solution</label>
      <textarea id="codingAnswerInput" placeholder="Write code and explain time/space complexity..."></textarea>
      <div class="coding-actions">
        <button id="submitCodingBtn" class="primary" disabled>Submit Coding Answer</button>
        <p class="muted">Auto-submit after 10 minutes if not submitted.</p>
      </div>
    `;
    const reportCard = el.workspace.querySelector(".report-card");
    if (reportCard) {
      el.workspace.insertBefore(codingCard, reportCard);
    } else {
      el.workspace.appendChild(codingCard);
    }
  }

  el.codingCard = codingCard;
  el.codingTimer = document.getElementById("codingTimer");
  el.codingAnswerInput = document.getElementById("codingAnswerInput");
  el.submitCodingBtn = document.getElementById("submitCodingBtn");
};

const setStopBtnState = (disabled) => {
  if (el.stopAnswerBtn) {
    el.stopAnswerBtn.disabled = disabled;
  }
};

const isCodingQuestion = (question = state.question) => {
  if (!question) return false;
  const qid = String(question.id || "").toLowerCase();
  const qrole = String(question.role || "").toLowerCase();
  const qtext = String(question.question || "").toLowerCase();
  return (
    qrole === "coding_round" ||
    qid.startsWith("coding_") ||
    qid === "coding_round_1" ||
    qtext.includes("write working code")
  );
};

const setCodingSubmitBtnState = (disabled) => {
  if (el.submitCodingBtn) {
    el.submitCodingBtn.disabled = disabled;
  }
};

const formatSeconds = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
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

const setGazeStatus = (message, type = "info") => {
  if (!el.gazeStatus) return;
  el.gazeStatus.textContent = message;
  el.gazeStatus.style.color =
    type === "error" ? "#ff8b8b" : type === "success" ? "#6fffe9" : type === "warn" ? "#ffb86b" : "#b8c1e3";
};

const updateGazeWarningBadge = () => {
  if (!el.gazeWarningBadge) return;
  el.gazeWarningBadge.textContent = `Warnings: ${state.gazeWarnings}/${state.maxGazeWarnings}`;
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

const setAnswerModeUI = (codingMode) => {
  ensureCodingUI();
  if (el.answerCard) {
    if (codingMode) {
      el.answerCard.setAttribute("hidden", "");
      el.answerCard.style.display = "none";
    } else {
      el.answerCard.removeAttribute("hidden");
      el.answerCard.style.display = "";
    }
  }
  if (el.codingCard) {
    if (codingMode) {
      el.codingCard.removeAttribute("hidden");
      el.codingCard.style.display = "";
    } else {
      el.codingCard.setAttribute("hidden", "");
      el.codingCard.style.display = "none";
    }
  }

  setStopBtnState(codingMode || !state.question);
  setCodingSubmitBtnState(!codingMode || !state.question || state.codingSubmitting);
  if (!codingMode && el.codingAnswerInput) {
    el.codingAnswerInput.value = "";
  }
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

const distance2D = (a, b) => {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
};

const averagePoint = (points) => {
  const total = points.reduce(
    (acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }),
    { x: 0, y: 0 }
  );
  return { x: total.x / points.length, y: total.y / points.length };
};

const isLookingAtScreen = (landmarks) => {
  if (!landmarks || landmarks.length < 477) return false;

  const leftOuter = landmarks[33];
  const leftInner = landmarks[133];
  const rightInner = landmarks[362];
  const rightOuter = landmarks[263];

  const leftUpper = landmarks[159];
  const leftLower = landmarks[145];
  const rightUpper = landmarks[386];
  const rightLower = landmarks[374];

  const leftIris = averagePoint([landmarks[468], landmarks[469], landmarks[470], landmarks[471]]);
  const rightIris = averagePoint([landmarks[473], landmarks[474], landmarks[475], landmarks[476]]);

  const leftEyeWidth = Math.max(distance2D(leftOuter, leftInner), 0.0001);
  const rightEyeWidth = Math.max(distance2D(rightOuter, rightInner), 0.0001);
  const leftEyeOpen = distance2D(leftUpper, leftLower) / leftEyeWidth;
  const rightEyeOpen = distance2D(rightUpper, rightLower) / rightEyeWidth;

  const leftRatio = (leftIris.x - leftOuter.x) / Math.max(leftInner.x - leftOuter.x, 0.0001);
  const rightRatio = (rightIris.x - rightInner.x) / Math.max(rightOuter.x - rightInner.x, 0.0001);

  const eyesOpenEnough = leftEyeOpen > 0.12 && rightEyeOpen > 0.12;
  const gazeCentered = leftRatio > 0.2 && leftRatio < 0.8 && rightRatio > 0.2 && rightRatio < 0.8;
  return eyesOpenEnough && gazeCentered;
};

const stopCameraMonitoring = () => {
  if (state.camVideoLoopRaf) {
    cancelAnimationFrame(state.camVideoLoopRaf);
    state.camVideoLoopRaf = null;
  }
  if (state.gazeMonitorTimer) {
    clearInterval(state.gazeMonitorTimer);
    state.gazeMonitorTimer = null;
  }
  if (state.camStream) {
    state.camStream.getTracks().forEach((track) => track.stop());
    state.camStream = null;
  }
  if (el.gazeVideo) {
    el.gazeVideo.srcObject = null;
  }
  state.faceMeshBusy = false;
  state.gazeAwaySince = 0;
  state.gazeLastResultAt = 0;
};

const finalizeInterviewDueToProctoring = () => {
  if (state.interviewLocked) return;
  state.interviewLocked = true;
  clearInterval(state.timer);
  clearAutoRecordTimers();
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.audioDiscard = true;
    stopRecorderOnly();
  }
  stopAndReleaseStream();
  stopCameraMonitoring();
  setQuestion(null);
  el.questionTag.textContent = "Stopped";
  el.questionText.textContent =
    "Interview stopped because camera proctoring reached 5 warnings (candidate not looking at screen).";
  setStopBtnState(true);
  toast("Interview stopped: 5 proctoring warnings reached.", "error");
  setGazeStatus("Interview stopped by proctoring policy.", "error");
};

const issueGazeWarning = () => {
  const now = Date.now();
  if (now - state.lastGazeWarningAt < 4000) return;
  state.lastGazeWarningAt = now;
  state.gazeWarnings += 1;
  updateGazeWarningBadge();
  toast(
    `Warning ${state.gazeWarnings}/${state.maxGazeWarnings}: keep your eyes on the screen.`,
    "error"
  );
  setGazeStatus("Warning issued: you are not looking at the screen.", "warn");
  if (state.gazeWarnings >= state.maxGazeWarnings) {
    finalizeInterviewDueToProctoring();
  }
};

const startGazeViolationMonitor = () => {
  if (state.gazeMonitorTimer) {
    clearInterval(state.gazeMonitorTimer);
  }
  state.gazeMonitorTimer = setInterval(() => {
    if (!state.sessionId || state.interviewLocked) return;

    const now = Date.now();
    const staleSignal = now - state.gazeLastResultAt > 2500;
    const hasAttention = !staleSignal && state.gazeIsOnScreen;

    if (hasAttention) {
      state.gazeAwaySince = 0;
      setGazeStatus("Camera active: candidate is looking at the screen.", "success");
      return;
    }

    if (!state.gazeAwaySince) {
      state.gazeAwaySince = now;
      setGazeStatus("Look back at the screen to avoid warning.", "warn");
      return;
    }

    if (now - state.gazeAwaySince >= 2500) {
      state.gazeAwaySince = now;
      issueGazeWarning();
    }
  }, 1000);
};

const initCameraAndGazeMonitor = async () => {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setGazeStatus("Browser does not support camera access.", "error");
    return false;
  }
  if (typeof FaceMesh === "undefined") {
    setGazeStatus("Face tracking module failed to load.", "error");
    return false;
  }

  try {
    setGazeStatus("Requesting camera access...", "info");
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    });
    state.camStream = stream;
    if (el.gazeVideo) {
      el.gazeVideo.srcObject = stream;
      await el.gazeVideo.play();
    }

    if (!state.faceMesh) {
      state.faceMesh = new FaceMesh({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
      });
      state.faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.6,
        minTrackingConfidence: 0.6,
      });
      state.faceMesh.onResults((results) => {
        state.gazeLastResultAt = Date.now();
        const landmarks = results.multiFaceLandmarks?.[0];
        state.gazeIsOnScreen = Boolean(landmarks && isLookingAtScreen(landmarks));
      });
    }

    const processFrame = async () => {
      if (!el.gazeVideo || !state.camStream) return;
      if (!state.faceMeshBusy && el.gazeVideo.readyState >= 2) {
        try {
          state.faceMeshBusy = true;
          await state.faceMesh.send({ image: el.gazeVideo });
        } catch (_err) {
          state.gazeIsOnScreen = false;
        } finally {
          state.faceMeshBusy = false;
        }
      }
      state.camVideoLoopRaf = requestAnimationFrame(processFrame);
    };
    processFrame();

    state.gazeIsOnScreen = true;
    state.gazeAwaySince = 0;
    state.lastGazeWarningAt = 0;
    setGazeStatus("Camera active: gaze monitor running.", "success");
    startGazeViolationMonitor();
    return true;
  } catch (err) {
    setGazeStatus(`Camera access denied: ${err.message}`, "error");
    stopCameraMonitoring();
    return false;
  }
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

const uploadAudioAnswer = async (blob, options = {}) => {
  if (!state.sessionId || !state.question) return;
  setStopBtnState(true);
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
    await handlePostAnswerFlow(data, options);
  } catch (err) {
    setAudioStatus(`Audio upload failed: ${err.message}`, "error");
    setStopBtnState(false);
  }
};

const startRecording = async () => {
  if (!state.question || state.interviewLocked) return;
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
      const shouldGoNextImmediately = state.stopRequested;
      state.stopRequested = false;
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
        if (shouldGoNextImmediately) {
          submitStoppedAnswerWithoutAudio();
        }
        return;
      }
      if (el.audioPlayback) {
        el.audioPlayback.src = URL.createObjectURL(blob);
        el.audioPlayback.hidden = false;
      }
      uploadAudioAnswer(blob, { immediateNext: shouldGoNextImmediately });
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

const submitCodingAnswer = async ({ timedOut = false } = {}) => {
  if (!state.question || !state.sessionId || state.interviewLocked || !isCodingQuestion()) return;
  if (state.codingSubmitting) return;

  const typed = (el.codingAnswerInput?.value || "").trim();
  const answerText = typed || (timedOut ? "(No answer - time expired)" : "");
  if (!answerText) {
    toast("Write your coding answer before submitting.", "error");
    return;
  }

  state.codingSubmitting = true;
  setCodingSubmitBtnState(true);
  try {
    const payload = {
      question_id: state.question.id,
      answer_text: answerText,
    };
    const data = await apiFetch(`/interview/${state.sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await handlePostAnswerFlow(data, { immediateNext: true });
  } catch (err) {
    toast(`Coding submit failed: ${err.message}`, "error");
  } finally {
    state.codingSubmitting = false;
    setCodingSubmitBtnState(false);
  }
};

const startTimer = () => {
  if (state.interviewLocked) return;
  clearInterval(state.timer);
  const codingMode = isCodingQuestion();
  state.timerRemaining = codingMode ? CODING_SECONDS : PREP_SECONDS + RECORD_SECONDS;
  if (el.timer) {
    el.timer.textContent = formatSeconds(state.timerRemaining);
  }
  if (el.codingTimer) {
    el.codingTimer.textContent = formatSeconds(state.timerRemaining);
  }
  state.timer = setInterval(() => {
    state.timerRemaining -= 1;
    if (el.timer) {
      el.timer.textContent = formatSeconds(state.timerRemaining);
    }
    if (el.codingTimer) {
      el.codingTimer.textContent = formatSeconds(state.timerRemaining);
    }
    if (state.timerRemaining <= 0) {
      clearInterval(state.timer);
      if (codingMode) {
        if (!state.timerExpiredSent) {
          state.timerExpiredSent = true;
          submitCodingAnswer({ timedOut: true });
        }
        return;
      }
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
  if (state.interviewLocked && question) {
    return;
  }
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
  state.stopRequested = false;
  state.timerExpiredSent = false;
  state.codingSubmitting = false;
  el.questionText.textContent = question ? question.question : "No question available.";
  el.questionTag.textContent = question ? (isCodingQuestion(question) ? "Coding Round" : "Live") : "Waiting";
  el.questionRole.textContent = `Role: ${question ? question.role : "--"}`;
  el.questionDifficulty.textContent = `Difficulty: ${question ? question.difficulty : "--"}`;
  resetAudioUI();
  setAnswerModeUI(isCodingQuestion(question));
  if (question) {
    if (isCodingQuestion(question)) {
      clearAutoRecordTimers();
      if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
        state.audioDiscard = true;
        stopRecorderOnly();
      }
      if (el.codingAnswerInput) {
        el.codingAnswerInput.value = "";
        el.codingAnswerInput.focus();
      }
      startTimer();
      speakText("Coding round started. You have ten minutes. Submit when ready.");
      toast("Coding round started: 10 minutes timer is running.", "info");
      return;
    }
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
    `Technical responses are spoken with 60 seconds each, followed by a 10-minute coding round. ` +
    `We'll begin in a moment.`;
  el.questionText.textContent = "Interview starting... The interviewer is introducing the session.";
  el.questionTag.textContent = "Intro";
  el.questionRole.textContent = "Role: --";
  el.questionDifficulty.textContent = "Difficulty: --";
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
    return false;
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
    return true;
  } catch (err) {
    setAudioStatus(`Mic access denied: ${err.message}`, "error");
    return false;
  }
};

const handlePostAnswerFlow = async (data, options = {}) => {
  if (state.interviewLocked) return;
  if (!data.has_more_questions) {
    toast("Interview completed. Generate the report.", "success");
    stopAndReleaseStream();
    stopCameraMonitoring();
    setStopBtnState(true);
    setCodingSubmitBtnState(true);
    return;
  }
  const immediateNext = Boolean(options.immediateNext);
  toast("Answer submitted. Loading next question...", "success");
  setStopBtnState(true);
  if (!immediateNext) {
    clearInterval(state.timer);
  }
  await loadNextQuestion();
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
    state.interviewLocked = false;
    state.gazeWarnings = 0;
    state.gazeAwaySince = 0;
    state.lastGazeWarningAt = 0;
    updateGazeWarningBadge();
    setGazeStatus("Camera check idle.", "info");

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
    setStopBtnState(true);
    toast(`Interview started. ${data.total_questions} questions queued.`, "success");
    const micReady = await initMicStream();
    const camReady = await initCameraAndGazeMonitor();
    if (!micReady || !camReady) {
      await apiFetch(`/interview/${state.sessionId}`, { method: "DELETE" });
      state.sessionId = null;
      el.endBtn.disabled = true;
      el.reportBtn.disabled = true;
      stopAndReleaseStream();
      stopCameraMonitoring();
      setQuestion(null);
      toast("Interview cancelled: microphone and camera access are required.", "error");
      return;
    }
    await startIntro();
  } catch (err) {
    toast(`Start failed: ${err.message}`, "error");
  }
});

const loadNextQuestion = async () => {
  if (!state.sessionId || state.interviewLocked) return;
  try {
    const data = await apiFetch(`/interview/${state.sessionId}/question`);
    if (!data) {
      setQuestion(null);
      toast("Interview completed.", "success");
      stopAndReleaseStream();
      stopCameraMonitoring();
      return;
    }
    setQuestion(data);
  } catch (err) {
    toast(`Question fetch failed: ${err.message}`, "error");
  }
};

const submitTimeoutAnswer = async () => {
  if (!state.question || !state.sessionId || state.interviewLocked) return;
  if (isCodingQuestion()) {
    await submitCodingAnswer({ timedOut: true });
    return;
  }
  setStopBtnState(true);
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
    setStopBtnState(false);
  }
};

const submitStoppedAnswerWithoutAudio = async () => {
  if (!state.question || !state.sessionId || state.interviewLocked) return;
  if (isCodingQuestion()) return;
  setStopBtnState(true);
  try {
    const payload = {
      question_id: state.question.id,
      answer_text: "(Candidate stopped early)",
    };
    const data = await apiFetch(`/interview/${state.sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await handlePostAnswerFlow(data, { immediateNext: true });
  } catch (err) {
    toast(`Stop submit failed: ${err.message}`, "error");
    setStopBtnState(false);
  }
};

if (el.stopAnswerBtn) {
  el.stopAnswerBtn.addEventListener("click", async () => {
    if (!state.sessionId || !state.question || state.interviewLocked) return;
    if (isCodingQuestion()) return;
    if (state.stopRequested) return;
    state.stopRequested = true;
    clearInterval(state.timer);
    clearAutoRecordTimers();
    if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
      setAudioStatus("Stopping and submitting answer...", "info");
      stopRecorderOnly();
      return;
    }
    await submitStoppedAnswerWithoutAudio();
    state.stopRequested = false;
  });
}

const bindCodingSubmitHandler = () => {
  ensureCodingUI();
  if (!el.submitCodingBtn || el.submitCodingBtn.dataset.bound === "1") return;
  el.submitCodingBtn.addEventListener("click", async () => {
    if (!state.sessionId || !state.question || state.interviewLocked) return;
    if (!isCodingQuestion()) return;
    clearInterval(state.timer);
    await submitCodingAnswer({ timedOut: false });
  });
  el.submitCodingBtn.dataset.bound = "1";
};

el.reportBtn.addEventListener("click", async () => {
  if (!state.sessionId) return;
  try {
    const data = await apiFetch(`/interview/${state.sessionId}/report`);
    const roles = data.roles || [];
    const lines = [];
    if (typeof data.total_raw_score === "number" && typeof data.max_possible === "number") {
      lines.push(`Overall Score: ${data.total_raw_score}/${data.max_possible}`);
      lines.push("");
    }
    roles.forEach((role) => {
      lines.push(`${role.role_name}: ${role.total_raw_score}/${role.max_possible}`);
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
    stopCameraMonitoring();
    resetAudioUI();
    setGazeStatus("Camera check idle.", "info");
    state.gazeWarnings = 0;
    updateGazeWarningBadge();
    state.interviewLocked = false;
    state.codingSubmitting = false;
    setStopBtnState(true);
    setCodingSubmitBtnState(true);
    setQuestion(null);
  } catch (err) {
    toast(`End failed: ${err.message}`, "error");
  }
});

resetAudioUI();
ensureCodingUI();
bindCodingSubmitHandler();
setAnswerModeUI(false);
setCodingSubmitBtnState(true);
updateGazeWarningBadge();
setGazeStatus("Camera check idle.", "info");
