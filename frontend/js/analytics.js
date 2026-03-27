const API_URL = "/api";

// Chart instances
let faultModesChart = null;
let trendChart = null;

// Theming setup for Chart.js
Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";
Chart.defaults.color = "#6b7280";

document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  fetchAnalyticsData();
  // Auto-refresh the analytics quietly every 2 seconds to sync with the simulation
  setInterval(fetchAnalyticsData, 2000);
});

function initCharts() {
  const ctxFault = document.getElementById("faultModesChart").getContext("2d");
  const ctxTrend = document.getElementById("trendChart").getContext("2d");

  faultModesChart = new Chart(ctxFault, {
    type: "doughnut",
    data: {
      labels: [],
      datasets: [
        {
          data: [],
          backgroundColor: [
            "#3b82f6", // blue-500 (Normal)
            "#f59e0b", // amber-500 (Surveillance)
            "#f97316", // orange-500 (Alerte)
            "#ef4444", // red-500 (Critique)
            "#8b5cf6", // Optional
            "#6366f1", // Optional
          ],
          borderWidth: 0,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "65%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { usePointStyle: true, padding: 20 },
        },
      },
    },
  });

  trendChart = new Chart(ctxTrend, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Avg Efficiency (%)",
          data: [],
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          yAxisID: "y",
          tension: 0.4,
          fill: true,
        },
        {
          label: "Avg Coil Temp (°C)",
          data: [],
          borderColor: "#ef4444",
          backgroundColor: "transparent",
          yAxisID: "y1",
          tension: 0.4,
          borderDash: [5, 5],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: { position: "top", align: "end" },
      },
      scales: {
        x: {
          grid: { display: false },
        },
        y: {
          type: "linear",
          display: true,
          position: "left",
          title: { display: true, text: "Efficiency (%)" },
          grid: { color: "#f3f4f6" },
          min: 0,
          max: 100,
        },
        y1: {
          type: "linear",
          display: true,
          position: "right",
          title: { display: true, text: "Temperature (°C)" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

async function fetchAnalyticsData() {
  try {
    // Fetch last 500 telemetry records for deep analytics
    const resTel = await fetch(`${API_URL}/history/telemetry?limit=500`);
    const telemetry = await resTel.json();

    // Fetch last 100 events
    const resEvt = await fetch(`${API_URL}/history/events?limit=100`);
    const events = await resEvt.json();

    processAnalytics(telemetry, events);
  } catch (e) {
    console.error("Error fetching analytics data:", e);
  }
}

function processAnalytics(telemetry, events) {
  if (!telemetry || telemetry.length === 0) return;

  /// 1. KPI Calculation ///
  let totalEff = 0;
  let maxTemp = 0;
  let faultCount = 0;

  telemetry.forEach((point) => {
    totalEff += point.efficiency;
    if (point.temp_coil > maxTemp) maxTemp = point.temp_coil;
    if (point.fault_mode && point.fault_mode !== "NORMAL") faultCount++;
  });

  const avgEff = totalEff / telemetry.length;

  document.getElementById("stat-avg-eff").textContent = avgEff.toFixed(1) + "%";
  document.getElementById("stat-max-temp").textContent =
    maxTemp.toFixed(1) + "°C";
  document.getElementById("stat-total-faults").textContent = faultCount;
  document.getElementById("stat-total-points").textContent = telemetry.length;

  /// 2. Mode Distribution (Pie Chart) ///
  // Count occurrences of each 'probable_fault' from events or 'fault_mode' from telemetry
  const faultCounts = {};
  telemetry.forEach((t) => {
    const mode = t.fault_mode || "NORMAL";
    faultCounts[mode] = (faultCounts[mode] || 0) + 1;
  });

  faultModesChart.data.labels = Object.keys(faultCounts);
  faultModesChart.data.datasets[0].data = Object.values(faultCounts);
  faultModesChart.update();

  /// 3. Trend Formatting (Line/Bar Chart over time) ///
  // Reverse to chronological order
  const chronoData = [...telemetry].reverse();

  // Group into chunks (e.g. groups of 10 points) to smooth the chart
  const chunkSize = Math.max(1, Math.floor(chronoData.length / 50));
  const trendLabels = [];
  const trendEff = [];
  const trendTemp = [];

  for (let i = 0; i < chronoData.length; i += chunkSize) {
    const chunk = chronoData.slice(i, i + chunkSize);

    // Use the timestamp of the first item in chunk
    const d = new Date(chunk[0].timestamp);
    trendLabels.push(
      `${d.getHours()}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`,
    );

    const avgChEff =
      chunk.reduce((sum, item) => sum + item.efficiency, 0) / chunk.length;
    const avgChTemp =
      chunk.reduce((sum, item) => sum + item.temp_coil, 0) / chunk.length;

    trendEff.push(avgChEff.toFixed(2));
    trendTemp.push(avgChTemp.toFixed(2));
  }

  trendChart.data.labels = trendLabels;
  trendChart.data.datasets[0].data = trendEff;
  trendChart.data.datasets[1].data = trendTemp;
  trendChart.update();

  /// 4. Populate Events Table ///
  const tbody = document.getElementById("analytics-table-body");
  tbody.innerHTML = ""; // Clear existing

  events.slice(0, 15).forEach((evt) => {
    const tr = document.createElement("tr");
    const d = new Date(evt.timestamp);
    const timeStr = `${d.getHours()}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;

    // Status Badge Styling
    let statusBadge = `<span class="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">${evt.status_level}</span>`;
    if (evt.status_level === "NORMAL") {
      statusBadge = `<span class="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">${evt.status_level}</span>`;
    } else if (evt.status_level === "SURVEILLANCE") {
      statusBadge = `<span class="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">${evt.status_level}</span>`;
    } else if (evt.status_level === "ALERTE") {
      statusBadge = `<span class="px-2 py-1 text-xs font-semibold rounded-full bg-orange-100 text-orange-800">${evt.status_level}</span>`;
    } else if (evt.status_level === "CRITIQUE") {
      statusBadge = `<span class="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">${evt.status_level}</span>`;
    }

    tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-gray-500">${timeStr}</td>
            <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">${evt.probable_fault || "Unknown"}</td>
            <td class="px-6 py-4 whitespace-nowrap">${statusBadge}</td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                <i class="fas fa-thermometer-half mr-1 ${evt.status_level === "CRITIQUE" ? "text-red-500" : "text-gray-400"}"></i>
                -- 
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-500 italic max-w-xs truncate">${evt.recommended_action}</td>
        `;
    tbody.appendChild(tr);
  });
}
