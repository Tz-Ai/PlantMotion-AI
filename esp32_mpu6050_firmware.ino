#include <Wire.h>
#include <MPU6050_light.h>

MPU6050 mpu(Wire);

void setup() {
  Serial.begin(115200);
  delay(3000);

  Wire.begin(19, 22);     // SDA, SCL
  Wire.setClock(100000); // Safe I2C speed

  byte status = mpu.begin();
  if (status != 0) {
    Serial.println(status);
    while (1);
  }

  delay(1000);
  mpu.calcOffsets(true, true); // gyro + accel
}

void loop() {
  mpu.update();

  // CSV output: Pitch,Roll
  Serial.print(mpu.getAccX());
  Serial.print(",");
  Serial.print(mpu.getAccY());
  Serial.print(",");
  Serial.println(mpu.getAccZ());


  delay(200);
}
