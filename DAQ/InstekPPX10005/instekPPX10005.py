import pyvisa, time


def open(name="ASRL3::INSTR"):

    rm = pyvisa.ResourceManager()
    inst = rm.open_resource(name, read_termination='\r', write_termination="\n", timeout=10000)

    return inst

def set_voltage(inst, volt, curr=2):
    inst.write(":volt %.1f;:curr %.1f"%(volt, curr))

def set_output(inst, onoff):
    if(onoff=='off'):
        inst.write(":outp 0")
    elif(onoff=='on'):
        inst.write(":outp 1")