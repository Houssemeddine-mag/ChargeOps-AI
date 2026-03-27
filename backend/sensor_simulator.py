import time
import random
import math
from datetime import datetime

class WPTSensorSimulator:
    def __init__(self, station_id="WPT-STATION-01"):
        self.station_id = station_id
        self.active_fault = "NORMAL"
        
        # --- Physical Parameters ---
        self.L1 = 150e-6     # Primary inductance (H)
        self.L2 = 150e-6     # Secondary inductance (H)
        self.C1 = 23.37e-9   # Primary capacitance (F)
        self.C2 = 23.37e-9   # Secondary capacitance (F)
        self.R_ac1 = 0.2     # AC resistance primary (Ohms)
        self.R_ac2 = 0.2     # AC resistance secondary (Ohms)
        self.mutual_inductance = 0.0
        
        # --- Pre-calculated Constants ---
        self._2pi = 2.0 * math.pi
        self._base_sqrt_L1L2 = math.sqrt(self.L1 * self.L2)
        
        # --- State Variables ---
        # Fixed Voltages as requested (Update these to match your picture)
        self.v_primary = 400.0
        self.v_secondary = 380.0

        self.i_primary = 15.0
        self.i_secondary = 20.0
        self.phase_angle = 5.0
        
        self.temp_coil = 35.0
        self.temp_inverter = 40.0
        self.coupling_factor = 0.82
        self.frequency = 85.0
        
        self.humidity = 40.0
        self.misalignment = 1.0
        self.fod_detected = False
        self.lod_detected = False
        
        self.capacitor_esr = 0.05
        self.thermal_stress_cycles = 0 
        self.is_charging = True
        self.q_factor = 0.0

    def set_fault_mode(self, fault_type: str):
        """Inject a specific fault mode."""
        if fault_type in {"NORMAL", "FOD", "CAPACITOR", "MISALIGNMENT", "INVERTER", "COIL_DEGRADATION"}:
            self.active_fault = fault_type
            print(f"[{self.station_id}] Fault mode activated: {fault_type}")

    def _apply_fault_transformations(self):
        """Applies physical and electrical transformations based on the active fault."""
        efficiency_drop = 1.0
        
        if self.active_fault == "FOD":
            self.temp_coil += random.uniform(0.5, 2.0)
            self.fod_detected = True
            efficiency_drop = 0.82
        elif self.active_fault == "CAPACITOR":
            self.capacitor_esr += 0.001
            self.temp_inverter += random.uniform(0.3, 1.0)
        elif self.active_fault == "MISALIGNMENT":
            self.misalignment = min(15.0, self.misalignment + 1.0)
        elif self.active_fault == "INVERTER":
            # Voltage fixed as requested, only vary current
            self.i_primary *= random.uniform(0.5, 1.5)
            self.temp_inverter += random.uniform(1.0, 3.0)
            efficiency_drop = 0.60
        elif self.active_fault == "COIL_DEGRADATION":
            self.temp_coil += random.uniform(0.1, 0.4)
            efficiency_drop = 0.95
        elif self.active_fault == "FREQUENCY_BREAKDOWN":
            self.temp_inverter += random.uniform(0.2, 0.5)
            # This causes the main logic to randomly exceed bounds

        return efficiency_drop

    def _calculate_resonant_physics(self, efficiency_drop: float) -> tuple:
        """Calculate physics equations (resonance, mutual inductance, Q-factors, power)."""
        # Eq (6) & (7): Resonance frequency
        eff_C1 = self.C1 * (1.0 - (self.capacitor_esr - 0.05) * 5)
        f_hz = 1.0 / (self._2pi * math.sqrt(self.L1 * eff_C1))
        
        # Base frequency around 85kHz. We add natural noise between -4.5 and +4.5
        # so that it visibly fluctuates between 80 and 90 in the UI.
        noise = random.uniform(-4.5, 4.5)
        self.frequency = (f_hz / 1000.0) + noise

        if self.active_fault == "FREQUENCY_BREAKDOWN":
            # Force the frequency well out of bounds randomly (> 90 or < 80)
            self.frequency = random.choice([random.uniform(70.0, 79.5), random.uniform(90.5, 100.0)])

        # Eq (5): Mutual inductance
        self.mutual_inductance = self.coupling_factor * self._base_sqrt_L1L2

        # Eq (9): Quality factors with dynamic resistance
        temp_delta = max(0.0, (self.temp_coil - 35) * 0.002)
        Rac1_eff = self.R_ac1 + self.capacitor_esr + temp_delta
        Rac2_eff = self.R_ac2 + temp_delta

        omega_L = self._2pi * f_hz * self.L1
        Q1 = omega_L / Rac1_eff
        Q2 = omega_L / Rac2_eff
        self.q_factor = Q1  # Store for payload

        # Eq (15): Coupling efficiency
        K2_Q1_Q2 = (self.coupling_factor**2) * Q1 * Q2
        eta_link = K2_Q1_Q2 / (1.0 + K2_Q1_Q2)
        overall_eta = eta_link * 0.92 * efficiency_drop

        # Power calculations
        power_tx = (self.v_primary * self.i_primary * math.cos(math.radians(self.phase_angle))) / 1000.0
        power_rx = power_tx * overall_eta

        # Fixed secondary voltage matching the primary as requested (update logic if picture differs)
        self.v_secondary = 380.0

        # 3% margin error between I1 and I2 as requested
        margin = random.uniform(-0.03, 0.03)

        if self.active_fault == "I1_I2_ERROR":
            # Force the margin to be intentionally bad (e.g. 5% to 8%)
            margin = random.choice([random.uniform(0.04, 0.08), random.uniform(-0.08, -0.04)])

        self.i_secondary = min(20.0, max(0.0, self.i_primary * (1.0 + margin)))

        return power_tx, power_rx

    def _evaluate_status_level(self, eta_percent: float, freq_khz: float) -> str:
        """Evaluate the overall health status of the station."""
        freq_bad = freq_khz < 80.0 or freq_khz > 90.0
        
        if (self.temp_coil > 75 or self.temp_inverter > 85 or self.coupling_factor < 0.10 or eta_percent < 80 or freq_bad) and self.is_charging:
            return "CRITIQUE"
        if self.temp_coil > 60 or self.temp_inverter > 75 or self.coupling_factor < 0.15 or eta_percent < 85:
            return "ALERTE"
        if self.temp_coil > 50 or self.temp_inverter > 60 or self.coupling_factor < 0.20 or eta_percent < 88:
            return "SURVEILLANCE"
        if not self.is_charging:
            return "ALERTE"
        return "NORMAL"

    def generate_data(self) -> dict:
        """Simulate and return a data frame of the station."""
        # Physical Movement Drift is evaluated first to check coupling
        if self.active_fault != "MISALIGNMENT":
            self.misalignment = max(0.0, min(15.0, self.misalignment + random.uniform(-0.2, 0.2)))
        self.coupling_factor = max(0.01, 0.85 - (self.misalignment * 0.06))

        # IMPORTANT: Station only charges if coupling factor >= 0.75
        self.is_charging = (self.coupling_factor >= 0.75)

        if not self.is_charging:
            # Voltage fixed as requested
            self.v_primary = 400.0
            self.i_primary = self.i_secondary = 0.0
            self.temp_coil = max(25.0, self.temp_coil - 0.5)
            self.temp_inverter = max(25.0, self.temp_inverter - 0.8)
            power_tx = power_rx = 0.0
            eta_percent = 0.0
        else:
            # Voltage fixed as requested
            self.v_primary = 400.0
            # Noise & Smoothing ONLY on I_primary
            self.i_primary = 0.2 * (self.i_primary + random.uniform(-0.5, 0.5)) + 0.8 * 15.0

            # Fault Injection
            efficiency_drop = self._apply_fault_transformations()

            # Nominal Heating & Degradation 
            self.temp_coil += random.uniform(-0.1, 0.2)
            self.temp_inverter += random.uniform(-0.1, 0.25)
            
            self.thermal_stress_cycles += 1
            if self.temp_inverter > 60:
                self.capacitor_esr += 0.0001

            # Core Mathematical Engine
            power_tx, power_rx = self._calculate_resonant_physics(efficiency_drop)
            eta_percent = (power_rx / power_tx) * 100 if power_tx > 0 else 0.0

        # Environmental & Cyber Anomalies
        if self.active_fault != "FOD":
            self.fod_detected = random.random() < 0.01
        self.lod_detected = random.random() < 0.005

        is_attack = random.random() < 0.002
        if is_attack:
            self.temp_coil = 150.0
        else:
            self.temp_coil = max(20.0, min(120.0, self.temp_coil))
            self.temp_inverter = max(20.0, min(120.0, self.temp_inverter))
            
        # Analysis (frequency evaluated globally)
        status_level = self._evaluate_status_level(eta_percent, self.frequency)

        return self._build_payload(power_tx, power_rx, status_level, is_attack)

    def _build_payload(self, p_tx: float, p_rx: float, status: str, cyber_attack: bool = False) -> dict:
        """Constructs the JSON output payload."""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z", 
            "station_id": self.station_id,
            "status_level": status,
            "active_fault_mode": self.active_fault,
            "auth_token": "VEH-AUTH-Valid-X9" if random.random() > 0.05 else "DENIED",
            "is_charging": self.is_charging,
            "electrical": {
                "v_primary": round(self.v_primary, 2),
                "i_primary": round(self.i_primary, 2),
                "v_secondary": round(self.v_secondary, 2),
                "i_secondary": round(self.i_secondary, 2),
                "power_tx_kw": round(p_tx, 2),
                "power_rx_kw": round(p_rx, 2),
                "efficiency_percent": round((p_rx/p_tx)*100, 2) if p_tx > 0 else 0,
                "frequency_hz": round(self.frequency * 1000, 2),
                "capacitor_esr": round(self.capacitor_esr, 4)
            },
            "thermal": {
                "temp_coil_c": round(self.temp_coil, 2),
                "temp_inverter_c": round(self.temp_inverter, 2),
            },
            "quality": {
                "q_factor": round(self.q_factor, 2)
            },
            "coupling": {
                "k_factor": round(self.coupling_factor, 3),
                "mutual_inductance_uh": round(self.mutual_inductance * 1e6, 2),
                "misalignment_cm": round(self.misalignment, 2),
            },
            "environment": {
                "humidity_percent": round(self.humidity, 2),
                "fod_detected": self.fod_detected,
                "lod_detected": self.lod_detected
            },
            "cyber": {
                "possible_injection_attack": cyber_attack
            }
        }
