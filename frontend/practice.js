// === Global variables ===
let mediaRecorder = null;
let recordedChunks = [];
let currentQuestionIndex = 0;
let currentQuestions = [];
let questionList = [];

const btnNextQuestion = document.getElementById("btn-next-question");
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");

const qTextDiv = document.getElementById("question_text");
const transcriptPre = document.getElementById("transcript");
const analysisPre = document.getElementById("analysis");
const summaryPre = document.getElementById("overall-summary");

const progressBar = document.getElementById("progress-bar");
const speechLoading = document.getElementById("speech-loading");
const analysisLoading = document.getElementById("analysis-loading");
const questionBar = document.getElementById("question_bar");

// Retrieve role, voice, and notes from localStorage
const interviewRole = localStorage.getItem("interviewRole") || "software engineer";
const ttsVoice = localStorage.getItem("ttsVoice") || "en_woman";
const interviewNotes = localStorage.getItem("interviewNotes") || "";

// === Helpers ===
function updateProgress() {
  const percent = (currentQuestionIndex / questionList.length) * 100;
  progressBar.style.width = `${percent}%`;
}

function clearDisplay() {
  transcriptPre.textContent = "—";
  analysisPre.textContent = "—";
  summaryPre.textContent = "—";
}

function setNextButtonState(enabled) {
  btnNextQuestion.disabled = !enabled;
  btnNextQuestion.classList.toggle("btn-success", enabled);
  btnNextQuestion.classList.toggle("btn-secondary", !enabled);
}

function addQuestionToBar(index, questionText, done = false) {
  const div = document.createElement("div");
  div.className = "question-item" + (index === currentQuestionIndex ? " active" : "");
  div.textContent = `Question #${index + 1}: ${questionText}` + (done ? " ✅" : "");
  questionBar.appendChild(div);
}

// === Load questions on page load ===
document.addEventListener("DOMContentLoaded", async () => {
  const savedQuestions = localStorage.getItem("generatedQuestions");
  if (savedQuestions) {
    questionList = JSON.parse(savedQuestions);
  } else {
    await fetchQuestionsFromBackend();
  }

  if (questionList.length > 0) {
    questionBar.innerHTML = "";
    questionList.forEach((q, idx) => addQuestionToBar(idx, q.question));
    await showQuestion(currentQuestionIndex);
  }
});

// === Fetch questions from backend ===
async function fetchQuestionsFromBackend() {
  try {
    qTextDiv.textContent = "Generating interview questions...";
    speechLoading.style.display = "flex";

    const resp = await fetch("/question", {
      method: "POST",
      body: JSON.stringify({ role: interviewRole, additional_note: interviewNotes }),
      headers: { "Content-Type": "application/json" }
    });

    const data = await resp.json();
    if (!data.questions || data.questions.length === 0) {
      alert("No questions received from the server.");
      return;
    }

    questionList = data.questions;
    localStorage.setItem("generatedQuestions", JSON.stringify(questionList));
  } catch (e) {
    console.error(e);
    alert("Error loading questions.");
  } finally {
    speechLoading.style.display = "none";
  }
}

// === Show one question and play TTS ===
async function showQuestion(index) {
  if (index < 0 || index >= questionList.length) return;

  const qObj = questionList[index];
  qTextDiv.textContent = qObj.question;
  clearDisplay();

  Array.from(questionBar.children).forEach((child, i) => {
    child.classList.toggle("active", i === index);
  });

  updateProgress();

  // Play TTS
  speechLoading.style.display = "flex";
  btnStart.disabled = true;
  try {
    const ttsResp = await fetch("/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: qObj.question, voice: ttsVoice }),
    });
    const blob = await ttsResp.blob();
    const audio = new Audio(URL.createObjectURL(blob));
    audio.onended = () => {
      speechLoading.style.display = "none";
      btnStart.disabled = false;
    };
    audio.play();
  } catch (e) {
    console.error(e);
    speechLoading.style.display = "none";
    btnStart.disabled = false;
  }
}

btnNextQuestion.onclick = async () => {
  currentQuestionIndex++;
  if (currentQuestionIndex >= questionList.length) {
    updateProgress();
    alert("🎉 Interview complete! Saved session record to profile.");
    setNextButtonState(false);

    // Generate overall summary
    summaryPre.textContent = "Generating overall summary...";
    const summaryResp = await fetch("/summarize_interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questions: currentQuestions })
    });
    const summaryData = await summaryResp.json();

    const summary = summaryData.overall_summary;
    html_summary = `
      <h5>Strengths</h5>
      <p>${summary.strengths || "—"}</p>

      <h5>Weaknesses</h5>
      <p>${summary.weaknesses || "—"}</p>

      <h5>Tips</h5>
      <p>${summary.tips || "—"}</p>

      <h5>Overall Score</h5>
      <p>${summary.overall_score || "—"}</p>
    `
    summaryPre.innerHTML = html_summary;

    // === Save session ===
    const saveResp = await fetch("/save_session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        questions: currentQuestions,
        overall_summary: html_summary
      })
    });
    const saveData = await saveResp.json();
    if (saveData.status === "success") {
      console.log("Session saved:", saveData.session);
    } else {
      console.error("Failed to save session:", saveData.error);
    }

    return;
  }

  clearDisplay();
  await showQuestion(currentQuestionIndex);
};

// === Recording ===
btnStart.onclick = async () => {
  btnStart.disabled = true;
  btnStop.disabled = false;
  recordedChunks = [];
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => e.data.size > 0 && recordedChunks.push(e.data);
    mediaRecorder.start();
  } catch (e) {
    alert("Could not start recording: " + e.message);
    btnStart.disabled = false;
  }
};

btnStop.onclick = async () => {
  btnStop.disabled = true;
  if (!mediaRecorder) return;
  mediaRecorder.stop();
  mediaRecorder.onstop = async () => {
    const blob = new Blob(recordedChunks, { type: "audio/webm" });
    const fd = new FormData();
    fd.append("file", blob, "answer.webm");
    analysisLoading.style.display = "flex";

    try {
      // 1. Upload audio and get transcript + raw analysis
      const uploadResp = await fetch("/upload_answer", { method: "POST", body: fd });
      const uploadData = await uploadResp.json();
      const transcript = uploadData.transcript || "—";
      transcriptPre.textContent = transcript;

      // 2. Analyze question via LLM
      const qText = questionList[currentQuestionIndex].question;
      const analysisResp = await fetch("/analyze_question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: qText, response: transcript })
      });
      const analysisData = await analysisResp.json();
      analysisPre.innerHTML = `
<b>Content:</b> ${analysisData.analysis_content}<br>
<b>Delivery:</b> ${analysisData.analysis_delivery}<br>
<b>Score:</b> ${analysisData.score}
`.trim();

      // Store result for interview summary
      currentQuestions[currentQuestionIndex] = {
        question: qText,
        response: transcript,
        analysis_content: analysisData.analysis_content,
        analysis_delivery: analysisData.analysis_delivery,
        score: analysisData.score
      };

      // Mark question as done
      questionBar.children[currentQuestionIndex].textContent += " ✅";
      setNextButtonState(true);
    } catch (e) {
      console.error(e);
      alert("Error analyzing response.");
    } finally {
      analysisLoading.style.display = "none";
    }
  };
};
