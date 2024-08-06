#include <VarSpeedServo.h>

/* Servo names/numbers */
#define BAS_SERVO 4
#define SHL_SERVO 5
#define ELB_SERVO 6
#define WRI_SERVO 7
#define WRO_SERVO 8
#define GRI_SERVO 9

VarSpeedServo servo1, servo2, servo3, servo4, servo5, servo6;
int servoSpeed = 20;

void setup() {
    servo1.attach(BAS_SERVO, 544, 2400);
    servo2.attach(SHL_SERVO, 544, 2400);
    servo3.attach(ELB_SERVO, 544, 2400);
    servo4.attach(WRI_SERVO, 544, 2400);
    servo5.attach(WRO_SERVO, 544, 2400);
    servo6.attach(GRI_SERVO, 544, 2400);

    Serial.begin(9600);
    Serial.println("Start");
    Serial.println("Ready to receive servo commands.");
}

void loop() {
    if (Serial.available() > 0) {
        int servoNumber = Serial.parseInt();
        int angle = Serial.parseInt();
        Serial.read();  // Clear the newline character

        switch (servoNumber) {
            case 1:
                servo1.write(angle, servoSpeed);
                Serial.print("Servo 1 set to ");
                Serial.println(angle);
                break;
            case 2:
                servo2.write(angle, servoSpeed);
                Serial.print("Servo 2 set to ");
                Serial.println(angle);
                break;
            case 3:
                servo3.write(angle, servoSpeed);
                Serial.print("Servo 3 set to ");
                Serial.println(angle);
                break;
            case 4:
                servo4.write(angle, servoSpeed);
                Serial.print("Servo 4 set to ");
                Serial.println(angle);
                break;
            case 5:
                servo5.write(angle, servoSpeed);
                Serial.print("Servo 5 set to ");
                Serial.println(angle);
                break;
            case 6:
                servo6.write(angle, servoSpeed);
                Serial.print("Servo 6 set to ");
                Serial.println(angle);
                break;
            default:
                Serial.println("Invalid servo number");
                break;
        }
    }
}
