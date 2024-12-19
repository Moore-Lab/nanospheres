import numpy as np
import pyvisa
import time
import sys
from multiprocessing import Process

sys.path.insert(1, 'C:/Users/microspheres/Documents/Nanosphere github/nanospheres')

import DAQ.picoscope_utils.Picoscope_control as pico
import Control.src.RIGOL_control.DG822.DG822_control as rig

####
#
# Variables
#
####

# Harmonic

VOLT_SIN = 3
FREQ_SIN = 5000

# Picoscope

channels = ['A', 'B'] # 'A' is photodiode, 'B' is drive signal, 'C' is HV control signal, 'D' is lock-in signal
file_length = 20 # time length in seconds
sampleInterval = 1
sampleUnit = 'US' # ["S", "MS", "US", "NS "] are options
multiplier = {'S':1, 'MS':1000, 'US':1000000, 'NS': 1000000000}
ranges = {'A':9, 'B':9} # 0: 10 mV, 1: 20 mV, 2: 50 mV, 3: 100 mV, 4: 200 mV, 5: 500 mV, 6: 1 V, 7: 2 V, 8: 5 V, 9: 10 V, 10: 20 V, 11: 50 V

totalSamples =  int(file_length*multiplier[sampleUnit]/sampleInterval) # total number of points in single file
buffer_num = 1 # number of buffers, it will shift data every buffer. 1 is fine for this application
buffersize = int(totalSamples/buffer_num)

filename = 'D:/Experiment/Calibration/20241218/Particle 2/Field on2.hdf5' # for saving data
filename2 = 'D:/Experiment/Calibration/20241218/Particle 2/Field off2.hdf5' # for saving data


### Don't change unless error with these values (e.g. does not connect)
### Can find out what the value should be using the following lines. You will have to figure out which resource is which instrument
# rm = pyvisa.ResourceManager()
# rm.list_resources()

_VISA_ADDRESS_rigol = 'USB0::0x1AB1::0x0643::DG8A261500548::INSTR'

DG822 = rig.FuncGen(_VISA_ADDRESS_rigol)

DG822.harmonic(channel = 1, amp=VOLT_SIN, freq=FREQ_SIN)

DAQ = pico.PicoScope(channels, buffersize, sampleInterval, sampleUnit, totalSamples, ranges)

DG822.turn_on(channel = 1)
print('Drive on')
time.sleep(1)

print('Streaming...')
DAQ.Stream()
print('Finished streaming.')
print('Saving...')
DAQ.save_data_hdf5(filename, {'A':DAQ.buffersComplete[0], 'B':DAQ.buffersComplete[1], 'Tinterval':[sampleInterval/multiplier[sampleUnit]]})
print('Finished saving.')
time.sleep(1)

DG822.turn_off(channel = 1)
print('Drive off')
time.sleep(1)

print('Streaming...')
DAQ.Stream()
print('Finished streaming.')
print('Saving...')
DAQ.save_data_hdf5(filename2, {'A':DAQ.buffersComplete[0], 'B':DAQ.buffersComplete[1], 'Tinterval':[sampleInterval/multiplier[sampleUnit]]})
print('Finished saving.')

DAQ.stop()
DAQ.close()

print('Program end.')


