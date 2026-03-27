class PrognosticEngine:
    """
    Tâche 4.2.3 : Module de Pronostic Simplifié
    Calcule une tendance linéaire sur les 10 dernières valeurs historiques
    pour estimer le Remaining Useful Life (RUL).
    """
    def __init__(self, critical_threshold=75.0, history_size=10):
        self.history = [] # Liste de tuples (index_temps, valeur)
        self.current_idx = 0
        self.critical_threshold = critical_threshold
        self.history_size = history_size
        
    def add_point(self, value):
        self.history.append((self.current_idx, value))
        self.current_idx += 1
        
        # Conserver seulement N dernières valeurs
        if len(self.history) > self.history_size:
            self.history.pop(0)
            
    def calculate_rul(self):
        """Retourne le nombre de cycles estimés avant d'atteindre le seuil critique."""
        if len(self.history) < 5:
            return None # Pas assez de données pour faire une régression fiable
            
        # Régression linéaire classique : y = a*x + b
        x_vals = [p[0] for p in self.history]
        y_vals = [p[1] for p in self.history]
        
        x_mean = sum(x_vals) / len(x_vals)
        y_mean = sum(y_vals) / len(y_vals)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        denominator = sum((x - x_mean)**2 for x in x_vals)
        
        if denominator == 0: 
            return None
            
        slope = numerator / denominator # Pente "a"
        
        # Si la pente est négative ou nulle, la température n'augmente pas : infinité
        if slope <= 0:
            return 9999.0
            
        intercept = y_mean - slope * x_mean # Ordonnée à l'origine "b"
        
        # A quel index 'x' atteindrons-nous le seuil critique 'y_crit' ?
        # y = a*x + b  =>  x = (y - b) / a
        target_idx = (self.critical_threshold - intercept) / slope
        rul_cycles = target_idx - self.current_idx
        
        return max(0.0, float(rul_cycles))

# Instance unique pour la station (pour ce prototype)
coil_temp_prognostic = PrognosticEngine(critical_threshold=75.0)
