import torch
import torch.nn as nn
import torch.optim as optim
import os
import random

MODEL_PATH = os.path.join(os.path.dirname(__file__), "wpt_transformer.pth")

class WPTDiagnosticTransformer(nn.Module):
    def __init__(self, input_dim=12, num_classes=7, d_model=64, nhead=4, num_layers=3):
        super().__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        # Sequence formulation: treating our 1x dim feature vector as sequence length 1
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc_out = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, num_classes)
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
        return "[AI-Transformer] CRITIQUE", "FOD (Objet métallique détecté sur la bobine)", "[ARRÊT SÉCURITÉ IMMÉDIAT] Interrompre la charge. Nettoyer la surface du pad primaire."
    elif pred_idx == 2:
        return "[AI-Transformer] ALERTE", "Défaut de Résonance (Dégradation Condensateur)", "Planifier le remplacement des condensateurs de l'onduleur."
    elif pred_idx == 3:
        return "[AI-Transformer] ALERTE", "Désalignement critique du Véhicule", "Guidage requis : Demander au conducteur de recentrer le véhicule."
    elif pred_idx == 4:
        return "[AI-Transformer] CRITIQUE", "Défaut Électronique (Pertes Onduleur)", "[ARRÊT SÉCURITÉ IMMÉDIAT] Diagnostic matériel requis sur les MOSFETs de l'onduleur."
    elif pred_idx == 5:
        return "[AI-Transformer] SURVEILLANCE", "Dégradation lente de la bobine (Vieillissement)", "Passer la station en maintenance préventive dans les prochains jours."
    elif pred_idx == 6:
        return "[AI-Transformer] CRITIQUE", "Anomalie Multi-factorielle ou Cyber-attaque", "[ARRÊT SÉCURITÉ IMMÉDIAT] Vérifier l'intégrité des communications locales."
    else:
        return "[AI-Transformer] NORMAL", "Aucun", "Maintenir la charge. Bon fonctionnement."

def generate_synthetic_data(samples=8000):
    X = []
    y = []
    for _ in range(samples):
        temp_coil = random.uniform(20.0, 100.0)
        temp_inv = random.uniform(20.0, 100.0)
        eff = random.uniform(70.0, 100.0)
        k_factor = random.uniform(0.05, 0.35)
        freq_dev = random.uniform(0, 3500)
        
        q_factor = random.uniform(10.0, 150.0)
        v1 = random.uniform(20.0, 480.0)
        i1 = random.uniform(0.0, 80.0)
        v2 = random.uniform(20.0, 480.0)
        i2 = random.uniform(0.0, 80.0)
        p1 = (v1 * i1) / 1000.0
        p2 = (v2 * i2) / 1000.0

        fault_class = 0 
        
        if temp_coil > 75 or temp_inv > 85 or k_factor < 0.10 or eff < 80:
            if eff < 80 and freq_dev <= 1000:
                fault_class = 4 
            else:
                fault_class = 6 
        elif temp_coil > 60 or temp_inv > 75 or k_factor < 0.15 or freq_dev > 2000 or eff < 85: 
            if temp_coil > 60 and eff < 85 and k_factor > 0.15:
                fault_class = 1 
            elif freq_dev > 1000 and temp_inv > 60:
                fault_class = 2 
            elif k_factor < 0.20 and eff < 88:
                fault_class = 3 
            else:
                fault_class = 6 
        elif temp_coil > 50 or temp_inv > 60 or k_factor < 0.20 or freq_dev > 1000 or eff < 88: 
            if temp_coil > 50 and eff >= 85:
                fault_class = 5 
            elif k_factor < 0.20 and eff < 88:
                fault_class = 3 
            else:
                fault_class = 5

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
