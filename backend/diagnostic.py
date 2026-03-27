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
        fault = "Aucun"
        action = "Maintenir la charge. Bon fonctionnement."
        
        if temp_coil > 75 or temp_inverter > 85 or k_factor < 0.10 or eff < 80:
            status = "CRITIQUE"
        elif temp_coil > 60 or temp_inverter > 75 or k_factor < 0.15 or freq_dev > 2000 or eff < 85: 
            status = "ALERTE"
        elif temp_coil > 50 or temp_inverter > 60 or k_factor < 0.20 or freq_dev > 1000 or eff < 88: 
            status = "SURVEILLANCE"

        if status != "NORMAL":
            if temp_coil > 60 and eff < 85 and k_factor > 0.15:
                fault = "FOD (Objet métallique détecté sur la bobine)"
                action = "Interrompre la charge. Nettoyer la surface du pad primaire."
            elif freq_dev > 1000 and temp_inverter > 60:
                fault = "Défaut de Résonance (Dégradation Condensateur)"
                action = "Planifier le remplacement des condensateurs de l'onduleur."
            elif k_factor < 0.20 and eff < 88:
                fault = "Désalignement critique du Véhicule"
                action = "Guidage requis : Demander au conducteur de recentrer le véhicule."        
            elif eff < 80 and freq_dev <= 1000:
                fault = "Défaut Électronique (Pertes Onduleur)"
                action = "Diagnostic matériel requis sur les MOSFETs de l'onduleur."
            elif temp_coil > 50 and eff >= 85:
                fault = "Dégradation lente de la bobine (Vieillissement)"
                action = "Passer la station en maintenance préventive dans les prochains jours."    
            else:
                fault = "Anomalie Multi-factorielle ou Cyber-attaque"
                action = "Vérifier l'intégrité des communications locales."

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

