import numpy as np
import pyvisa
import time
import sys
from multiprocessing import Process

sys.path.insert(1, 'C:/Users/microspheres/Documents/Nanosphere github/nanospheres')

import DAQ.picoscope_utils.Picoscope_control as pico
import Control.src.RIGOL_control.DG822.DG822_control as rig

"""
Turns on HV source for needle to create plasma in chamber and change the charge state of the sphere.
Does this using pulses to make it more controllable - just turning it on makes it too messy.
Will only work in the 1 - 10 mbar pressure range.
"""

def DAQ_stream(x):
    
    print(x)
    
def pulse_and_sin_run(x):
    
    print(x)



# For paralellisation 



# Actually running
if __name__ == '__main__':

    ####
    #
    # Variables
    #
    ####

    # Pulse

    VOLT_PULSE = 4000      # Voltage one wants on the needle.
                # There will be a minimum below which it will not ionise the air. 
                # I think this probably also maxes out around 1 kV as it can't supply more current.
    FREQ_PULSE = 0.2

    # Drive

    VOLT_SIN = 3
    FREQ_SIN = 30000

    # Picoscope

    channels = ['D'] # 'A' is photodiode, 'B' is drive signal, 'C' is HV control signal, 'D' is lock-in signal
    file_length = 10 # time length in seconds
    sampleInterval = 1
    sampleUnit = 'MS' # ["S", "MS", "US", "NS "] are options
    multiplier = {'S':1, 'MS':1000, 'US':1000000, 'NS': 1000000000}
    ranges = {'D':1} # 1: 10 mV, 2: 20 mV, 3: 50 mV, 4: 100 mV, 5: 200 mV, 6: 500 mV, 7: 1 V, 8: 2 V, 9: 5 V, 10: 10 V, 11: 20 V, 12: 50 V

    totalSamples =  int(file_length*multiplier[sampleUnit]/sampleInterval) # total number of points in single file
    buffer_num = 1 # number of buffers, it will shift data every buffer. 1 is fine for this application
    buffersize = int(totalSamples/buffer_num)

    filename = 'D:/Experiment/Calibration/20241216/Particle 1/Charge_change_after_initial_charge.hdf5' # for saving data


    ### Don't change unless error with these values (e.g. does not connect)
    ### Can find out what the value should be using the following lines. You will have to figure out which resource is which instrument
    # rm = pyvisa.ResourceManager()
    # rm.list_resources()

    _VISA_ADDRESS_rigol = 'USB0::0x1AB1::0x0643::DG8A261500548::INSTR'

    ####
    #
    # Initialising classes
    #
    ####

    DG822 = rig.FuncGen(_VISA_ADDRESS_rigol)

    control_voltage = VOLT_PULSE/500

    DG822.sin_wave(channel = 1, amp=VOLT_SIN, freq=FREQ_SIN, )
    DG822.pulse(channel = 2, amp=control_voltage, duty=4, freq=FREQ_PULSE, off=control_voltage/2)
    #DG822.pulse(amp=VOLT, duty=50, freq=FREQ_PULSE, off=-VOLT/2)

    #DAQ = pico.PicoScope(channels, buffersize, sampleInterval, sampleUnit, totalSamples, ranges)
    print('bloop')
    # Ouput signals
    print('Bleep bloop')
    p1 = Process(target=DAQ_stream, args = [1])
    print('here')
    p2 = Process(target=pulse_and_sin_run, args = [2])

    p1.start()
    time.sleep(5)
    p2.start()
    print('here2')
    p1.join()
    p2.join()
    print('here3')


    #DAQ.save_data_hdf5(filename, {'data':DAQ.buffersComplete[0]})
    #DAQ.stop()
    #DAQ.close()

    print('Program ends')