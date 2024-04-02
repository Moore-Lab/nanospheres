import serial, time
import numpy as np

def check_if_stopped(n, arduino, write_stop=False):
    
    got_stop = False
    for i in range(n):
        cline = arduino.readline().decode()
        #print(cline)
        if("stop" not in cline):

            if(write_stop):
                didwrite = arduino.write(b"stop\n")
                arduino.reset_input_buffer()
            time.sleep(1)
        else:
            got_stop = True
            break
    
    return got_stop

def move_stage(mm_1, mm_2):

    arduino = serial.Serial(port='COM7', baudrate=9600, timeout=10)

    time.sleep(1)

    arduino.write(b"stop\n")
    time.sleep(0.5)

    got_stop = check_if_stopped(5, arduino, write_stop=True)
    if(not got_stop):
        print("Stage not stopped, failed to move")
        arduino.close()
        return False

    print("Moving by dX, dY: %.1f mm, %.1fmm"%(mm_1, mm_2))
    time.sleep(0.5)
    arduino.write(b"step:%.1f:%.1f\n"%(mm_1, mm_2))
    time.sleep(0.5)

    arduino.close()

    return True

