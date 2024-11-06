import AFG1022_control as AFG

def sine_wave(address: str, amplitude = 1, frequency = 20000, offset = 0, channel = 1):
    """Changes channel input to sin wave with input frequency, offset and pk-pk amplitude"""
    with AFG.FuncGen(address) as fgen:
        fgen.channels[channel - 1].set_function("SIN")
        fgen.channels[channel - 1].set_frequency(frequency, unit="Hz")
        fgen.channels[channel - 1].set_offset(offset, unit="V")
        fgen.channels[channel - 1].set_amplitude(amplitude)

def turn_on(address:str, channel = 1):
    with AFG.FuncGen(address) as fgen:
        fgen.channels[channel - 1].set_output("ON")


def turn_off(address:str, channel = 1):
    with AFG.FuncGen(address) as fgen:
        fgen.channels[channel - 1].set_output("OFF")
