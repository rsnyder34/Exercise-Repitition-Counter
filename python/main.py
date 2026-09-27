import time
import collections
from parse import parse_mpu6050

PORT = "COM3"
BAUDRATE = 115200

# Algorithm Parameters
WINDOW_SIZE = 175      
MIN_AMPLITUDE = 3.0    

# State Variables
history = collections.deque(maxlen=WINDOW_SIZE)
in_rep_motion = False
rep_count = 0
rep_start_time = 0.0

if __name__ == "__main__":
    print("Connecting to Arduino... please wait.")
    
    for data in parse_mpu6050(PORT, BAUDRATE):
        x = data["accel"]["x"]
        y = data["accel"]["y"]
        z = data["accel"]["z"]

        # Coordinates -> 3D vector 
        magnitude = (x**2 + y**2 + z**2)**0.5
        history.append(magnitude)
        
        # DEBUG PRINT:
        print(f"Mag: {magnitude:.2f} m/s^2 | Buffer: {len(history)}/{WINDOW_SIZE} | Reps: {rep_count}")
        
        # Wait until sliding window is completely full
        if len(history) < WINDOW_SIZE:
            continue
            
        local_max = max(history)
        local_min = min(history)
        amplitude = local_max - local_min
        
        if amplitude > MIN_AMPLITUDE:
            dynamic_upper = local_min + (amplitude * 0.75)
            dynamic_lower = local_min + (amplitude * 0.25)
            
            if not in_rep_motion and magnitude > dynamic_upper:
                in_rep_motion = True
                rep_start_time = time.time()
                print(">>> MOVEMENT STARTED <<<") 
                
            elif in_rep_motion and magnitude < dynamic_lower:
                in_rep_motion = False
                rep_count += 1
                rep_duration = time.time() - rep_start_time
                print(f"*** REP {rep_count} COMPLETE! *** (Duration: {rep_duration:.2f}s)")