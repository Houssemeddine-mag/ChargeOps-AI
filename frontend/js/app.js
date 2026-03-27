const API_URL = "/api";

let globalStatusLevel = "NORMAL";

// Fetch Latest Telemetry
async function fetchTelemetry() {
  try {
    const response = await fetch(`${API_URL}/history/telemetry?limit=1`);
    if (!response.ok) throw new Error("HTTP erreur " + response.status);
    const data = await response.json();

    if (data.length > 0) {
      const current = data[0];

      // Jauges (Gauges)
      document.getElementById("val-eff").textContent = current.efficiency
        ? current.efficiency.toFixed(1)
        : "--";
      const barEff = document.getElementById("bar-eff");
      if (current.efficiency && barEff) {
        barEff.style.width =
          Math.min(100, Math.max(0, current.efficiency)) + "%";
      }

      document.getElementById("val-ptx").textContent = current.frequency
        ? (current.frequency / 1000).toFixed(1)
        : "--";

      const kEl = document.getElementById("val-k");
      if (kEl) {
        kEl.textContent =
          current.coupling_k !== undefined && current.coupling_k !== null
            ? current.coupling_k.toFixed(3)
            : "--";
      }

      const tempCoilEl = document.getElementById("val-temp-coil");
      if (tempCoilEl) {
        tempCoilEl.textContent =
          current.temp_coil !== undefined && current.temp_coil !== null
            ? current.temp_coil.toFixed(1)
            : "--";
      }

      const tempInvEl = document.getElementById("val-temp-inv");
      if (tempInvEl) {
        tempInvEl.textContent =
          current.temp_inverter !== undefined && current.temp_inverter !== null
            ? current.temp_inverter.toFixed(1)
            : "--";
      }

      const qFactorEl = document.getElementById("val-qfactor");
      if (qFactorEl) {
        qFactorEl.textContent =
          current.q_factor !== undefined && current.q_factor !== null
            ? current.q_factor.toFixed(2)
            : "--";
      }

      // Check frequency bounds 80kHz to 90kHz
      const currentFreq = current.frequency ? current.frequency / 1000 : 85;
      const freqValid = currentFreq >= 80 && currentFreq <= 90;

      // Error Margin between I1 and I2 (+-3%)
      let i1_i2_error = false;
      if (current.i1 && current.i2) {
        const diff = Math.abs(current.i1 - current.i2);
        const percent = (diff / current.i1) * 100;
        if (percent > 3) {
          i1_i2_error = true;
        }
      }

      // Evaluate Charging Status based on Coupling Factor, Frequency, and I1/I2 difference
      const isCharging =
        current.coupling_k &&
        current.coupling_k >= 0.75 &&
        freqValid &&
        !i1_i2_error;
      const chargingEl = document.getElementById("val-charging");
      const chargingBar = document.getElementById("bar-charging");
      if (chargingEl) {
        if (isCharging) {
          chargingEl.textContent = "ACTIVE";
          chargingEl.className = "text-xs font-bold text-blue-400";
          if (chargingBar)
            chargingBar.className =
              "h-full bg-blue-500 transition-all duration-500";
        } else {
          chargingEl.textContent = "HALTED";
          chargingEl.className = "text-xs font-bold text-red-500";
          if (chargingBar)
            chargingBar.className =
              "h-full bg-red-500 transition-all duration-500";
        }
      }

      const freqEl = document.getElementById("val-ptx");
      if (freqEl) {
        if (!freqValid) {
          freqEl.className = "text-sm font-black text-red-500";
        } else {
          freqEl.className = "text-sm font-black text-slate-800";
        }
      }

      // Health badge logic
      let health = 100;
      if (current.efficiency < 80) health -= 20;
      if (!isCharging) health -= 30; // Penalize if charging halted due to low coupling
      if (!freqValid) health -= 40; // High penalty for bad frequency

      let badgeHtml = '<i class="fas fa-check text-green-600"></i>';
      let badgeClasses =
        "ml-2 w-10 h-10 rounded-full border-2 border-green-500 flex items-center justify-center bg-green-50 shadow-sm";
      let textClass = "text-5xl font-black tracking-tighter text-slate-800";
      let alertText = "NO ALERT";
      let alertClasses =
        "ml-2 px-2 py-0.5 text-[10px] font-bold rounded bg-green-100 text-green-800 border border-green-200 uppercase tracking-wider";

      const hasRedAlert =
        globalStatusLevel.includes("CRITIQUE") ||
        globalStatusLevel.includes("ALERTE");
      const hasAnyAlert = !globalStatusLevel.includes("NORMAL");

      // conditions logic matching EXACTLY what user said:
      // green if HI>80% and add a field alert that says no alert
      // yellow if 60<HI<80 and no alert
      // red if HI<60% with a red alert
      if (health < 60) {
        badgeClasses =
          "ml-2 w-10 h-10 rounded-full border-2 border-red-500 flex items-center justify-center bg-red-50 shadow-sm";
        badgeHtml = '<i class="fas fa-times text-red-600"></i>';
        textClass = "text-5xl font-black tracking-tighter text-slate-800";
        dotPingColor = "bg-red-400";
        dotColor = "bg-red-500";
        alertText = "RED ALERT";
        alertClasses =
          "ml-2 px-2 py-0.5 text-[10px] font-bold rounded bg-red-100 text-red-800 border border-red-200 uppercase tracking-wider";
      } else if (health <= 80) {
        badgeClasses =
          "ml-2 w-10 h-10 rounded-full border-2 border-amber-500 flex items-center justify-center bg-amber-50 shadow-sm";
        badgeHtml = '<i class="fas fa-exclamation text-amber-600"></i>';
        textClass = "text-5xl font-black tracking-tighter text-slate-800";
        dotPingColor = "bg-amber-400";
        dotColor = "bg-amber-500";
        alertText = "NO ALERT"; // User wanted yellow to read "no alert" per prompt
        alertClasses =
          "ml-2 px-2 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-800 border border-amber-200 uppercase tracking-wider";
      } else {
        badgeClasses =
          "ml-2 w-10 h-10 rounded-full border-2 border-green-500 flex items-center justify-center bg-green-50 shadow-sm";
        badgeHtml = '<i class="fas fa-check text-green-600"></i>';
        textClass = "text-5xl font-black tracking-tighter text-slate-800";
        dotPingColor = "bg-green-400";
        dotColor = "bg-green-500";
        alertText = "NO ALERT";
        alertClasses =
          "ml-2 px-2 py-0.5 text-[10px] font-bold rounded bg-green-100 text-green-800 border border-green-200 uppercase tracking-wider";
      }

      const badge = document.getElementById("health-badge");
      if (badge) {
        badge.className = badgeClasses;
        badge.innerHTML = badgeHtml;
      }

      const healthIndexElem = document.getElementById("health-index");
      if (healthIndexElem) {
        healthIndexElem.textContent = health + "%";
        healthIndexElem.className = textClass;
      }

      const alertElem = document.getElementById("health-alert-text");
      if (alertElem) {
        alertElem.textContent = alertText;
        alertElem.className = alertClasses;
      }

      const dotPingElem = document.getElementById("health-dot-ping");
      if (dotPingElem) {
        dotPingElem.className = `animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotPingColor}`;
      }

      const dotElem = document.getElementById("health-dot");
      if (dotElem) {
        dotElem.className = `relative inline-flex rounded-full h-2.5 w-2.5 ${dotColor}`;
      }

      document.getElementById("val-v1").textContent =
        current.v1 !== undefined ? current.v1.toFixed(1) : "--";
      document.getElementById("val-i1").textContent =
        current.i1 !== undefined ? current.i1.toFixed(1) : "--";
      document.getElementById("val-v2").textContent =
        current.v2 !== undefined ? current.v2.toFixed(1) : "--";
      document.getElementById("val-i2").textContent =
        current.i2 !== undefined ? current.i2.toFixed(1) : "--";

      // Calculate Power (W to kW by dividing by 1000)
      const p1 =
        current.v1 && current.i1 ? (current.v1 * current.i1) / 1000 : 0;
      const p2 =
        current.v2 && current.i2 ? (current.v2 * current.i2) / 1000 : 0;

      const valP1 = document.getElementById("val-p1");
      if (valP1)
        valP1.textContent = current.v1 !== undefined ? p1.toFixed(2) : "--";

      const valP2 = document.getElementById("val-p2");
      if (valP2)
        valP2.textContent = current.v2 !== undefined ? p2.toFixed(2) : "--";
    }
  } catch (e) {
    console.error("Erreur de récupération Télémétrie:", e);
  }
}

// Fetch Events & Alerts
async function fetchEvents() {
  try {
    const response = await fetch(`${API_URL}/history/events?limit=8`);
    const events = await response.json();

    const tbody = document.getElementById("alerts-table");
    tbody.innerHTML = "";

    if (events.length > 0) {
      // Module Maintenance (Dernier évènement)
      const latest = events[0];
      globalStatusLevel = latest.status_level || "NORMAL";

      // Update AI Diagnostic Box natively in light mode
      const probSpan = document.getElementById("current-fault");
      const iconSpan = document.getElementById("state-icon");

      probSpan.textContent = latest.probable_fault || "No anomalies.";

      if (latest.status_level && latest.status_level.includes("CRITIQUE")) {
        probSpan.className = "text-red-400 font-bold text-xs truncate";
        iconSpan.innerHTML =
          '<i class="fas fa-times-circle text-red-500 text-xl"></i>';
      } else if (
        latest.status_level &&
        latest.status_level.includes("ALERTE")
      ) {
        probSpan.className = "text-orange-400 font-bold text-xs truncate";
        iconSpan.innerHTML =
          '<i class="fas fa-exclamation-triangle text-orange-400 text-xl"></i>';
      } else if (
        latest.status_level &&
        latest.status_level.includes("SURVEILLANCE")
      ) {
        probSpan.className = "text-yellow-400 font-bold text-xs truncate";
        iconSpan.innerHTML =
          '<i class="fas fa-search text-yellow-400 text-xl"></i>';
      } else {
        probSpan.className = "text-green-400 font-bold text-xs truncate";
        iconSpan.innerHTML =
          '<i class="fas fa-check-circle text-green-400 text-xl"></i>';
      }

      document.getElementById("current-action").textContent =
        latest.recommended_action ||
        "System operating normally within threshold bounds.";

      // RUL Prediction Check
      document.getElementById("val-rul").textContent =
        latest.estimated_rul_seconds !== null &&
        latest.estimated_rul_seconds !== undefined &&
        latest.estimated_rul_seconds < 100
          ? Math.round(latest.estimated_rul_seconds)
          : "--";

      // Historique Array rendering
      events.forEach((ev) => {
        let badgeStyle = "bg-green-100 text-green-800 border-green-200";
        if (ev.status_level && ev.status_level.includes("CRITIQUE"))
          badgeStyle = "bg-red-100 text-red-800 border-red-200";
        else if (ev.status_level && ev.status_level.includes("ALERTE"))
          badgeStyle = "bg-orange-100 text-orange-800 border-orange-200";
        else if (ev.status_level && ev.status_level.includes("SURVEILLANCE"))
          badgeStyle = "bg-yellow-100 text-yellow-800 border-yellow-200";

        // Clean out any tags to be crisp
        let statusName = (ev.status_level || "NORMAL").replace(
          "[AI-Transformer] ",
          "",
        );

        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50 transition-colors";

        const d = new Date(ev.timestamp);
        const timeStr = `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;

        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-medium">${timeStr}</td>        
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeStyle}">
                ${statusName}
              </span>
            </td>                                                                               
            <td class="px-6 py-4 text-sm text-slate-800 font-medium">${ev.probable_fault || "--"}</td>      
            <td class="px-6 py-4 text-sm text-gray-500">${ev.recommended_action || "--"}</td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (e) {
    console.error("Erreur de récupération Evènements:", e);
  }
}

// Init & loop
document.addEventListener("DOMContentLoaded", () => {
  // Initial fetch
  fetchTelemetry();
  fetchEvents();

  // Boucle de rafraichissement toutes les 2 secondes
  setInterval(() => {
    fetchTelemetry();
    fetchEvents();
  }, 2000);
});
