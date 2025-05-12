from pylablib.devices import Thorlabs
import time
import sys
sys.path.insert(1, r'C:\Users\yuhan\nanospheres\control\src\Red_pitaya_control')
import redpitaya_control as rpc
import numpy as np


try:
    print("Begin autobalancing")
    # Connect to k-cube

    stage = Thorlabs.KinesisMotor('27007228')

    # Connect to red pitaya
    # IP address can change so double check which IP address is for rp-ba55. The red pitaya connection is dodgy so won't always connect
    # through web browser but haven't had any problems doing SCPI connection with IP address

    IP_rp = '169.254.240.122'
    rp = rpc.RedPitaya(IP_rp)

    while True:
        z_data = rp.acquire_data_now()
        zmean = np.mean(z_data)
        if zmean > 2:
            print('Jogging +')
            stage.jog('+')
            time.sleep(2)
            stage.stop()

        elif zmean < -2:
            print('Jogging -')
            stage.jog('-')
            time.sleep(2)
            stage.stop()
        
        else:
            time.sleep(2)

except KeyboardInterrupt:
    print("Program interrupted by user")

finally:
    stage.close()
    rp.close()
    print("Stage and red pitaya closed.")
    print("End autobalancing")