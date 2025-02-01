#include <VarSpeedServo.h>

#define BAS_SERVO 3
#define SHL_SERVO 5
#define ELB_SERVO 6
#define WRI_SERVO 9
#define WRO_SERVO 10
#define GRI_SERVO 11

VarSpeedServo servo1, servo2, servo3, servo4, servo5, servo6;
int servoSpeed = 35;
int gripperGripSpeed = 15;     // Faster but still safe speed for gripping
int gripperReleaseSpeed = 30;  // Fast speed for release
bool isGripping = false;

const int GRIPPER_OPEN = 23;   // Open position (release)
const int GRIPPER_CLOSE = 85;  // Fully closed position
const int GRIPPER_MIN = 25;    // Minimum safe closing angle

void setup() {
    servo1.attach(BAS_SERVO, 544, 2400);
    servo2.attach(SHL_SERVO, 544, 2400);
    servo3.attach(ELB_SERVO, 544, 2400);
    servo4.attach(WRI_SERVO, 544, 2400);
    servo5.attach(WRO_SERVO, 544, 2400);
    servo6.attach(GRI_SERVO, 544, 2400);
    
    // Initialize gripper to closed position
    servo6.write(GRIPPER_CLOSE, gripperGripSpeed);
    
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
                if (angle == -1) {  // Command to release grip
                    servo6.write(GRIPPER_OPEN, gripperReleaseSpeed);  // Open position (23 degrees) - fast
                    isGripping = false;
                    Serial.println("Gripper released");
                }
                else if (angle == -2) {  // Command to start gripping
                    isGripping = true;
                    adaptiveGrip();
                }
                else {
                    // Ensure angle is within safe range
                    int safeAngle = constrain(angle, GRIPPER_OPEN, GRIPPER_CLOSE);
                    servo6.write(safeAngle, gripperGripSpeed);
                    Serial.print("Servo 6 set to ");
                    Serial.println(safeAngle);
                }
                break;
            default:
                Serial.println("Invalid servo number");
                break;
        }
    }
}

void adaptiveGrip() {
    // Start from open position - use fast speed for opening
    servo6.write(GRIPPER_OPEN, gripperReleaseSpeed);
    delay(500);  // Reduced delay since we're moving faster
    
    // Slowly close until resistance is met or minimum angle reached
    for (int angle = GRIPPER_OPEN; angle <= GRIPPER_CLOSE; angle++) {
        servo6.write(angle, gripperGripSpeed);
        delay(50);  // Reduced delay between movements for faster operation while still maintaining control
        
        
        // Stop if maximum closing angle reached
        if (angle >= GRIPPER_CLOSE) {
            break;
        }
    }
    Serial.println("Grip complete");
}