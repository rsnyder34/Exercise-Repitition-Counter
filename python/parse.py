import re
import time
import serial

# Update to match your port ('COM3', 'COM4' on Windows; '/dev/ttyUSB0', '/dev/ttyACM0' on Linux/Mac)
PORT = "COM3"
BAUDRATE = 115200

# Regex patterns matching your Arduino Serial output format
ACCEL_REGEX = re.compile(
    r"Acceleration X:\s*([-\d.]+),\s*Y:\s*([-\d.]+),\s*Z:\s*([-\d.]+)"
)
GYRO_REGEX = re.compile(
    r"Rotation X:\s*([-\d.]+),\s*Y:\s*([-\d.]+),\s*Z:\s*([-\d.]+)"
)
TEMP_REGEX = re.compile(r"Temperature:\s*([-\d.]+)")


def parse_mpu6050(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Pause to allow Arduino to reset on connection
        print(f"Connected to {port} at {baudrate} baud.\n")

        frame = {}

        while True:
            if ser.in_waiting > 0:
                line = (
                    ser.readline().decode("utf-8", errors="ignore").strip()
                )

                # 1. Match Acceleration
                accel_match = ACCEL_REGEX.search(line)
                if accel_match:
                    frame["accel"] = {
                        "x": float(accel_match.group(1)),
                        "y": float(accel_match.group(2)),
                        "z": float(accel_match.group(3)),
                    }
                    continue

                # 2. Match Gyroscope
                gyro_match = GYRO_REGEX.search(line)
                if gyro_match:
                    frame["gyro"] = {
                        "x": float(gyro_match.group(1)),
                        "y": float(gyro_match.group(2)),
                        "z": float(gyro_match.group(3)),
                    }
                    continue

                # 3. Match Temperature
                temp_match = TEMP_REGEX.search(line)
                if temp_match:
                    frame["temp"] = float(temp_match.group(1))

                    # Yield complete frame once all sensor groups are populated
                    if "accel" in frame and "gyro" in frame:
                        yield frame
                        frame = {}  # Clear for next loop

    except serial.SerialException as e:
        print(f"Serial port error: {e}")
    except KeyboardInterrupt:
        print("\nStopping reader.")
    finally:
        if "ser" in locals() and ser.is_open:
            ser.close()

