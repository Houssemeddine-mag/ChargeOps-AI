import torch
import torch.nn as nn
import torch.optim as optim
import os
import random

MODEL_PATH = os.path.join(os.path.dirname(__file__), "wpt_transformer.pth")

class WPTDiagnosticTransformer(nn.Module):
    def __init__(self, input_dim=12, num_classes=9, d_model=64, nhead=4, num_layers=3):
        super().__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        # Sequence formulation: treating our 1x dim feature vector as sequence length 1
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc_out = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes)
        )
        
    def forward(self, x):
        # x shape: (batch, input_dim) -> (batch, 1, d_model)
        x = self.embedding(x).unsqueeze(1)
        # Pass through Transformer blocks
        x = self.transformer(x)
        # Extract features and classify -> (batch, num_classes)
        x = x.squeeze(1)
        return self.fc_out(x)

def get_diagnostic_outputs(pred_idx):
    if pred_idx == 1:
        return "[AI] CRITIQUE", "FOD (Objet métallique détecté)", "[ARRÊT SÉCURITÉ] Interrompre la charge. Nettoyer la surface du pad primaire."
    elif pred_idx == 2:
        return "[AI] ALERTE", "Défaut Condensateur (Résonance)", "[MAINTENANCE] Planifier le remplacement des condensateurs de l'onduleur."
    elif pred_idx == 3:
        return "[AI] ALERTE", "Désalignement critique", "[GUIDAGE] Guidage requis, demander au conducteur de recentrer le véhicule."
    elif pred_idx == 4:
        return "[AI] CRITIQUE", "Défaut Onduleur", "[ARRÊT SÉCURITÉ] Diagnostic matériel requis sur les MOSFETs de l'onduleur."
    elif pred_idx == 5:
        return "[AI] SURVEILLANCE", "Vieillissement (Dégradation lente)", "[MAINTENANCE] Passer la station en maintenance préventive dans les prochains jours."
    elif pred_idx == 6:
        return "[AI] CRITIQUE", "Défaut Électronique", "[ARRÊT SÉCURITÉ] Anomalie des paramètres de puissance."
    elif pred_idx == 7:
        return "[AI] CRITIQUE", "Défaut Température (ou + Électrique)", "[ARRÊT SÉCURITÉ] Surchauffe détectée. Relancer le refroidissement."
    elif pred_idx == 8:
        return "[AI] CRITIQUE", "Anomalie Multi-factorielle", "[ARRÊT SÉCURITÉ] Multiples paramètres critiques. Vérification globale immédiate."
    else:
        return "[AI] NORMAL", "Fonctionnement Normal", "Maintenir la charge en cours. Bon état."

def generate_synthetic_data(samples=12000):
    X = []
    y = []
    for _ in range(samples):
        is_normal = random.random() < 0.3
        
        if is_normal:
            temp_coil = random.uniform(20.0, 50.0)
            temp_inv = random.uniform(20.0, 60.0)
            eff = random.uniform(90.0, 99.0)
            k_factor = random.uniform(0.20, 0.35)
            freq_dev = random.uniform(0, 500)
            q_factor = random.uniform(100.0, 150.0)
        else:
            temp_coil = random.uniform(20.0, 100.0)
            temp_inv = random.uniform(20.0, 100.0)
            eff = random.uniform(50.0, 95.0)
            k_factor = random.uniform(0.05, 0.35)
            freq_dev = random.uniform(0, 3500)
            q_factor = random.uniform(10.0, 150.0)
        
        v1 = random.uniform(200.0, 480.0)
        i1 = random.uniform(10.0, 80.0)
        p1 = (v1 * i1) / 1000.0
        
        p2 = p1 * (eff / 100.0)
        v2 = v1 * random.uniform(0.8, 1.0)
        if v2 <= 0: v2 = 0.1
        i2 = (p2 * 1000.0) / v2

        fault_class = 0 
        
        elec_bad = (eff < 75)
        temp_high = (temp_coil > 80 or temp_inv > 85)
        temp_med = (temp_coil > 65 or temp_inv > 75)
        
        misaligned = (k_factor < 0.12)
        fod_suspect = (temp_coil > 75 and eff < 80 and k_factor > 0.15)
        condensateur_bad = (freq_dev > 1500 and temp_inv > 70)
        onduleur_bad = (eff < 70 and freq_dev <= 1500)
        
        if (temp_high and misaligned and eff < 65) or (condensateur_bad and elec_bad):
            fault_class = 8 # Multi-factorielle
        elif fod_suspect:
            fault_class = 1 # Fod
        elif condensateur_bad:
            fault_class = 2 # Condensateur
        elif misaligned:
            fault_class = 3 # Desalignements
        elif onduleur_bad:
            fault_class = 4 # Onduleur
        elif elec_bad and temp_high:
            fault_class = 7 # Température + Electrique
        elif elec_bad:
            fault_class = 6 # Electronique
        elif temp_high:
            fault_class = 7 # Température
        elif temp_med and eff < 85:
            fault_class = 5 # Vieillissement
        elif eff < 90 and temp_coil > 50:
            fault_class = 5 # Early vieillissement
        else:
            fault_class = 0 # Normal

        X.append([
            temp_coil / 100.0,
            temp_inv / 100.0,
            eff / 100.0,
            k_factor / 0.5,
            freq_dev / 5000.0,
            q_factor / 200.0,
            v1 / 500.0,
            i1 / 100.0,
            v2 / 500.0,
            i2 / 100.0,
            p1 / 50.0,
            p2 / 50.0
        ])
        y.append(fault_class)

    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.long)

def train_or_load_model():
    model = WPTDiagnosticTransformer()
    if os.path.exists(MODEL_PATH):
        try:
            model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
            model.eval()
            return model
        except Exception as e:
            print("[AI] Failed to load model architecture, retraining...", e)
        
    print("🛠️ Training new Deep PyTorch Transformer model (7-Class Diagnostics)...")
    X, y = generate_synthetic_data(10000)
    optimizer = optim.Adam(model.parameters(), lr=0.003)
    criterion = nn.CrossEntropyLoss()
    
    model.train()
    for epoch in range(250): 
        optimizer.zero_grad()
        out = model(X)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch + 1}/250], Loss: {loss.item():.4f}")
        
    torch.save(model.state_dict(), MODEL_PATH)
    print("✅ Transform Model saved successfully to", MODEL_PATH)
    model.eval()
    return model

ai_model = train_or_load_model()

def ai_predict_status(temp_coil, temp_inv, eff, k_factor, freq_dev, q_factor, v1, i1, v2, i2, p1, p2):
    model = train_or_load_model() 
    
    with torch.no_grad():
        x = torch.tensor([[
            temp_coil / 100.0,
            temp_inv / 100.0,
            eff / 100.0,
            k_factor / 0.5,
            freq_dev / 5000.0,
            q_factor / 200.0,
            v1 / 500.0,
            i1 / 100.0,
            v2 / 500.0,
            i2 / 100.0,
            p1 / 50.0,
            p2 / 50.0
        ]], dtype=torch.float32)

        out = model(x)
        pred_idx = torch.argmax(out, dim=1).item()

        return get_diagnostic_outputs(pred_idx)
