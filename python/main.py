import time
import collections
import threading
import queue
import customtkinter as ctk
from parse import parse_mpu6050

PORT = "COM3"
BAUDRATE = 115200

# Define tuning params for different exercises
EXERCISE_PROFILES = {
    "Bicep Curls (Standard)": {"window": 150, "amplitude": 3.0},
    "Squats (Slow/Heavy)": {"window": 250, "amplitude": 2.0},
    "Kettlebell Swings (Explosive)": {"window": 100, "amplitude": 6.0},
    "Push-ups (Bodyweight)": {"window": 175, "amplitude": 2.5}
}

class RepCounterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Real-Time Rep Counter")
        self.geometry("450x450")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # UI Elements
        self.current_exercise = "Bicep Curls (Standard)"
        self.exercise_menu = ctk.CTkOptionMenu(
            self, 
            values=list(EXERCISE_PROFILES.keys()),
            command=self.on_exercise_change,
            font=("Arial", 16),
            width=250
        )
        self.exercise_menu.set(self.current_exercise)
        self.exercise_menu.pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="Connecting...", font=("Arial", 20))
        self.status_label.pack(pady=10)

        self.rep_label = ctk.CTkLabel(self, text="0", font=("Arial", 100, "bold"), text_color="#1DB954")
        self.rep_label.pack(pady=10)

        self.duration_label = ctk.CTkLabel(self, text="Last Rep: -- sec", font=("Arial", 20))
        self.duration_label.pack(pady=20)

        # Threading Setup
        self.data_queue = queue.Queue()
        self.profile_update_flag = False  
        
        self.sensor_thread = threading.Thread(target=self.sensor_loop, daemon=True)
        self.sensor_thread.start()
        self.check_queue()

    def on_exercise_change(self, choice):
        """Triggered automatically when the user selects a new dropdown option."""
        self.current_exercise = choice
        self.profile_update_flag = True  

        # Reset the UI counters
        self.rep_label.configure(text="0")
        self.duration_label.configure(text="Last Rep: -- sec")

    def sensor_loop(self):
        # Initial setup based on default selection
        window_size = EXERCISE_PROFILES[self.current_exercise]["window"]
        min_amp = EXERCISE_PROFILES[self.current_exercise]["amplitude"]
        history = collections.deque(maxlen=window_size)
        
        in_rep_motion = False
        rep_count = 0
        rep_start_time = 0.0

        try:
            for data in parse_mpu6050(PORT, BAUDRATE):
                if self.profile_update_flag:
                    window_size = EXERCISE_PROFILES[self.current_exercise]["window"]
                    min_amp = EXERCISE_PROFILES[self.current_exercise]["amplitude"]
                    
                    history = collections.deque(maxlen=window_size)
                    in_rep_motion = False
                    rep_count = 0
                    
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
                        self.data_queue.put({"type": "status", "value": "Lifting..."})

                    elif in_rep_motion and magnitude < dynamic_lower:
                        in_rep_motion = False
                        rep_count += 1
                        rep_duration = time.time() - rep_start_time
                        
                        self.data_queue.put({"type": "rep", "value": rep_count})
                        self.data_queue.put({"type": "duration", "value": f"Last Rep: {rep_duration:.2f} sec"})
                        self.data_queue.put({"type": "status", "value": "Ready!"})

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

        self.after(50, self.check_queue)

if __name__ == "__main__":
    app = RepCounterApp()
    app.mainloop()