#include <AccelStepper.h>
#include <MultiStepper.h>

// Define pin relationships
#define PUL1_PIN    3
#define DIR1_PIN    2
#define PUL2_PIN    5
#define DIR2_PIN    4

#define MOTOR_INTERFACE_TYPE 1

// Use microstep configuration for smoother movement
// Using full step instead of microsteps if set to 1
// (might involve rewiring the motor control chip)
// #define MICROSTEPS 1
#define MICROSTEPS 8
#define STEPS_PER_REV 400
#define SPEED_MAX 1000

// For the function `taper`
int cycles = 500;
int increment_steps = 200;
int hot_zone_revs = 3;

// For the function `pull`
double pull_speed = 50;      // microsteps
double pull_length = 12.5;   // mm (on each side)

double mm_to_steps = 800 * MICROSTEPS;
double steps_to_mm = 0.00125 / MICROSTEPS;

enum Command {
    TEST,
    FLUSH,
    OSCILLATE,
    TAPER,
    PULL,
    STOP,
    STEP,
    NONE
};

Command get_command(String command) {
    Command ret;
    
    if (command.equals("flush")) { ret = FLUSH; }
    else if (command.equals("oscillate")) { ret = OSCILLATE; }
    else if (command.equals("taper")) { ret = TAPER; }
    else if (command.equals("pull")) { ret = PULL; }
    else if (command.equals("stop")) { ret = STOP; }
    else if (command.equals("step")) { ret = STEP; }
    else { ret = NONE; }

    return ret;
}

/*
 * Bring the stages back to their original positions
 * Might need manual adjustment before starting a new run
 */
void flush_steppers(MultiStepper &steppers, AccelStepper &stepper1, AccelStepper &stepper2, long (&step_count)[2]) {
    // Flush the steps back
    long positions[2] = {-1 * step_count[0], -1 * step_count[1]};

    stepper1.setMaxSpeed(SPEED_MAX * MICROSTEPS);  // (micro)steps per second
    stepper2.setMaxSpeed(SPEED_MAX * MICROSTEPS);
    
    stepper1.setCurrentPosition(0);
    stepper2.setCurrentPosition(0);

    steppers.moveTo(positions);
    steppers.runSpeedToPosition();

    // Reset the step count
    step_count[0] = 0;
    step_count[1] = 0;
}

void oscillate(MultiStepper &steppers, AccelStepper &stepper1, AccelStepper &stepper2, const int n_cycles, long (&step_count)[2]) {
    // Move 3 revolutions, or 1.5 mm
    long pos_plus[2]  = {3 * STEPS_PER_REV * MICROSTEPS, - 3 * STEPS_PER_REV * MICROSTEPS};  // target pos in steps
    long positions[2];

    stepper1.setMaxSpeed(SPEED_MAX * MICROSTEPS);  // steps per second
    stepper2.setMaxSpeed(SPEED_MAX * MICROSTEPS);
        
    for (int i=0; i < n_cycles * 2; i++) {
        positions[0] = i % 2 == 0 ? pos_plus[0] : pos_plus[1];
        positions[1] = i % 2 == 0 ? pos_plus[0] : pos_plus[1];

        // Set current positions as origin
        // and move forward/backward to the target positions
        stepper1.setCurrentPosition(0);
        stepper2.setCurrentPosition(0);

        // NOTE: speed is calculated according to the one fed to
        // `AccelStepper::setMaxSpeed()`
        steppers.moveTo(positions);
        steppers.runSpeedToPosition();  // Blocks until movement is done

        step_count[0] += positions[0];
        step_count[1] += positions[1];
        
        delay(100);
    }
}

void taper(MultiStepper &steppers, AccelStepper &stepper1, AccelStepper &stepper2, const int n_cycles, long (&step_count)[2]) {
    long pos_plus[2]  = {hot_zone_revs * STEPS_PER_REV * MICROSTEPS, - hot_zone_revs * STEPS_PER_REV * MICROSTEPS};
    long positions[2];  // target pos in steps

    stepper1.setMaxSpeed(SPEED_MAX * MICROSTEPS);  // steps per second
    stepper2.setMaxSpeed(SPEED_MAX * MICROSTEPS);
    
    for (int i=0; i < n_cycles * 2 + 2; i++) {
        if (i == 0) {
            positions[0] = pos_plus[0];
            positions[1] = pos_plus[0];
        }
        else if (i == 1) {
            positions[0] = pos_plus[1];
            positions[1] = pos_plus[1];
        }
        else {
            positions[0] = i % 2 == 0 ? pos_plus[0] : pos_plus[1] + increment_steps;
            positions[1] = i % 2 == 0 ? pos_plus[0] - increment_steps : pos_plus[1];
        }

        // Set current positions as origin
        // and move forward/backward to the target positions
        stepper1.setCurrentPosition(0);
        stepper2.setCurrentPosition(0);

        // NOTE: speed is calculated according to the max speed from
        // `AccelStepper::setMaxSpeed()`
        steppers.moveTo(positions);
        steppers.runSpeedToPosition();  // Blocks until movement is done

        step_count[0] += positions[0];
        step_count[1] += positions[1];
        
        delay(200);  // Delay for reversing the direction
    }
}

void pull(MultiStepper &steppers, AccelStepper &stepper1, AccelStepper &stepper2, long (&step_count)[2]) {
    delay(1000);
    
    // Total pull length will be (`pull_length` * 2) millimeters
    // Target pos in steps
    long positions[2];
    positions[0] = pull_length * mm_to_steps;
    positions[1] = - pull_length * mm_to_steps;

    stepper1.setMaxSpeed(pull_speed);  // steps per second
    stepper2.setMaxSpeed(pull_speed);

    stepper1.setCurrentPosition(0);
    stepper2.setCurrentPosition(0);

    steppers.moveTo(positions);
    steppers.runSpeedToPosition();  // Blocks until movement is done
    
    step_count[0] += positions[0];
    step_count[1] += positions[1];
}

void step_single(MultiStepper &steppers, AccelStepper &stepper1, AccelStepper &stepper2, long (&step_count)[2]) {
    // step a single motor
    
    delay(1000);
    
    // Total pull length will be (`pull_length` * 2) millimeters
    // Target pos in steps
    long positions[2];
    positions[0] = -2 * mm_to_steps;
    positions[1] = 0;
    pull_speed=1000;

    stepper1.setMaxSpeed(pull_speed);  // steps per second
    stepper2.setMaxSpeed(pull_speed);

    stepper1.setCurrentPosition(0);
    stepper2.setCurrentPosition(0);

    steppers.moveTo(positions);
    steppers.runSpeedToPosition();  // Blocks until movement is done
    
    step_count[0] += positions[0];
    step_count[1] += positions[1];
}

void stop_steppers(AccelStepper &stepper1, AccelStepper &stepper2) {
    stepper1.stop();
    stepper2.stop();
}

String getValue(String data, char separator, int index)
{
    int found = 0;
    int strIndex[] = { 0, -1 };
    int maxIndex = data.length() - 1;

    Serial.println("data: " + data);
    Serial.println("sep: " + separator);
    for (int i = 0; i <= maxIndex && found <= index; i++) {
        if (data.charAt(i) == separator || i == maxIndex) {
            found++;
            strIndex[0] = strIndex[1] + 1;
            strIndex[1] = (i == maxIndex) ? i+1 : i;
        }
    }
    return found > index ? data.substring(strIndex[0], strIndex[1]) : "";
}

//
// Main Program
//

String command, command_base, command_arg;
long step_count[2] = {0, 0};

AccelStepper stepper1 = AccelStepper(MOTOR_INTERFACE_TYPE, PUL1_PIN, DIR1_PIN);
AccelStepper stepper2 = AccelStepper(MOTOR_INTERFACE_TYPE, PUL2_PIN, DIR2_PIN);
MultiStepper steppers;

void setup() {
    Serial.begin(9600);
    
    stepper1.setMaxSpeed(SPEED_MAX * MICROSTEPS);  // steps per second
    stepper2.setMaxSpeed(SPEED_MAX * MICROSTEPS);

    steppers.addStepper(stepper1);
    steppers.addStepper(stepper2);
}

void loop() {
    // Initialize serial read function
    if (Serial.available()) {
        command = Serial.readStringUntil('\n');
        command.trim();
        command_base = getValue(command, ':', 0);
        command_arg = getValue(command, ':', 1);
    }

    delay(5000);
    Serial.println("command: " + command);
    Serial.println("base: " + command_base);
    Serial.println("command arg: " + command_arg);


    switch(get_command(command)) {
        case FLUSH:
            flush_steppers(steppers, stepper1, stepper2, step_count);
            command = "stop";
            break;
        case OSCILLATE:
            oscillate(steppers, stepper1, stepper2, cycles, step_count);
            command = "stop";
            break;
        case TAPER:
            taper(steppers, stepper1, stepper2, cycles, step_count);
            command = "stop";
            break;
        case PULL:
            pull(steppers, stepper1, stepper2, step_count);
            command = "stop";
            break;
        case STEP:
            step_single(steppers, stepper1, stepper2, step_count);
            command = "stop";
            break;
        case STOP:
            stop_steppers(stepper1, stepper2);
//            Serial.println("Done!");
//            Serial.println("Please reset the board");  // Is this necessary?
    }
}
