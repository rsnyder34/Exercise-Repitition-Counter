import serial
import time

PORT = "COM4"
BAUDRATE = 9600

print(f"Attempting to connect to {PORT}...")
try:
    ser = serial.Serial(PORT, BAUDRATE, timeout=2)
    time.sleep(2)
    print("Connected! Waiting for data...\n")
    
    while True:
        if ser.in_waiting > 0:
            raw_data = ser.readline().decode('utf-8', errors='ignore').strip()
            print(raw_data)
            
except Exception as e:
    print(f"Error: {e}")