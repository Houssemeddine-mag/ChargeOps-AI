const API_URL = "/api";
let distChart = null;
let classChart = null;
Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";

document.addEventListener("DOMContentLoaded", () => {
  fetchWeightsData();
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
  tbody.innerHTML = "";
  let totalParams = 0;

  tensors.forEach((t) => {
    let params = t.shape.reduce((a, b) => a * b, 1);
    if (t.shape.length === 0) params = 1;
    totalParams += params;

    const tr = document.createElement("tr");
    tr.className = "hover:bg-gray-50 transition-colors";

    let healthBadge = `<span class="px-2.5 py-1 rounded text-[11px] font-bold bg-green-100 text-green-800 uppercase tracking-widest"><i class="fas fa-check mr-1"></i>OK</span>`;
    if (t.health !== "OK") {
      healthBadge = `<span class="px-2.5 py-1 rounded text-[11px] font-bold bg-red-100 text-red-800 uppercase tracking-widest"><i class="fas fa-bug mr-1"></i>${t.health}</span>`;
    }

    tr.innerHTML = `
      <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-800">${t.name}</td>
      <td class="px-6 py-4 whitespace-nowrap text-xs text-gray-500 font-mono bg-gray-50 border-r border-l border-gray-100">[${t.shape.join(", ")}]</td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
        <div class="flex flex-col">
            <span>&mu;: ${t.mean.toFixed(4)}</span>
            <span class="text-xs text-gray-400">&sigma;: ${t.std.toFixed(4)}</span>
        </div>
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
        <div class="flex flex-col">
            <span class="text-blue-600">Min: ${t.min.toFixed(4)}</span>
            <span class="text-red-500">Max: ${t.max.toFixed(4)}</span>
        </div>
      </td>
      <td class="px-6 py-4 whitespace-nowrap">${healthBadge}</td>
    `;
    tbody.appendChild(tr);
  });

  document.getElementById("param-count").textContent =
    `${totalParams.toLocaleString()} Total Network Parameters`;
}

function drawDistChart(tensors) {
  const ctx = document.getElementById("distributionChart").getContext("2d");

  const labels = tensors.map(
    (t) => t.name.substring(0, 20) + (t.name.length > 20 ? "..." : ""),
  );
  const means = tensors.map((t) => t.mean);
  const stds = tensors.map((t) => t.std);

  if (distChart) distChart.destroy();
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
  if (classChart) classChart.destroy();

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
