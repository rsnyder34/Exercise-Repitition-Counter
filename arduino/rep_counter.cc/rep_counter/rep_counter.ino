#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <SoftwareSerial.h> // 1. Include SoftwareSerial

// 2. Set up the Bluetooth serial port
// Pin 10 is Arduino RX (Connect to HC-05 TXD)
// Pin 11 is Arduino TX (Connect to HC-05 RXD through your voltage divider)
SoftwareSerial BTSerial(10, 11); 

Adafruit_MPU6050 mpu;

void setup(void) {
  // Keep the hardware serial at 115200 for USB debugging
  Serial.begin(115200);
  
  // 3. Start Bluetooth at 9600 baud (the factory default for HC-05)
  BTSerial.begin(9600); 
  
  while (!Serial)
    delay(10); 

  Serial.println("Adafruit MPU6050 test!");

  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1) {
      delay(10);
    }
  }
  Serial.println("MPU6050 Found!");

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  delay(100);
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // 4. Change Serial.print to BTSerial.print to send data wirelessly
  BTSerial.print("Acceleration X: ");
  BTSerial.print(a.acceleration.x);
  BTSerial.print(", Y: ");
  BTSerial.print(a.acceleration.y);
  BTSerial.print(", Z: ");
  BTSerial.print(a.acceleration.z);
  BTSerial.println(" m/s^2");

  BTSerial.print("Rotation X: ");
  BTSerial.print(g.gyro.x);
  BTSerial.print(", Y: ");
  BTSerial.print(g.gyro.y);
  BTSerial.print(", Z: ");
  BTSerial.print(g.gyro.z);
  BTSerial.println(" rad/s");

  BTSerial.print("Temperature: ");
  BTSerial.print(temp.temperature);
  BTSerial.println(" degC");

  BTSerial.println("");
  
  delay(20);
}