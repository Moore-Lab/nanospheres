import numpy as np
import pyvisa
import time
import sys

sys.path.insert(1, 'C:/Users/microspheres/Documents/Nanosphere github/nanospheres')

import DAQ.picoscope_utils.Picoscope_control as pico
import Control.src.RIGOL_control.DG822.DG822_control as rig

"""
Turns on HV source for needle to create plasma in chamber and change the charge state of the sphere.
Does this using pulses to make it more controllable - just turning it on makes it too messy.
Will only work in the 1 - 10 mbar pressure range.
"""

### Variables
VOLT_PULSE = 4000      # Voltage one wants on the needle.
              # There will be a minimum below which it will not ionise the air. 
              # I think this probably also maxes out around 1 kV as it can't supply more current.
FREQ_PULSE = 0.2

VOLT_SIN = 4
FREQ_SIN = 30000

### Don't change unless error with these values (e.g. does not connect)
### Can find out what the value should be using the following lines. You will have to figure out which resource is which instrument
# rm = pyvisa.ResourceManager()
# rm.list_resources()

_VISA_ADDRESS_rigol = 'USB0::0x1AB1::0x0643::DG8A261500548::INSTR'

DG822 = rig.FuncGen(_VISA_ADDRESS_rigol)

control_voltage = VOLT_PULSE/500

DG822.sin_wave(channel = 1, amp=VOLT_SIN, freq=FREQ_SIN, )
DG822.pulse(channel = 2, amp=control_voltage, duty=4, freq=FREQ_PULSE, off=control_voltage/2)
#DG822.pulse(amp=VOLT, duty=50, freq=FREQ_PULSE, off=-VOLT/2)

# Ouput signals

#DG822.turn_on(channel = 1)
print('Drive on')
time.sleep(5)
#DG822.turn_on(channel = 2)
print('HV triggered')

# Hold in loop until cancel - have 10 minute timeout
i = 0
while i < 34:
    try:
        time.sleep(1)
        i+=1
    except KeyboardInterrupt:
        break

#DG822.turn_off(channel = 1)
print('Drive off')
#DG822.turn_off(channel = 2)

print('HV switched off')
print('Program ends')