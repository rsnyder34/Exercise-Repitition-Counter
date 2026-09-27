# Real-Time Exercise Repetition Counter

An embedded hardware-software system that tracks and counts physical exercise repetitions in real time using an Arduino Uno, an MPU-6050 6-axis accelerometer/gyroscope, and a custom Python serial visualization GUI.

---

## Features
- **Real-Time Sensor Processing:** Samples 3D vector magnitude at 50Hz via I2C communication (20ms Arduino loop delay).
- **Hysteresis State Machine:** Implements a robust two-threshold filtering algorithm (`MIN_AMPLITUDE` noise gate at `3.0 m/s²`) to eliminate false triggers and ghosting.
- **Dynamic Sliding Window:** Utilizes `collections.deque` (150-sample buffer) in Python for smooth data stream analysis and visualization.
- **Live GUI Output:** Visualizes repetition counts, peaks, and movement thresholds dynamically over Serial.

---

## Tech Stack & Hardware
* **Microcontroller:** Arduino Uno
* **Sensor:** MPU-6050 Accelerometer/Gyroscope
* **Embedded Firmware:** C++ (Arduino IDE)
  * Libraries: `Adafruit_MPU6050`, `Adafruit_Unified_Sensor`, `Wire`
* **Desktop Interface:** Python 3
  * Libraries: `pyserial`, `matplotlib` (or your GUI framework)

---

## Repository Structure
```text
├── arduino/
│   └── rep_counter.ino       # Firmware for I2C data acquisition & thresholding
├── python/
│   └── gui_visualizer.py     # Python script for serial parsing & real-time plotting
└── README.md