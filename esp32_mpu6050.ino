#include <Wire.h>
#include <MPU6050_light.h>

MPU6050 mpu(Wire);

void setup() {
  Serial.begin(115200);
  delay(3000);

  Wire.begin(19, 22);     // SDA, SCL
  Wire.setClock(100000); // Safe I2C speed

  Serial.println("Initializing MPU6050...");
  byte status = mpu.begin();

  if (status != 0) {
    Serial.print("MPU init failed with code ");
    Serial.println(status);
    while (1);
  }

  Serial.println("✅ MPU6050 Found!");
  Serial.println("Calibrating...");
  delay(1000);
  mpu.calcOffsets(true, true); // gyro + accel
  Serial.println("Calibration done");
}

void loop() {
  mpu.update();

  Serial.print("Pitch: ");
  Serial.print(mpu.getAngleX());
  Serial.print(" | Roll: ");
  Serial.print(mpu.getAngleY());
  Serial.print(" | Yaw: ");
  Serial.println(mpu.getAngleZ());

  delay(200);
}
