import copy
import pyvisa
import numpy as np
from typing import Tuple, List, Union
import time

_VISA_ADDRESS = "USB0::0x1AB1::0x0643::DG8A204201834::INSTR"

class FuncGen:

    def __init__(self, visa_address):
        self._visa_address = visa_address
        self.open(visa_address)
    
    def open(self, visa_address):
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(_VISA_ADDRESS)
        self.write("*CLS")
        self._id = self.query("*IDN?") 
        self._maker, self._model, self._serial = self._id.split(",")[:3]
        print(f"Connected to {self._maker} model {self._model}, serial {self._serial}")
    
    def write(self, command):
        self._inst.write(command)
    
    def query(self, command):
        response = self._inst.query(command)
        return response
    
    def pulse(self, channel=1, amp=-5, off=0, freq=0.2, duty=0.2):
    
        source = f"SOURce{channel}:"

        shape = "PULSe"
        cmd = f"{source}FUNCtion:SHAPe {shape}"
        self.write(cmd)

        unit = "Vpp"
        cmd = f"{source}VOLTage:LEVel {amp}{unit}"
        self.write(cmd)

        unit = "V"
        cmd = f"{source}VOLTage:OFFSet  {off}{unit}"
        self.write(cmd)

        unit = "Hz"
        cmd = f"{source}FREQuency:FIXed  {freq}{unit}"
        self.write(cmd)

        cmd = f"{source}FUNCtion:PULSe:DCYCle {duty}"
        self.write(cmd)

    def turn_on(self, channel = 1):
        cmd = f"OUTPut{channel}:STATe {1}"
        self.write(cmd)

    def turn_off(self, channel = 1):
        cmd = f"OUTPut{channel}:STATe {0}"
        self.write(cmd)
