import time
import collections
import threading
import queue
import csv
import os
import json
from datetime import datetime
import customtkinter as ctk
from parse import parse_mpu6050

PORT = "COM4" 
BAUDRATE = 9600
USER_WEIGHT_KG = 65.0 

EXERCISE_PROFILES = {
    "Bicep Curls": {"window": 150, "amplitude": 3.0, "type": "Rep", "met": 3.0},
    "Squats": {"window": 250, "amplitude": 2.0, "type": "Rep", "met": 6.0},
    "Kettlebell Swings": {"window": 100, "amplitude": 6.0, "type": "Rep", "met": 8.0},
    "Push-ups": {"window": 175, "amplitude": 2.5, "type": "Rep", "met": 3.8},
    "Walking": {"window": 50, "amplitude": 1.5, "type": "Step", "met": 3.5},
    "Running": {"window": 35, "amplitude": 4.0, "type": "Step", "met": 9.8}
}

def load_or_create_plans():
    """Loads workout circuits from JSON, or creates a default file if missing."""
    file_path = "saved_plans.json"
    if not os.path.exists(file_path):
        default_plans = {
            "Free Track: Squats": [
                {"exercise": "Squats (Slow/Heavy)", "target": 999}
            ],
            "Grappling Conditioning Circuit": [
                {"exercise": "Kettlebell Swings (Explosive)", "target": 25},
                {"exercise": "Push-ups (Bodyweight)", "target": 25},
                {"exercise": "Squats (Slow/Heavy)", "target": 25}
            ]
        }
        with open(file_path, "w") as f:
            json.dump(default_plans, f, indent=4)
        return default_plans
    
    with open(file_path, "r") as f:
        return json.load(f)

class RepCounterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Motion Tracker Pro")
        self.geometry("450x550")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Load Plans and Setup Variables
        self.workout_plans = load_or_create_plans()
        self.current_plan_name = list(self.workout_plans.keys())[0]
        self.current_step_index = 0
        self.active_exercise = self.workout_plans[self.current_plan_name][self.current_step_index]["exercise"]
        self.target_reps = self.workout_plans[self.current_plan_name][self.current_step_index]["target"]

        # csv log Init
        self.log_file = "workout_log.csv"
        if not os.path.exists(self.log_file):
            with open(self.log_file, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Plan", "Exercise", "Type", "Duration (sec)", "Calories Burned", "Session Total Calories"])

        # UI Elements
        self.plan_menu = ctk.CTkOptionMenu(
            self, 
            values=list(self.workout_plans.keys()),
            command=self.on_plan_change,
            font=("Arial", 16),
            width=300
        )
        self.plan_menu.set(self.current_plan_name)
        self.plan_menu.pack(pady=20)

        self.exercise_label = ctk.CTkLabel(self, text=f"Current: {self.active_exercise}", font=("Arial", 16, "bold"), text_color="#1DB954")
        self.exercise_label.pack(pady=5)

        self.status_label = ctk.CTkLabel(self, text="Connecting...", font=("Arial", 20))
        self.status_label.pack(pady=10)

        self.rep_label = ctk.CTkLabel(self, text=f"0 / {self.target_reps}", font=("Arial", 80, "bold"), text_color="#1DB954")
        self.rep_label.pack(pady=10)

        self.duration_label = ctk.CTkLabel(self, text="Last Rep: -- sec", font=("Arial", 20))
        self.duration_label.pack(pady=15)

        self.calorie_label = ctk.CTkLabel(self, text="Calories: 0.00", font=("Arial", 20, "bold"), text_color="#FF5722")
        self.calorie_label.pack(pady=10)

        self.total_calories = 0.0 
        self.session_rep_count = 0 

        # Threading Setup
        self.data_queue = queue.Queue()
        self.profile_update_flag = False  
        
        self.sensor_thread = threading.Thread(target=self.sensor_loop, daemon=True)
        self.sensor_thread.start()
        self.check_queue()

    def on_plan_change(self, choice):
        """Resets the circuit when a new workout plan is selected from the dropdown."""
        self.current_plan_name = choice
        self.current_step_index = 0
        self.active_exercise = self.workout_plans[self.current_plan_name][self.current_step_index]["exercise"]
        self.target_reps = self.workout_plans[self.current_plan_name][self.current_step_index]["target"]
        
        self.session_rep_count = 0 
        self.profile_update_flag = True  

        self.exercise_label.configure(text=f"Current: {self.active_exercise}")
        self.rep_label.configure(text=f"0 / {self.target_reps}")
        self.duration_label.configure(text="Last Rep: -- sec")

    def sensor_loop(self):
        window_size = EXERCISE_PROFILES[self.active_exercise]["window"]
        min_amp = EXERCISE_PROFILES[self.active_exercise]["amplitude"]
        history = collections.deque(maxlen=window_size)
        
        in_rep_motion = False
        rep_start_time = 0.0

        try:
            for data in parse_mpu6050(PORT, BAUDRATE):
                if self.profile_update_flag:
                    window_size = EXERCISE_PROFILES[self.active_exercise]["window"]
                    min_amp = EXERCISE_PROFILES[self.active_exercise]["amplitude"]
                    
                    history = collections.deque(maxlen=window_size)
                    in_rep_motion = False
                    
                    self.profile_update_flag = False
                    self.data_queue.put({"type": "status", "value": "Re-calibrating..."})
                    continue 

                x = data["accel"]["x"]
                y = data["accel"]["y"]
                z = data["accel"]["z"]

                magnitude = (x**2 + y**2 + z**2)**0.5
                history.append(magnitude)
                
                if len(history) < window_size:
                    self.data_queue.put({"type": "status", "value": f"Calibrating: {len(history)}/{window_size}"})
                    continue
                
                if len(history) == window_size and not in_rep_motion:
                    self.data_queue.put({"type": "status", "value": "Ready!"})

                local_max = max(history)
                local_min = min(history)
                amplitude = local_max - local_min

                if amplitude > min_amp:
                    dynamic_upper = local_min + (amplitude * 0.75)
                    dynamic_lower = local_min + (amplitude * 0.25)

                    if not in_rep_motion and magnitude > dynamic_upper:
                        in_rep_motion = True
                        rep_start_time = time.time()
                        self.data_queue.put({"type": "status", "value": "Active..."})

                    elif in_rep_motion and magnitude < dynamic_lower:
                        in_rep_motion = False
                        self.session_rep_count += 1
                        rep_duration = time.time() - rep_start_time
                        
                        move_type = EXERCISE_PROFILES[self.active_exercise]["type"]
                        met_value = EXERCISE_PROFILES[self.active_exercise]["met"]
                        
                        # Calorie Math
                        duration_hours = rep_duration / 3600.0
                        rep_calories = met_value * USER_WEIGHT_KG * duration_hours
                        self.total_calories += rep_calories
                        
                        # Log to CSV
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with open(self.log_file, mode='a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([timestamp, self.current_plan_name, self.active_exercise, move_type, round(rep_duration, 2), round(rep_calories, 4), round(self.total_calories, 2)])

                        # Update GUI
                        self.data_queue.put({"type": "rep", "value": f"{self.session_rep_count} / {self.target_reps}"})
                        self.data_queue.put({"type": "duration", "value": f"Last {move_type}: {rep_duration:.2f} sec"})
                        self.data_queue.put({"type": "calories", "value": f"Calories: {self.total_calories:.2f}"})
                        self.data_queue.put({"type": "status", "value": "Ready!"})

                        # Auto-Advance Logic
                        if self.session_rep_count >= self.target_reps:
                            self.current_step_index += 1
                            plan_sequence = self.workout_plans[self.current_plan_name]
                            
                            if self.current_step_index < len(plan_sequence):
                                # Load next exercise in the circuit
                                self.active_exercise = plan_sequence[self.current_step_index]["exercise"]
                                self.target_reps = plan_sequence[self.current_step_index]["target"]
                                self.session_rep_count = 0
                                self.profile_update_flag = True
                                
                                self.data_queue.put({"type": "exercise_label", "value": f"Current: {self.active_exercise}"})
                                self.data_queue.put({"type": "rep", "value": f"0 / {self.target_reps}"})
                                self.data_queue.put({"type": "status", "value": "Set Complete! Switching..."})
                            else:
                                # Workout Finished
                                self.data_queue.put({"type": "status", "value": "Workout Complete!"})
                                self.data_queue.put({"type": "exercise_label", "value": "Done. Select a new plan."})

        except Exception as e:
            self.data_queue.put({"type": "status", "value": "Disconnected/Error"})

    def check_queue(self):
        while not self.data_queue.empty():
            msg = self.data_queue.get()
            if msg["type"] == "status":
                self.status_label.configure(text=msg["value"])
            elif msg["type"] == "rep":
                self.rep_label.configure(text=str(msg["value"]))
            elif msg["type"] == "duration":
                self.duration_label.configure(text=msg["value"])
            elif msg["type"] == "calories":
                self.calorie_label.configure(text=msg["value"])
            elif msg["type"] == "exercise_label":
                self.exercise_label.configure(text=msg["value"])

        self.after(50, self.check_queue)

if __name__ == "__main__":
    app = RepCounterApp()
    app.mainloop()