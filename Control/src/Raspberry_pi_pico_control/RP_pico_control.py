import serial 
import time

class RPpico:
    """
    RPpico class to communicate with Raspberry Pi Pico via serial.
    Input port and baudrate to initialize the serial connection. Automatic baudrate is 115200
    """
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = serial.Serial(port, baudrate)
        time.sleep(2)  # wait for the serial connection to establish
        print(f"Connected to {port}")

    def send_command(self, command):
        self.ser.write(command.encode() + b'\r\n') # send command

    def close(self):
        self.ser.close()