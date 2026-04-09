const API_URL = "http://127.0.0.1:8000/api";
let distChart = null;
let classChart = null;
Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";

document.addEventListener("DOMContentLoaded", () => {
  fetchWeightsData();

  // Refresh Weights Dashboard in Real-Time (every 2.5 seconds)
  setInterval(fetchWeightsData, 2500);
});

async function fetchWeightsData() {
  try {
    const response = await fetch(`${API_URL}/model/weights`);
    const data = await response.json();
    if (data.architecture) {
      document.getElementById("arch-name").textContent = data.architecture;
      document.getElementById("arch-dim").textContent = data.input_dim;
      document.getElementById("arch-layers").textContent = data.layers;
      document.getElementById("arch-heads").textContent = data.nhead;
      document.getElementById("arch-accuracy").textContent = data.accuracy
        ? `${data.accuracy}%`
        : "--";

      const statusEl = document.getElementById("system-status-indicator");
      statusEl.innerHTML = `<span>${data.model_status}</span>`;
      statusEl.className = data.model_status.includes("Healthy")
        ? "px-3 py-1 bg-green-50 text-green-700 border border-green-200 rounded-md text-sm font-semibold flex items-center gap-2 shadow-sm"
        : "px-3 py-1 bg-red-50 text-red-700 border border-red-200 rounded-md text-sm font-semibold flex items-center gap-2 shadow-sm";

      populateTensorsTable(data.tensors);

      // Only re-draw the distribution charts if they don't exist yet,
      // to stop complete jarring UI rebuilds, or update them in-place
      drawDistChart(data.tensors);
      if (data.class_predictions_dist) {
        drawClassChart(data.class_predictions_dist);
      }
    }
  } catch (error) {
    console.error("Error fetching", error);
  }
}

function populateTensorsTable(tensors) {
  const tbody = document.getElementById("tensors-tbody");
  const existingRows = tbody.querySelectorAll("tr");

  let totalParams = 0;

  tensors.forEach((t, index) => {
    let params = t.shape.reduce((a, b) => a * b, 1);
    if (t.shape.length === 0) params = 1;
    totalParams += params;

    let healthBadge = `<span class="px-3 py-1 rounded-full text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 uppercase tracking-widest shadow-[0_0_10px_rgba(16,185,129,0.15)]"><i class="fas fa-check-circle mr-1.5"></i>Healthy</span>`;
    if (t.health !== "OK") {
      healthBadge = `<span class="px-3 py-1 rounded-full text-[10px] font-bold bg-rose-500/10 border border-rose-500/30 text-rose-400 uppercase tracking-widest shadow-[0_0_10px_rgba(244,63,94,0.15)]"><i class="fas fa-exclamation-triangle mr-1.5"></i>${t.health}</span>`;
    }

    const rowHtml = `
      <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-200 tracking-wide">${t.name}</td>
      <td class="px-6 py-4 whitespace-nowrap text-xs text-indigo-300 font-mono bg-indigo-900/10 border-r border-l border-slate-800/50 tracking-wider">[${t.shape.join(" × ")}]</td>
      <td class="px-6 py-4 whitespace-nowrap text-sm">
        <div class="flex flex-col gap-1">
            <span class="text-cyan-400 font-mono tracking-tight"><span class="text-cyan-600 mr-1">&mu;:</span>${t.mean.toFixed(5)}</span>
            <span class="text-xs text-slate-500 font-mono tracking-tight"><span class="text-slate-600 mr-1">&sigma;:</span>${t.std.toFixed(5)}</span>
        </div>
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm">
        <div class="flex flex-col gap-1">
            <span class="text-amber-400 font-mono tracking-tight"><span class="text-amber-600/70 mr-1">Min:</span>${t.min.toFixed(4)}</span>
            <span class="text-fuchsia-400 font-mono tracking-tight"><span class="text-fuchsia-600/70 mr-1">Max:</span>${t.max.toFixed(4)}</span>
        </div>
      </td>
      <td class="px-6 py-4 whitespace-nowrap">${healthBadge}</td>
    `;

    if (existingRows.length > index) {
      existingRows[index].innerHTML = rowHtml;
    } else {
      const tr = document.createElement("tr");
      tr.className =
        "hover:bg-slate-800/40 transition-all duration-300 border-b border-slate-800/60";
      tr.innerHTML = rowHtml;
      tbody.appendChild(tr);
    }
  });

  document.getElementById("param-count").innerHTML =
    `<i class="fas fa-network-wired mr-2"></i><span class="text-indigo-400">${totalParams.toLocaleString()}</span> Total Network Parameters`;
}

function drawDistChart(tensors) {
  const ctx = document.getElementById("distributionChart").getContext("2d");

  const labels = tensors.map(
    (t) => t.name.substring(0, 20) + (t.name.length > 20 ? "..." : ""),
  );
  const means = tensors.map((t) => t.mean);
  const stds = tensors.map((t) => t.std);

  // Update logic to stop UI flicker
  if (distChart) {
    distChart.data.datasets[0].data = means;
    distChart.data.datasets[1].data = stds;
    distChart.update();
    return;
  }

  distChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Tensor Mean Value",
          data: means,
          backgroundColor: "rgba(59, 130, 246, 0.8)",
          borderColor: "rgba(59, 130, 246, 1)",
          borderWidth: 1,
          borderRadius: 2,
        },
        {
          label: "Standard Deviation (σ)",
          data: stds,
          backgroundColor: "rgba(245, 158, 11, 0.8)",
          borderColor: "rgba(245, 158, 11, 1)",
          borderWidth: 1,
          borderRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "top" } },
      scales: {
        x: { ticks: { maxRotation: 45, minRotation: 45, font: { size: 9 } } },
        y: {
          beginAtZero: false,
          suggestedMin: -0.5,
          suggestedMax: 0.5,
          grid: { color: "#e5e7eb" },
        },
      },
    },
  });
}

function drawClassChart(classDist) {
  const ctx = document.getElementById("classDistChart").getContext("2d");

  if (classChart) {
    // If the chart exists, just update data (smooth real-time)
    classChart.data.datasets[0].data = classDist;
    classChart.update();
    return;
  }

  classChart = new Chart(ctx, {
    type: "pie",
    data: {
      labels: [
        "Normal",
        "FOD",
        "Condensateur",
        "Désalignement",
        "Onduleur",
        "Vieillissement",
        "Électronique",
        "Température",
        "Multi-factorielle",
      ],
      datasets: [
        {
          label: "Predictions Frequency",
          data: classDist,
          backgroundColor: [
            "rgba(34, 197, 94, 0.8)", // Normal
            "rgba(239, 68, 68, 0.8)", // FOD
            "rgba(245, 158, 11, 0.8)", // Condensateur
            "rgba(59, 130, 246, 0.8)", // Désalignement
            "rgba(168, 85, 247, 0.8)", // Onduleur
            "rgba(236, 72, 153, 0.8)", // Vieillissement
            "rgba(20, 184, 166, 0.8)", // Électronique (teal-500)
            "rgba(220, 38, 38, 0.8)", // Température (red-600)
            "rgba(107, 114, 128, 0.8)", // Multi-factorielle
          ],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { boxWidth: 12, font: { size: 10 } },
        },
      },
    },
  });
}
