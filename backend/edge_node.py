import time
import json
import logging
from collections import deque
import paho.mqtt.client as mqtt
from sensor_simulator import WPTSensorSimulator

# --- Configuration ---
BROKER_ADDRESS = "localhost"
BROKER_PORT = 1883
TOPIC_TELEMETRY = "wpt/telemetry"
TOPIC_ALERTS = "wpt/alerts"
SAMPLE_RATE = 1.0 # 1 seconde par cycle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EdgeAcquisitionNode:
    def __init__(self):
        self.simulator = WPTSensorSimulator()
        
        # Buffers pour le filtre de moyenne mobile (Moving Average)
        self.window_size = 5
        self.buffers = {
            "temp_coil": deque(maxlen=self.window_size),
            "temp_inverter": deque(maxlen=self.window_size),
            "v_primary": deque(maxlen=self.window_size),
            "i_primary": deque(maxlen=self.window_size),
            "power_tx": deque(maxlen=self.window_size),
            "power_rx": deque(maxlen=self.window_size)
        }
        
        # Configuration MQTT
        self.mqtt_client = mqtt.Client(client_id="WPT-Edge-Node")
        self.mqtt_client.on_connect = self._on_connect
        
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connecté au Broker MQTT avec succès.")
        else:
            logging.error(f"Échec de connexion au Broker. Code retour : {rc}")

    def connect_mqtt(self):
        try:
            self.mqtt_client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logging.warning(f"Impossible de se connecter à MQTT ({e}). Le script continuera en mode local (affichage terminal).")

    def _apply_moving_average(self, key, new_value):
        """Filtre de lissage (Moyenne mobile) pour réduire le bruit"""
        self.buffers[key].append(new_value)
        return sum(self.buffers[key]) / len(self.buffers[key])

    def process_and_publish(self):
        """Acquisition, pré-traitement (Edge Computing) et envoi via MQTT"""
        # 1. Acquisition brute depuis le "capteur" matériel
        raw_data = self.simulator.generate_data()
        
        # 2. Pré-traitement Edge (Filtrage)
        filtered_temp_coil = self._apply_moving_average("temp_coil", raw_data["thermal"]["temp_coil_c"])
        filtered_temp_inv = self._apply_moving_average("temp_inverter", raw_data["thermal"]["temp_inverter_c"])
        filtered_p_tx = self._apply_moving_average("power_tx", raw_data["electrical"]["power_tx_kw"])
        filtered_p_rx = self._apply_moving_average("power_rx", raw_data["electrical"]["power_rx_kw"])
        
        # 3. Calcul Edge d'Indicateurs Clés (KPI)
        # Recalcul de l'efficacité sur les puissances lissées
        edge_efficiency = (filtered_p_rx / filtered_p_tx) * 100 if filtered_p_tx > 0 else 0
        
        # Mise à jour du payload avec les données traitées (Edge)
        edge_payload = raw_data.copy()
        edge_payload["thermal"]["temp_coil_c_filtered"] = round(filtered_temp_coil, 2)
        edge_payload["thermal"]["temp_inverter_c_filtered"] = round(filtered_temp_inv, 2)
        edge_payload["electrical"]["power_tx_kw_filtered"] = round(filtered_p_tx, 2)
        edge_payload["electrical"]["power_rx_kw_filtered"] = round(filtered_p_rx, 2)
        edge_payload["electrical"]["edge_computed_efficiency"] = round(edge_efficiency, 2)
        
        # 4. Transmission des données
        payload_str = json.dumps(edge_payload)
        
        # Publish MQTT
        try:
            self.mqtt_client.publish(TOPIC_TELEMETRY, payload_str)
        except Exception:
            pass # Géré si non connecté
            
        # HTTP POST HTTP vers Backend Cloud pour la Tâche 4
        try:
            import requests
            # Update this URL to target the cloud backend instead of local:
            # We use the provided Render URL
            target_url = "https://chargeops-ai.onrender.com/api/telemetry"
            requests.post(target_url, json=edge_payload, timeout=2.0)
        except Exception:
            pass
            
        logging.info(f"[{raw_data['status_level']}] Eff: {edge_efficiency:.1f}% | Temp Bobine Lissé: {filtered_temp_coil:.1f}°C")
        
        # Si une anomalie majeure est détectée sur l'Edge, on envoie sur un topic critique
        if raw_data["status_level"] in ["ALERTE", "CRITIQUE"]:
            alert_payload = {"station_id": self.simulator.station_id, "alert_level": raw_data["status_level"], "fault_mode": raw_data["active_fault_mode"]}
            try:
                self.mqtt_client.publish(TOPIC_ALERTS, json.dumps(alert_payload))
            except:
                pass


def run_scenario():
    print('Démarrage de la simulation continue en temps réel')
    node = EdgeAcquisitionNode()
    node.connect_mqtt()
    logging.info('=== DEBUT DE LA MISSION D ACQUISITION WPT ===')
    try:
        while True:
            logging.info('\n--- SCENARIO 1: Fonctionnement Normal (Tout vert) ---')
            node.simulator.set_fault_mode('NORMAL')
            # Reset properties to normal mode
            node.simulator.temp_coil = 35.0
            node.simulator.temp_inverter = 40.0
            node.simulator.misalignment = 1.0
            node.simulator.capacitor_esr = 0.05
            for _ in range(20):
                node.process_and_publish()
                time.sleep(SAMPLE_RATE)

            logging.info('\n--- SCENARIO 2: Derive Lente (Temperature -> Surveillance) ---')
            node.simulator.set_fault_mode('COIL_DEGRADATION')
            node.simulator.temp_coil = 52.0 # Force temp > 50 for SURVEILLANCE
            for _ in range(20):
                node.process_and_publish()
                time.sleep(SAMPLE_RATE)

            logging.info('\n--- SCENARIO 3: Defaut brusque (Desalignement -> Alerte) ---')
            node.simulator.set_fault_mode('MISALIGNMENT')
            node.simulator.misalignment = 12.0 # Dropping K-factor to trigger ALERTE
            for _ in range(20):
                node.process_and_publish()
                time.sleep(SAMPLE_RATE)

            logging.info('\n--- SCENARIO 4: Defaut critique (Surchauffe massive -> Critique) ---')
            node.simulator.set_fault_mode('FOD')
            node.simulator.temp_coil = 80.0 # Temp > 75 for CRITIQUE
            for _ in range(20):
                node.process_and_publish()
                time.sleep(SAMPLE_RATE)

            logging.info('\n--- SCENARIO 5: Usure Condensateur (Capacitor -> Surveillance/Alerte) ---')
            node.simulator.set_fault_mode('CAPACITOR')
            node.simulator.temp_coil = 40.0
            node.simulator.capacitor_esr = 0.15 # Force anomalies
            for _ in range(20):
                node.process_and_publish()
                time.sleep(SAMPLE_RATE)

            logging.info('\n--- SCENARIO 6: ERREUR FREQUENCE (Hors 80-90kHz -> Critique) ---')
            node.simulator.set_fault_mode('FREQUENCY_BREAKDOWN')
            node.simulator.temp_coil = 35.0
            # Frequency is naturally bypassed in sensor_simulator
            for _ in range(20):
                node.process_and_publish()
                time.sleep(SAMPLE_RATE)

            logging.info('\n--- SCENARIO 7: ERREUR MARGE I1/I2 (>3% -> Critique) ---')
            node.simulator.set_fault_mode('I1_I2_ERROR')
            for _ in range(20):
                node.process_and_publish()
                time.sleep(SAMPLE_RATE)

    except KeyboardInterrupt:
        logging.info('Acquisition stoppee par utilisateur.')
    finally:
        node.mqtt_client.loop_stop()
        node.mqtt_client.disconnect()
        logging.info('=== FIN DE LA MISSION ===')

if __name__ == "__main__":
    run_scenario()

