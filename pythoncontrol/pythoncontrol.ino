#include <VarSpeedServo.h>

// Pin definitions
#define BAS_SERVO 3
#define SHL_SERVO 5
#define ELB_SERVO 6
#define WRI_SERVO 9
#define WRO_SERVO 10
#define GRI_SERVO 11

// Servo objects
VarSpeedServo servo1, servo2, servo3, servo4, servo5, servo6;

// Configurable parameters
int servoSpeed = 35;           // Default speed for regular movements
int interpolationDelay = 60;   // Delay between interpolation steps (ms)
int gripperGripSpeed = 50;     // Speed for gripping
int gripperReleaseSpeed = 30;  // Speed for release

// Gripper constants
#define GRIPPER_OPEN  37
#define GRIPPER_CLOSE  70  // Fixed close position
#define GRIPPER_SAFE_CLOSE 78  // Slightly less than GRIPPER_CLOSE for safety

void setup() {
    // Initialize all servos
    servo1.attach(BAS_SERVO, 544, 2400);
    servo2.attach(SHL_SERVO, 544, 2400);
    servo3.attach(ELB_SERVO, 544, 2400);
    servo4.attach(WRI_SERVO, 544, 2400);
    servo5.attach(WRO_SERVO, 544, 2400);
    servo6.attach(GRI_SERVO, 544, 2400);
    
    // Set initial angles
    servo1.write(84);
    servo2.write(77);
    servo3.write(164);
    servo4.write(40);
    servo5.write(90);
    
    // Initialize gripper to open position
    servo6.write(GRIPPER_OPEN);
    delay(1000);  // Allow time for the servo to reach position
    
    Serial.begin(9600);
    Serial.println("Robotic Arm Controller Started");
    Serial.println("Commands:");
    Serial.println("- Regular servo: [servo_number] [angle]");
    Serial.println("- Gripper: 6 -1 (release), 6 -2 (grip)");
    Serial.println("- Speed: s [speed] (5-255)");
    Serial.println("- Interpolation: i [delay_ms] (10-200)");
}

// Smooth movement function
void moveServoSmooth(VarSpeedServo& servo, int currentAngle, int targetAngle, int speed) {
    int step = (currentAngle < targetAngle) ? 1 : -1;
    
    for (int angle = currentAngle; angle != targetAngle; angle += step) {
        servo.write(angle, speed);
        delay(interpolationDelay);
    }
    servo.write(targetAngle, speed);
}

void loop() {
    if (Serial.available() > 0) {
        char firstChar = Serial.peek();
        
        // Check for special commands
        if (firstChar == 's' || firstChar == 'i') {
            String cmd = Serial.readStringUntil(' ');
            int value = Serial.parseInt();
            
            if (cmd == "s") {
                servoSpeed = constrain(value, 5, 255);
                Serial.print("Speed set to: ");
                Serial.println(servoSpeed);
            } else if (cmd == "i") {
                interpolationDelay = constrain(value, 10, 200);
                Serial.print("Interpolation delay set to: ");
                Serial.println(interpolationDelay);
            }
            return;
        }
        
        // Regular servo commands
        int servoNumber = Serial.parseInt();
        int angle = Serial.parseInt();
        Serial.read(); // Clear newline
        
        // Process command
        switch (servoNumber) {
            case 1:
            case 2:
            case 3:
            case 4:
            case 5: {
                VarSpeedServo* currentServo;
                switch(servoNumber) {
                    case 1: currentServo = &servo1; break;
                    case 2: currentServo = &servo2; break;
                    case 3: currentServo = &servo3; break;
                    case 4: currentServo = &servo4; break;
                    case 5: currentServo = &servo5; break;
                }
                
                int currentAngle = currentServo->read();
                angle = constrain(angle, 0, 180);
                
                Serial.print("Moving servo ");
                Serial.print(servoNumber);
                Serial.print(" from ");
                Serial.print(currentAngle);
                Serial.print(" to ");
                Serial.println(angle);
                
                moveServoSmooth(*currentServo, currentAngle, angle, servoSpeed);
                break;
            }
            
            case 6:
                if (angle == -1) {
                    Serial.println("Releasing gripper");
                    servo6.write(GRIPPER_OPEN, gripperReleaseSpeed);
                }
                else if (angle == -2) {
                    Serial.println("Closing gripper safely");
                    // First move to an intermediate position
                    servo6.write(GRIPPER_SAFE_CLOSE, gripperGripSpeed);
                    delay(500);  // Wait for movement
                    
                    // Then apply slightly more pressure but not maximum
                    servo6.write(GRIPPER_CLOSE, gripperGripSpeed/2);  // Use half speed for final grip
                }
                else {
                    int safeAngle = constrain(angle, GRIPPER_OPEN, GRIPPER_CLOSE);
                    Serial.print("Setting gripper to: ");
                    Serial.println(safeAngle);
                    servo6.write(safeAngle, gripperGripSpeed);
                }
                break;
                
            default:
                Serial.println("Invalid servo number");
                break;
        }
    }
}