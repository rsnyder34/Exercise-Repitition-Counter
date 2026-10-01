import time
import collections
import threading
import queue
import customtkinter as ctk
from parse import parse_mpu6050

PORT = "COM3"
BAUDRATE = 115200

# Algorithm Params
WINDOW_SIZE = 175      
MIN_AMPLITUDE = 3.0    

class RepCounterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Real-Time Rep Counter")
        self.geometry("400x350")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # UI Config
        self.status_label = ctk.CTkLabel(self, text="Connecting...", font=("Arial", 20))
        self.status_label.pack(pady=20)

        self.rep_label = ctk.CTkLabel(self, text="0", font=("Arial", 100, "bold"), text_color="#1DB954")
        self.rep_label.pack(pady=10)

        self.duration_label = ctk.CTkLabel(self, text="Last Rep: -- sec", font=("Arial", 20))
        self.duration_label.pack(pady=20)

        # Thread Setup
        self.data_queue = queue.Queue()
        
        # Sensor loop in separate background thread
        self.sensor_thread = threading.Thread(target=self.sensor_loop, daemon=True)
        self.sensor_thread.start()

        # Start the GUI's queue-checking loop
        self.check_queue()

    def sensor_loop(self):
        # Updates for GUI
        history = collections.deque(maxlen=WINDOW_SIZE)
        in_rep_motion = False
        rep_count = 0
        rep_start_time = 0.0

        try:
            for data in parse_mpu6050(PORT, BAUDRATE):
                x = data["accel"]["x"]
                y = data["accel"]["y"]
                z = data["accel"]["z"]

                magnitude = (x**2 + y**2 + z**2)**0.5
                history.append(magnitude)
                
                # Update calibration 
                if len(history) < WINDOW_SIZE:
                    self.data_queue.put({"type": "status", "value": f"Calibrating: {len(history)}/{WINDOW_SIZE}"})
                    continue
                
                # Clear status once buffer is full
                if len(history) == WINDOW_SIZE and not in_rep_motion:
                    self.data_queue.put({"type": "status", "value": "Ready!"})

                local_max = max(history)
                local_min = min(history)
                amplitude = local_max - local_min

                if amplitude > MIN_AMPLITUDE:
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
                        
                        # Send the new data to the GUI
                        self.data_queue.put({"type": "rep", "value": rep_count})
                        self.data_queue.put({"type": "duration", "value": f"Last Rep: {rep_duration:.2f} sec"})
                        self.data_queue.put({"type": "status", "value": "Ready!"})

        except Exception as e:
            self.data_queue.put({"type": "status", "value": f"Disconnected/Error"})

    def check_queue(self):
        while not self.data_queue.empty():
            msg = self.data_queue.get()
            
            if msg["type"] == "status":
                self.status_label.configure(text=msg["value"])
            elif msg["type"] == "rep":
                self.rep_label.configure(text=str(msg["value"]))
            elif msg["type"] == "duration":
                self.duration_label.configure(text=msg["value"])

        # Schedule function to run again in 50 milliseconds
        self.after(50, self.check_queue)

if __name__ == "__main__":
    app = RepCounterApp()
    app.mainloop()