import copy
import pyvisa
import numpy as np
from typing import Tuple, List, Union
import time

class FuncGen:

    def __init__(self, visa_address):
        self._visa_address = visa_address
        self.open(visa_address)
    
    def open(self, visa_address):
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(self._visa_address)
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

    def sin_wave(self, channel=1, amp=1, off=0, freq=1000):
    
        source = f"SOURce{channel}:"

        shape = "SINusoid"
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

    def DC(self, channel=1, off=1):
    
        source = f"SOURce{channel}:"

        shape = "DC"
        cmd = f"{source}FUNCtion:SHAPe {shape}"
        self.write(cmd)

        unit = "V"
        cmd = f"{source}VOLTage:OFFSet  {off}{unit}"
        self.write(cmd)

    def harmonic(self, channel=1, amp = 1, off = 0, freq = 5000, type = "BOTH"):

        source = f"SOURce{channel}:"

        shape = "HARMonic"
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

        cmd = f"{source}HARmonic:TYPE {type}"
        self.write(cmd)
    
    def change_amplitude(self, channel = 1, amp = 1):

        source = f"SOURce{channel}:"

        unit = "Vpp"
        cmd = f"{source}VOLTage:LEVel {amp}{unit}"
        self.write(cmd)

    def change_offset(self, channel = 1, off = 1):

        source = f"SOURce{channel}:"

        unit = "V"
        cmd = f"{source}VOLTage:OFFSet  {off}{unit}"
        self.write(cmd)

    def change_phase(self, channel = 1, phase = 0):

        source = f"SOURce{channel}:"

        cmd = f"{source}PHASe {phase}"
        self.write(cmd)

    def turn_on(self, channel = 1):
        cmd = f"OUTPut{channel}:STATe {1}"
        self.write(cmd)

    def turn_off(self, channel = 1):
        cmd = f"OUTPut{channel}:STATe {0}"
        self.write(cmd)
