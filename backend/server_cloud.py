from fastapi import FastAPI, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
import math

import database
from diagnostic import analyze_telemetry
from prognostic import coil_temp_prognostic
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="WPT Cloud Backend (Task 4)")

# Mount frontend folder explicitly to avoid VSCode Live Server issues
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/dashboard", StaticFiles(directory=frontend_path, html=True), name="frontend")

@app.get("/")
def read_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# Configuration CORS pour autoriser le frontend (Tâche 5) à faire des requêtes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Injection de dépendance pour la base de données SQLite
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/telemetry")
async def receive_telemetry(request: Request, db: Session = Depends(get_db)):
    """ 
    Endpoint pour recevoir les données JSON de l'Edge Node (Tâche 4.2.1)
    """
    data = await request.json()
    
    # 1. Extraction Télémétrie Lissé
    temp_coil = data["thermal"].get("temp_coil_c_filtered", data["thermal"]["temp_coil_c"])
    temp_inv = data["thermal"].get("temp_inverter_c_filtered", data["thermal"]["temp_inverter_c"])
    eff = data["electrical"].get("edge_computed_efficiency", data["electrical"]["efficiency_percent"])
    k_factor = data["coupling"]["k_factor"]
    freq = data["electrical"]["frequency_hz"]
    
    # 2. IA : Diagnostic Expert (Tâche 4.2.2)
    status, fault, action = analyze_telemetry(data)
    
    # 3. IA : Pronostic RUL (Tâche 4.2.3)
    coil_temp_prognostic.add_point(temp_coil)
    rul = coil_temp_prognostic.calculate_rul()
    
    # 4. Logique de Décision et Stockage (Tâche 4.2.4)
    telemetry_entry = database.TelemetryDB(
        timestamp=data["timestamp"],
        station_id=data["station_id"],
        temp_coil=temp_coil,
        temp_inverter=temp_inv,
        efficiency=eff,
        coupling_k=k_factor,
        frequency=freq,
        q_factor=data.get("quality", {}).get("q_factor", 0.0),
        v1=data["electrical"].get("v_primary", 0.0),
        i1=data["electrical"].get("i_primary", 0.0),
        v2=data["electrical"].get("v_secondary", 0.0),
        i2=data["electrical"].get("i_secondary", 0.0)
    )
    db.add(telemetry_entry)
    
    # Enregistrer un évènement si le statut n'est pas Normal ou si RUL < 10 cycles
    if status != "NORMAL" or (rul is not None and rul < 10.0):
        event = database.EventDB(
            station_id=data["station_id"],
            status_level=status,
            probable_fault=fault,
            recommended_action=action,
            estimated_rul_seconds=rul
        )
        db.add(event)
        
    db.commit()
    
    return {
        "message": "Data processed successfully",
        "diagnostic_result": {
            "status_level": status,
            "fault": fault,
            "action": action
        },
        "prognostic_result": {
            "coil_temp_rul_cycles": rul if rul is not None else "Calculating trend..."
        }
    }

@app.get("/api/history/telemetry")
def get_telemetry_history(limit: int = 100, db: Session = Depends(get_db)):
    """ Récupérer l'historique enregistré en BDD """
    data = db.query(database.TelemetryDB).order_by(database.TelemetryDB.id.desc()).limit(limit).all()
    return data

@app.get("/api/history/events")
def get_event_history(limit: int = 50, db: Session = Depends(get_db)):
    """ Récupérer l'historique des actions et diagnostics """
    events = db.query(database.EventDB).order_by(database.EventDB.id.desc()).limit(limit).all()
    return events

@app.get("/api/model/weights")
def get_model_weights():
    """ Expose internal weights, properties, and accuracy of the trained PyTorch Transformer """
    import torch
    import os
    from ai_transformer import train_or_load_model, generate_synthetic_data
    
    model_path = os.path.join(os.path.dirname(__file__), "wpt_transformer.pth")
    if not os.path.exists(model_path):
        return {"status": "error", "message": "Model not found."}

    # Evaluate Model Accuracy Dynamically
    model = train_or_load_model()
    model.eval()
    
    # Generate a small test set for immediate evaluation
    X_test, y_test = generate_synthetic_data(500)
    with torch.no_grad():
        out = model(X_test)
        preds = torch.argmax(out, dim=1)
        correct = (preds == y_test).sum().item()
        accuracy = (correct / 500.0) * 100.0

        # Calculate class distribution
        class_distribution = [0] * 7
        for p in preds:
            class_distribution[p.item()] += 1
    state_dict = torch.load(model_path, map_location="cpu")
    
    # We won't return ALL raw floats as it's too much JSON overhead. 
    # We'll return shape statistics, norms, and selective slices for visualizations.
    
    is_healthy = True
    for key, tensor in state_dict.items():
        if torch.isnan(tensor).any() or torch.isinf(tensor).any():
            is_healthy = False
            
    summary = {
        "architecture": "WPTDiagnosticTransformer (7-Class)",
        "layers": 3,
        "d_model": 64,
        "nhead": 4,
        "input_dim": 12,
        "output_classes": 7,
        "accuracy": round(accuracy, 2),
        "class_predictions_dist": class_distribution,
        "model_status": "🟢 Healthy" if is_healthy else "🔴 Corrupted (NaN/Inf Detected)",
        "tensors": []
    }

    for key, tensor in state_dict.items():
        mean_val = tensor.float().mean().item()
        
        # Simple health check per tensor 
        tensor_status = "OK" 
        if torch.isnan(tensor).any() or torch.isinf(tensor).any():
            tensor_status = "CORRUPTED"
        elif abs(mean_val) > 100:
            tensor_status = "WARNING: HIGH MAGNITUDE"
            
        summary["tensors"].append({
            "name": key,
            "shape": list(tensor.shape),
            "mean": round(mean_val, 6),
            "std": round(tensor.float().std().item(), 6),
            "min": round(tensor.float().min().item(), 6),
            "max": round(tensor.float().max().item(), 6),
            "health": tensor_status,
            # Return partial slice of data
            "sample": tensor.float().flatten()[:40].tolist()
        })
        
    return summary

if __name__ == "__main__":
    print("🚀 Démarrage du Serveur Backend (Tâche 4) sur le port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
