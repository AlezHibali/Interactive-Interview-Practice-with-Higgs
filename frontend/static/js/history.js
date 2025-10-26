// history.js
document.addEventListener("DOMContentLoaded", () => {
  const sessionListDiv = document.getElementById("sessionList");
  const modalDetail = document.getElementById("sessionDetail");

  // Load sessions from localStorage
  const sessions = JSON.parse(localStorage.getItem("interviewSessions") || "[]");

  if (sessions.length === 0) {
    sessionListDiv.innerHTML = `<div class="text-muted text-center py-4">No sessions recorded yet. Try a practice session!</div>`;
    return;
  }

  // Populate list
  sessions.forEach((s, idx) => {
    const item = document.createElement("button");
    item.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center";
    item.setAttribute("data-bs-toggle", "modal");
    item.setAttribute("data-bs-target", "#sessionModal");
    item.innerHTML = `
      <div>
        <strong>Session ${idx + 1}</strong><br>
        <small class="text-muted">${s.date || "Unknown date"}</small>
      </div>
      <span class="badge bg-primary rounded-pill">${s.score ?? "N/A"}</span>
    `;
    item.addEventListener("click", () => showSessionDetails(s));
    sessionListDiv.appendChild(item);
  });

  // Draw chart
  const ctx = document.getElementById("scoreChart");
  const scores = sessions.map(s => s.score || 0);
  const labels = sessions.map((_, i) => `S${i + 1}`);

  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Interview Score",
        data: scores,
        borderColor: "#007bff",
        tension: 0.3,
        fill: false,
        pointBackgroundColor: "#007bff"
      }]
    },
    options: {
      scales: {
        y: { beginAtZero: true, max: 100, title: { display: true, text: "Score" } },
        x: { title: { display: true, text: "Session" } }
      },
      plugins: { legend: { display: false } }
    }
  });

  // Show session details in modal
  function showSessionDetails(session) {
    let html = `<p><strong>Date:</strong> ${session.date || "Unknown"}</p>`;
    html += `<p><strong>Score:</strong> ${session.score ?? "N/A"}</p><hr>`;
    if (session.questions) {
      session.questions.forEach((q, i) => {
        html += `
          <div class="mb-3">
            <h6 class="fw-bold text-primary">Q${i + 1}: ${q.question}</h6>
            <p><strong>Transcript:</strong> ${q.transcript || "—"}</p>
            <p><strong>Analysis:</strong> ${q.analysis || "—"}</p>
          </div>
          <hr>
        `;
      });
    }
    modalDetail.innerHTML = html;
  }
});
