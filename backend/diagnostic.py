import logging

try:
    from ai_transformer import ai_predict_status
    AI_ENABLED = True
except ImportError as e:
    logging.warning(f"AI Transformer module not available: {e}")
    AI_ENABLED = False

def analyze_telemetry(data: dict):
    """
    Tâche 4.2.2 : Module de Diagnostic
    Utilise un modèle Transformer Neural Network (si disponible) ou la matrice experte par défaut.
    """
    temp_coil = data["thermal"].get("temp_coil_c_filtered", data["thermal"]["temp_coil_c"])      
    temp_inverter = data["thermal"].get("temp_inverter_c_filtered", data["thermal"]["temp_inverter_c"])                                                                                               
    eff = data["electrical"].get("edge_computed_efficiency", data["electrical"]["efficiency_percent"])
    k_factor = data["coupling"]["k_factor"]
    freq = data["electrical"]["frequency_hz"]
    
    q_factor = data.get("quality", {}).get("q_factor", 0.0)
    v1 = data["electrical"].get("v_primary", 0.0)
    i1 = data["electrical"].get("i_primary", 0.0)
    v2 = data["electrical"].get("v_secondary", 0.0)
    i2 = data["electrical"].get("i_secondary", 0.0)
    p1 = (v1 * i1) / 1000.0
    p2 = (v2 * i2) / 1000.0

    freq_dev = abs(freq - 85000)

    # 1. Classification de l'Etat de santé global avec l'IA
    if AI_ENABLED:
        status, fault, action = ai_predict_status(temp_coil, temp_inverter, eff, k_factor, freq_dev, q_factor, v1, i1, v2, i2, p1, p2)
    else:
        status = "NORMAL"
        fault = "Fonctionnement Normal"
        action = "Maintenir la charge en cours. Bon état."
        
        elec_bad = (eff < 75)
        temp_high = (temp_coil > 80 or temp_inverter > 85)
        temp_med = (temp_coil > 65 or temp_inverter > 75)
        
        misaligned = (k_factor < 0.12)
        fod_suspect = (temp_coil > 75 and eff < 80 and k_factor > 0.15)
        condensateur_bad = (freq_dev > 1500 and temp_inverter > 70)
        onduleur_bad = (eff < 70 and freq_dev <= 1500)
        
        if (temp_high and misaligned and eff < 65) or (condensateur_bad and elec_bad):
            status = "CRITIQUE"
            fault = "Anomalie Multi-factorielle"
            action = "Multiples paramètres critiques. Vérification globale immédiate."
        elif fod_suspect:
            status = "CRITIQUE"
            fault = "FOD (Objet métallique détecté)"
            action = "Interrompre la charge. Nettoyer la surface du pad primaire."
        elif condensateur_bad:
            status = "ALERTE"
            fault = "Défaut Condensateur (Résonance)"
            action = "Planifier le remplacement des condensateurs de l'onduleur."
        elif misaligned:
            status = "ALERTE"
            fault = "Désalignement critique"
            action = "Guidage requis, demander au conducteur de recentrer le véhicule."
        elif onduleur_bad:
            status = "CRITIQUE"
            fault = "Défaut Onduleur"
            action = "Diagnostic matériel requis sur les MOSFETs de l'onduleur."
        elif elec_bad and temp_high:
            status = "CRITIQUE"
            fault = "Défaut Température (ou + Électrique)"
            action = "Surchauffe détectée. Relancer le refroidissement."
        elif elec_bad:
            status = "CRITIQUE"
            fault = "Défaut Électronique"
            action = "Anomalie des paramètres de puissance."
        elif temp_high:
            status = "CRITIQUE"
            fault = "Défaut Température"
            action = "Surchauffe détectée. Relancer le refroidissement."
        elif temp_med and eff < 85:
            status = "SURVEILLANCE"
            fault = "Vieillissement (Dégradation lente)"
            action = "Passer la station en maintenance préventive dans les prochains jours."
        elif eff < 90 and temp_coil > 50:
            status = "SURVEILLANCE"
            fault = "Vieillissement (Dégradation lente)"
            action = "Passer la station en maintenance préventive dans les prochains jours."

        # Forcer l'arrêt si critique
        if status == "CRITIQUE":
            action = "[ARRÊT SÉCURITÉ IMMÉDIAT] " + action

    # --- NOUVELLES RÈGLES STRICTES AJOUTÉES DIRECTEMENT ICI ---
    # frequency has a marge error from 80 to 90khz, else break down and alert runs
    freq_khz = freq / 1000.0
    if freq_khz < 80.0 or freq_khz > 90.0:
        status = "CRITIQUE"
        fault = "Frequency breakdown (hors de 80-90kHz)!"
        action = "[ARRÊT] The system broke down and alert is running."

    # if the marge error between I1 and I2 deppasse +-3% the station stops charging and the alert runs
    if i1 > 0:
        margin_error = abs(i1 - i2) / i1 * 100.0
        if margin_error > 3.0:
            status = "CRITIQUE"
            fault = "I1/I2 Marge Error (>3%)"
            action = "[STATION STOPPED] Station arrétée d'urgence et alerte lancée."

    return status, fault, action

