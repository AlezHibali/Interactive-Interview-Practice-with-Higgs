const ctx = document.getElementById("scoreChart").getContext("2d");
const history = JSON.parse(localStorage.getItem("sessions") || "[]");
const scores = history.map(h => h.score);
const labels = history.map((h, i) => `Session ${i + 1}`);

new Chart(ctx, {
  type: "line",
  data: {
    labels,
    datasets: [{
      label: "Interview Scores",
      data: scores,
      fill: false,
      borderColor: "rgb(75, 192, 192)",
      tension: 0.1
    }]
  },
  options: { scales: { y: { beginAtZero: true, max: 100 } } }
});

const list = document.getElementById("sessionHistory");
if (history.length === 0) {
  list.innerHTML = `<p class='text-muted'>No sessions yet. Start one above!</p>`;
} else {
  history.forEach((s, i) => {
    const item = document.createElement("div");
    item.className = "list-group-item";
    item.innerHTML = `
      <div class="d-flex justify-content-between">
        <div>
          <strong>Session ${i + 1}</strong> - ${new Date(s.timestamp).toLocaleString()}
        </div>
        <div>
          <span class="badge bg-success">${s.score}/100</span>
        </div>
      </div>
    `;
    list.appendChild(item);
  });
}
