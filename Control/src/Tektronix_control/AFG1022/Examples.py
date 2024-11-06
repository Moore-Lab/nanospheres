import copy
import pyvisa
import numpy as np
from typing import Tuple, List, Union
import AFG1022_control as AFG

def example_basic_control(address: str):
    """Example showing how to connect, and the most basic control of the
    instrument parameters"""
    print("\n\n", example_basic_control.__doc__)
    with AFG.FuncGen(address) as fgen:
        fgen.ch1.set_function("SIN")
        fgen.ch1.set_frequency(25, unit="Hz")
        fgen.ch1.set_offset(50, unit="mV")
        fgen.ch1.set_amplitude(0.002)
        fgen.ch1.set_output("ON")
        fgen.ch1.set_output("OFF")
        # Alternatively fgen.ch1.print_settings() to show from one channel only
        fgen.print_settings()


def example_change_settings(address: str):
    """Example showing how to get the current settings of the instrument,
    store them, change a setting and then restore the initial settings"""
    print("\n\n", example_change_settings.__doc__)
    with AFG.FuncGen(address) as fgen:
        fgen.print_settings()
        print("Saving these settings..")
        settings = fgen.get_settings()
        print("Change to 1Vpp amplitude for channel 1..")
        fgen.ch1.set_amplitude(1)
        fgen.print_settings()
        print("Reset back to initial settings..")
        fgen.set_settings(settings)
        fgen.print_settings()


def example_lock_frequencies(address: str):
    """Example showing the frequency being set to 10Hz and then the frequency
    lock enabled, using the frequency at ch1 as the common frequency"""
    print("\n\n", example_lock_frequencies.__doc__)
    with AFG.FuncGen(address, verbose=False) as fgen:
        fgen.ch1.set_frequency(10)
        fgen.set_frequency_lock("ON", use_channel=1)


def example_changing_limits(address: str):
    """Example showing how limits can be read and changed"""
    print("\n\n", example_changing_limits.__doc__)
    with AFG.FuncGen(address) as fgen:
        lims = fgen.ch1.get_frequency_lims()
        print("Channel 1 frequency limits: {}".format(lims))
        print("Change the lower limit to 2Hz..")
        fgen.ch1.set_limit("frequency lims", "min", 2)
        lims = fgen.ch1.get_frequency_lims()
        print("Channel 1 frequency limits: {}".format(lims))
        print("Try to set ch1 frequency to 1Hz..")
        try:
            fgen.ch1.set_frequency(1)
        except NotSetError as err:
            print(err)


def example_set_and_use_custom_waveform(address: str, channel: int = 1, plot_signal: bool = True):
    """Example showing a waveform being created, transferred to the instrument,
    and applied to a channel"""
    print("\n\n", example_set_and_use_custom_waveform.__doc__)
    # Create a signal
    x = np.linspace(0, 4 * np.pi, 8000)
    signal = np.sin(x) + x / 5
    if plot_signal:  # plot the signal for visual control
        import matplotlib.pyplot as plt

        plt.plot(signal)
        plt.show()
    # Create initialise fgen if it was not supplied

    with AFG.FuncGen(address) as fgen:

        print("Current waveform catalogue")
        for i, wav in enumerate(fgen.get_waveform_catalogue()):
            print(f"  {i}: {wav}")
        # Transfer the waveform
        fgen.set_custom_waveform(signal, memory_num=5, verify=True)
        print("New waveform catalogue:")
        for i, wav in enumerate(fgen.get_waveform_catalogue()):
            print(f"  {i}: {wav}")
        print(f"Set new wavefrom to channel {channel}..", end=" ")
        fgen.channels[channel - 1].set_output_state("OFF")
        fgen.channels[channel - 1].set_function("USER5")
        print("ok")
        # Print current settings
        fgen.print_settings()


## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ MAIN FUNCTION ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

_VISA_ADDRESS = "USB0::0x0699::0x0353::2238362::INSTR"

if __name__ == "__main__":
    #example_basic_control(_VISA_ADDRESS)
    #example_change_settings(_VISA_ADDRESS)
    #example_lock_frequencies(_VISA_ADDRESS)
    #example_changing_limits(_VISA_ADDRESS)
    #with FuncGen(_VISA_ADDRESS) as fgen:
    example_set_and_use_custom_waveform(_VISA_ADDRESS)