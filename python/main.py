import time
import collections
import threading
import queue
import csv
import os
import json
from datetime import datetime
import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from parse import parse_mpu6050

PORT = "COM4" 
BAUDRATE = 9600
USER_WEIGHT_KG = 77.0 

EXERCISE_PROFILES = {
    "Bicep Curls (Standard)": {"window": 150, "amplitude": 3.0, "type": "Rep", "met": 3.0},
    "Squats (Slow/Heavy)": {"window": 250, "amplitude": 2.0, "type": "Rep", "met": 6.0},
    "Kettlebell Swings (Explosive)": {"window": 100, "amplitude": 6.0, "type": "Rep", "met": 8.0},
    "Push-ups (Bodyweight)": {"window": 175, "amplitude": 2.5, "type": "Rep", "met": 3.8},
    "Walking (Waist/Pocket)": {"window": 50, "amplitude": 1.5, "type": "Step", "met": 3.5},
    "Running (Waist/Pocket)": {"window": 35, "amplitude": 4.0, "type": "Step", "met": 9.8}
}

FILE_PATH = "saved_plans.json"

def load_or_create_plans():
    if not os.path.exists(FILE_PATH):
        default_plans = {
            "Grappling Conditioning Circuit": [
                {"exercise": "Kettlebell Swings (Explosive)", "target": 25},
                {"exercise": "Push-ups (Bodyweight)", "target": 25}
            ]
        }
        with open(FILE_PATH, "w") as f:
            json.dump(default_plans, f, indent=4)
        return default_plans
    
    with open(FILE_PATH, "r") as f:
        return json.load(f)

class MotionTrackerPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Motion Tracker Pro")
        self.geometry("550x850")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Core State Variables
        self.workout_plans = load_or_create_plans()
        self.current_plan_name = list(self.workout_plans.keys())[0] if self.workout_plans else ""
        self.current_step_index = 0
        self.active_exercise = "Bicep Curls (Standard)"
        self.target_reps = 0
        self.tracking_mode = "Freestyle" 
        self.is_paused = False

        self.total_calories = 0.0 
        self.session_rep_count = 0 

        # Initialize CSV Log
        self.log_file = "workout_log.csv"
        if not os.path.exists(self.log_file):
            with open(self.log_file, mode='w', newline='') as f:
                csv.writer(f).writerow(["Timestamp", "Mode/Plan", "Exercise", "Type", "Duration (sec)", "Calories Burned", "Session Total Calories"])

        # Tabview Setup
        self.tabview = ctk.CTkTabview(self, command=self.on_tab_change, width=500, height=800)
        self.tabview.pack(pady=10, padx=10, expand=True, fill="both")
        
        self.tab_tracker = self.tabview.add("Live Tracker")
        self.tab_builder = self.tabview.add("Plan Builder")

        self.setup_tracker_tab()
        self.setup_builder_tab()

        # Threading Setup
        self.data_queue = queue.Queue()
        self.profile_update_flag = False  
        
        self.sensor_thread = threading.Thread(target=self.sensor_loop, daemon=True)
        self.sensor_thread.start()
        self.check_queue()

    def setup_tracker_tab(self):
        self.mode_selector = ctk.CTkSegmentedButton(
            self.tab_tracker, 
            values=["Freestyle", "Workout Plan"], 
            command=self.on_mode_change,
            font=("Arial", 14)
        )
        self.mode_selector.set("Freestyle")
        self.mode_selector.pack(pady=(10, 15))

        self.exercise_menu = ctk.CTkOptionMenu(
            self.tab_tracker, 
            values=list(EXERCISE_PROFILES.keys()),
            command=self.on_freestyle_change,
            font=("Arial", 16),
            width=300
        )
        self.exercise_menu.pack(pady=5)

        self.plan_menu = ctk.CTkOptionMenu(
            self.tab_tracker, 
            values=list(self.workout_plans.keys()) if self.workout_plans else ["No Plans Saved"],
            command=self.on_plan_change,
            font=("Arial", 16),
            width=300
        )

        self.exercise_label = ctk.CTkLabel(self.tab_tracker, text=f"Current: {self.active_exercise}", font=("Arial", 16, "bold"), text_color="#1DB954")
        self.exercise_label.pack(pady=5)

        self.status_label = ctk.CTkLabel(self.tab_tracker, text="Connecting...", font=("Arial", 20))
        self.status_label.pack(pady=5)

        # Graph Setup
        self.fig, self.ax = plt.subplots(figsize=(5, 2.5), facecolor='#242424')
        self.ax.set_facecolor('#242424')
        self.ax.tick_params(colors='gray')
        self.ax.spines['bottom'].set_color('gray')
        self.ax.spines['left'].set_color('gray') 
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)

        self.max_window = 250
        self.x_data = np.arange(0, self.max_window)
        self.y_data = np.zeros(self.max_window)
        

        self.line, = self.ax.plot(self.x_data, self.y_data, color='#1DB954', linewidth=2)
        
        self.ax.set_ylim(0, 25) 
        self.ax.set_xlim(0, self.max_window)
        self.ax.set_xticks([]) 

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_tracker)
        self.canvas.get_tk_widget().pack(pady=10)

        self.rep_label = ctk.CTkLabel(self.tab_tracker, text="0", font=("Arial", 60, "bold"), text_color="#1DB954")
        self.rep_label.pack(pady=5)

        self.duration_label = ctk.CTkLabel(self.tab_tracker, text="Last Rep: -- sec", font=("Arial", 16))
        self.duration_label.pack(pady=5)

        self.calorie_label = ctk.CTkLabel(self.tab_tracker, text="Calories: 0.00", font=("Arial", 18, "bold"), text_color="#FF5722")
        self.calorie_label.pack(pady=5)

    def setup_builder_tab(self):
        self.builder_sequence = []

        title_label = ctk.CTkLabel(self.tab_builder, text="Create New Workout Plan", font=("Arial", 20, "bold"))
        title_label.pack(pady=(20, 10))

        self.plan_name_entry = ctk.CTkEntry(self.tab_builder, placeholder_text="Plan Name", width=300)
        self.plan_name_entry.pack(pady=10)

        self.b_exercise_dropdown = ctk.CTkOptionMenu(self.tab_builder, values=list(EXERCISE_PROFILES.keys()), width=300)
        self.b_exercise_dropdown.pack(pady=10)

        self.b_target_entry = ctk.CTkEntry(self.tab_builder, placeholder_text="Target Reps/Steps", width=300)
        self.b_target_entry.pack(pady=10)

        self.add_btn = ctk.CTkButton(self.tab_builder, text="Add to Sequence", command=self.add_to_sequence, width=300)
        self.add_btn.pack(pady=15)

        self.display_box = ctk.CTkTextbox(self.tab_builder, width=350, height=200)
        self.display_box.pack(pady=10)
        self.display_box.insert("end", "Current Sequence:\n------------------\n")
        self.display_box.configure(state="disabled")

        self.save_btn = ctk.CTkButton(self.tab_builder, text="Save & Refresh Tracker", command=self.save_and_refresh, width=300, fg_color="#1DB954")
        self.save_btn.pack(pady=15)
        
        self.b_status_label = ctk.CTkLabel(self.tab_builder, text="", text_color="gray")
        self.b_status_label.pack(pady=5)

    def on_tab_change(self):
        current_tab = self.tabview.get()
        if current_tab == "Live Tracker":
            self.is_paused = False
            self.profile_update_flag = True 
            self.status_label.configure(text="Resuming...")
        else:
            self.is_paused = True

    def on_mode_change(self, mode):
        self.tracking_mode = mode
        self.session_rep_count = 0
        self.profile_update_flag = True
        
        if mode == "Freestyle":
            self.plan_menu.pack_forget()
            self.exercise_menu.pack(pady=5, after=self.mode_selector)
            self.active_exercise = self.exercise_menu.get()
            self.exercise_label.configure(text=f"Current: {self.active_exercise}")
            self.rep_label.configure(text="0")
        else:
            self.exercise_menu.pack_forget()
            self.plan_menu.pack(pady=5, after=self.mode_selector)
            if self.workout_plans:
                self.on_plan_change(self.current_plan_name)

    def on_freestyle_change(self, choice):
        self.active_exercise = choice
        self.session_rep_count = 0 
        self.profile_update_flag = True
        self.exercise_label.configure(text=f"Current: {self.active_exercise}")
        self.rep_label.configure(text="0")

    def on_plan_change(self, choice):
        if not self.workout_plans: return
        self.current_plan_name = choice
        self.current_step_index = 0
        self.active_exercise = self.workout_plans[self.current_plan_name][self.current_step_index]["exercise"]
        self.target_reps = self.workout_plans[self.current_plan_name][self.current_step_index]["target"]
        self.session_rep_count = 0 
        self.profile_update_flag = True  

        self.exercise_label.configure(text=f"Current: {self.active_exercise}")
        self.rep_label.configure(text=f"0 / {self.target_reps}")

    def add_to_sequence(self):
        exercise = self.b_exercise_dropdown.get()
        target_str = self.b_target_entry.get()
        if not target_str.isdigit() or int(target_str) <= 0: return

        self.builder_sequence.append({"exercise": exercise, "target": int(target_str)})
        self.display_box.configure(state="normal")
        self.display_box.insert("end", f"[{len(self.builder_sequence)}] {exercise} - {target_str} Reps/Steps\n")
        self.display_box.configure(state="disabled")
        self.b_target_entry.delete(0, 'end')

    def save_and_refresh(self):
        plan_name = self.plan_name_entry.get().strip()
        if not plan_name or not self.builder_sequence: return

        self.workout_plans[plan_name] = self.builder_sequence
        with open(FILE_PATH, "w") as f:
            json.dump(self.workout_plans, f, indent=4)

        self.plan_menu.configure(values=list(self.workout_plans.keys()))
        if not self.current_plan_name: 
            self.current_plan_name = plan_name
            self.plan_menu.set(plan_name)

        self.b_status_label.configure(text=f"Saved! Ready in Tracker.", text_color="#1DB954")
        self.builder_sequence = []
        self.plan_name_entry.delete(0, 'end')
        self.display_box.configure(state="normal")
        self.display_box.delete("1.0", "end")
        self.display_box.insert("end", "Current Sequence:\n------------------\n")
        self.display_box.configure(state="disabled")

    def sensor_loop(self):
        window_size = EXERCISE_PROFILES[self.active_exercise]["window"]
        min_amp = EXERCISE_PROFILES[self.active_exercise]["amplitude"]
        history = collections.deque(maxlen=window_size)
        
        in_rep_motion = False
        rep_start_time = 0.0
        graph_update_throttle = 0 # Prevents GUI lag from rapid plotting

        try:
            for data in parse_mpu6050(PORT, BAUDRATE):
                if self.is_paused:
                    time.sleep(0.1)
                    continue

                if self.profile_update_flag:
                    window_size = EXERCISE_PROFILES[self.active_exercise]["window"]
                    min_amp = EXERCISE_PROFILES[self.active_exercise]["amplitude"]
                    history = collections.deque(maxlen=window_size)
                    in_rep_motion = False
                    self.profile_update_flag = False
                    self.data_queue.put({"type": "status", "value": "Re-calibrating..."})
                    
                    self.data_queue.put({"type": "resize_graph", "value": window_size})
                    continue 

                x, y, z = data["accel"]["x"], data["accel"]["y"], data["accel"]["z"]
                magnitude = (x**2 + y**2 + z**2)**0.5
                history.append(magnitude)
                
                # Send graph data to UI at a controlled rate 
                graph_update_throttle += 1
                if graph_update_throttle % 3 == 0 and len(history) > 5:
                    self.data_queue.put({"type": "graph", "value": list(history)})
                
                if len(history) < window_size:
                    self.data_queue.put({"type": "status", "value": f"Calibrating: {len(history)}/{window_size}"})
                    continue
                
                if len(history) == window_size and not in_rep_motion:
                    self.data_queue.put({"type": "status", "value": "Ready!"})

                local_max, local_min = max(history), min(history)
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
                        
                        rep_calories = met_value * USER_WEIGHT_KG * (rep_duration / 3600.0)
                        self.total_calories += rep_calories
                        
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_plan_name = "Freestyle" if self.tracking_mode == "Freestyle" else self.current_plan_name
                        with open(self.log_file, mode='a', newline='') as f:
                            csv.writer(f).writerow([timestamp, log_plan_name, self.active_exercise, move_type, round(rep_duration, 2), round(rep_calories, 4), round(self.total_calories, 2)])

                        if self.tracking_mode == "Freestyle":
                            self.data_queue.put({"type": "rep", "value": f"{self.session_rep_count}"})
                        else:
                            self.data_queue.put({"type": "rep", "value": f"{self.session_rep_count} / {self.target_reps}"})
                            
                        self.data_queue.put({"type": "duration", "value": f"Last {move_type}: {rep_duration:.2f} sec"})
                        self.data_queue.put({"type": "calories", "value": f"Calories: {self.total_calories:.2f}"})
                        self.data_queue.put({"type": "status", "value": "Ready!"})

                        if self.tracking_mode == "Workout Plan" and self.session_rep_count >= self.target_reps:
                            self.current_step_index += 1
                            plan_sequence = self.workout_plans[self.current_plan_name]
                            
                            if self.current_step_index < len(plan_sequence):
                                self.active_exercise = plan_sequence[self.current_step_index]["exercise"]
                                self.target_reps = plan_sequence[self.current_step_index]["target"]
                                self.session_rep_count = 0
                                self.profile_update_flag = True
                                
                                self.data_queue.put({"type": "exercise_label", "value": f"Current: {self.active_exercise}"})
                                self.data_queue.put({"type": "rep", "value": f"0 / {self.target_reps}"})
                                self.data_queue.put({"type": "status", "value": "Set Complete! Switching..."})
                            else:
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
            
            # Matplotlib GUI Updates
            elif msg["type"] == "resize_graph":
                new_window = msg["value"]
                self.max_window = new_window
                self.ax.set_xlim(0, new_window)
                self.x_data = np.arange(0, new_window)
                self.canvas.draw_idle()
                
            elif msg["type"] == "graph":
                history_list = msg["value"]
                padded_y = np.pad(history_list, (self.max_window - len(history_list), 0), 'constant', constant_values=0)
                
                # Prevent crashing if array shapes mismatch momentarily during a mode switch
                if len(padded_y) == len(self.x_data):
                    self.line.set_ydata(padded_y)
                    self.canvas.draw_idle()

        self.after(50, self.check_queue)

if __name__ == "__main__":
    app = MotionTrackerPro()
    app.mainloop()