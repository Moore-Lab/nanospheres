"""
Generates a frequency comb for the AWG, saves it to USER0 in memory then outputs it.

Used for calibrating the particle displacement by applying the voltage to the lens holder electrodes.
"""

import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as scisig
import AFG1022_control as AFG

def Frequency_comb_gen_and_send(address: str, channel: int = 1, plot_signal: bool = True, fstart = 1, fend = 151, numsteps = 76):
    """Example showing a waveform being created, transferred to the instrument,
    and applied to a channel"""
    # Create a signal
    
    numpoints = 8182 # Total number of points in waveform
    freqlist = np.linspace(fstart, fend, numsteps)*1000 # frequencies for frequency comb in kHz
    time = np.linspace(0, 0.001, numpoints) # make 8182 points equal to 0.001 second

    signal = np.zeros(numpoints)
    # Product the waveform
    for i in freqlist:
        signal = signal + np.sin(2*np.pi*i*time)

    with AFG.FuncGen(address) as fgen:

        # Transfer the waveform
        fgen.set_custom_waveform(signal, memory_num=0, verify=False)
        print("New waveform catalogue:")
        for i, wav in enumerate(fgen.get_waveform_catalogue()):
            print(f"  {i}: {wav}")
        print(f"Set new wavefrom to channel {channel}..", end=" ")

        # Set frequency to 1 Hz since signal is 1 s long
        fgen.channels[channel - 1].set_output_state("OFF")
        fgen.channels[channel - 1].set_function("USER0")
        fgen.channels[channel - 1].set_frequency(1000, unit="Hz")
        print("ok")
        # Print current settings
        #fgen.print_settings()


## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ MAIN FUNCTION ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

_VISA_ADDRESS = "USB0::0x0699::0x0353::2238362::INSTR"

if __name__ == "__main__":
    Frequency_comb_gen_and_send(_VISA_ADDRESS, fstart = 20, fend = 50, numsteps = 16)
"""
AFG.turn_on(_VISA_ADDRESS)

i = 0
while i < 5:
    try:
        time.sleep(1)
        i+=1
    except KeyboardInterrupt:
        break

AFG.turn_off(_VISA_ADDRESS)
"""