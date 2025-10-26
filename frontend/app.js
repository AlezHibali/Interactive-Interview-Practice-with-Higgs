// ===================== Variables =====================
let mediaRecorder = null;
let recordedChunks = [];

const btnQuestion = document.getElementById("btn-question");
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const roleInput = document.getElementById("role");
const voiceSelect = document.getElementById("voice-select");

const qTextDiv = document.getElementById("question_text");
const transcriptPre = document.getElementById("transcript");
const analysisPre = document.getElementById("analysis");
const summaryPre = document.getElementById("summary");

// ===================== Generate Question + TTS =====================
btnQuestion.onclick = async () => {
  btnQuestion.disabled = true;
  const role = roleInput.value.trim();
  try {
    const resp = await fetch("/question", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({role})
    });
    const j = await resp.json();
    if (j.error) { alert(j.error); return; }
    const q = j.question;
    qTextDiv.textContent = q;

    // Call TTS
    const ttsResp = await fetch("/tts", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({text: q, voice: voiceSelect.value})
    });
    const blob = await ttsResp.blob();
    const url = URL.createObjectURL(blob);
    const a = new Audio(url);
    a.play();
  } catch (e) {
    console.error(e);
    alert("Error fetching question or TTS. See console.");
  } finally {
    btnQuestion.disabled = false;
  }
};

// ===================== Recording =====================
btnStart.onclick = async () => {
  btnStart.disabled = true;
  btnStop.disabled = false;
  recordedChunks = [];
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    };
    mediaRecorder.start();
  } catch (e) {
    console.error(e);
    alert("Could not start recording: " + e.message);
    btnStart.disabled = false;
    btnStop.disabled = true;
  }
};

btnStop.onclick = async () => {
  btnStop.disabled = true;
  btnStart.disabled = false;
  if (!mediaRecorder) return;
  mediaRecorder.stop();
  mediaRecorder.onstop = async () => {
    const blob = new Blob(recordedChunks, {type: "audio/webm"});
    const fd = new FormData();
    fd.append("file", blob, "answer.webm");

    try {
      const uploadResp = await fetch("/upload_answer", {method: "POST", body: fd});
      const j = await uploadResp.json();
      if (j.error) {
        analysisPre.textContent = "Error: " + j.error;
        return;
      }
      transcriptPre.textContent = j.transcript || "—";
      analysisPre.textContent = JSON.stringify(j.analysis, null, 2);

      // request summary
      const sumResp = await fetch("/summary", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({transcript: j.transcript, audio_meta: j.analysis})
      });
      const sumJ = await sumResp.json();
      if (sumJ.error) {
        summaryPre.textContent = "Error: " + sumJ.error;
      } else {
        summaryPre.textContent = sumJ.summary;
      }
    } catch (e) {
      console.error(e);
      alert("Upload or summary error. See console.");
    }
  };
};
