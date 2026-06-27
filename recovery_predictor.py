class RecoveryPredictor:
    @staticmethod
    def predict_tomorrow(current_hrv: float, target_hrv: float, sleep_hours: float, workout_intensity: str) -> dict:
        """
        Predicts tomorrow's HRV and estimates the number of days to full recovery.
        
        workout_intensity options:
        - "Rest Day"
        - "Zone 2 (Light)"
        - "Hypertrophy (Moderate)"
        - "HIIT / Heavy (High)"
        """
        # HRV recovers or drops based on sleep and training load.
        # Baseline sleep is 7 hours.
        # Each hour above/below modifies HRV by ~5ms.
        sleep_multiplier = (sleep_hours - 7.0) * 5.0
        
        # Training load penalty
        workout_penalties = {
            "Rest Day": 10.0,
            "Zone 2 (Light)": 2.0,
            "Hypertrophy (Moderate)": -5.0,
            "HIIT / Heavy (High)": -15.0
        }
        workout_penalty = workout_penalties.get(workout_intensity, 0.0)
        
        predicted_change = sleep_multiplier + workout_penalty
        projected_hrv_tomorrow = max(30.0, min(120.0, current_hrv + predicted_change))
        
        # Calculate estimate for full recovery (projecting forward assuming 8h sleep and rest days)
        deficit = target_hrv - current_hrv
        days_needed = 0
        
        if projected_hrv_tomorrow < target_hrv:
            temp_hrv = projected_hrv_tomorrow
            while temp_hrv < target_hrv and days_needed < 7:
                days_needed += 1
                # Project subsequent recovery days assuming 8h sleep (+5ms) and rest day (+10ms)
                # However, decay the recovery rate slightly as they approach baseline
                temp_hrv += 8.0  
                
        return {
            "current_hrv": current_hrv,
            "target_hrv": target_hrv,
            "deficit": deficit,
            "projected_hrv_tomorrow": projected_hrv_tomorrow,
            "projected_change": predicted_change,
            "days_to_recovery": days_needed
        }
