import time
import redpitaya_scpi as scpi

class RedPitaya:

    def __init__(self, RP_address):
        self.RP_address = RP_address
        self.rp = scpi.scpi(RP_address)

    def acquire_data_now(self, DEC = 8192, channel = 1):
        """
        Acquire data immediately as a list of floats
        DEC is the decimation factor, essentially sets the sample rate, 1 is 125 MS/s and the decimation factor will lower this rate by the corresponding amount. e.g 8192 is 15.26 kS/s
        Always collects 16384 samples, so the total collection time is is given by 16384/125e6*DEC seconds. e.g. DEC = 8192 is slightly more than 1 second of data
        """""
        self.rp.tx_txt('ACQ:RST')
        self.rp.tx_txt('ACQ:DATA:FORMAT ASCII')
        self.rp.tx_txt('ACQ:DATA:UNITS VOLTS')
        self.rp.tx_txt('ACQ:DEC '+str(DEC))
        self.rp.tx_txt('ACQ:SOUR'+str(channel)+':GAIN HV')

        self.rp.tx_txt('ACQ:TRIG:DLY 0')

        self.rp.tx_txt('ACQ:START')
        time.sleep(1)
        self.rp.tx_txt('ACQ:TRIG NOW')
        time.sleep(1)

        while 1:
            self.rp.tx_txt('ACQ:TRIG:STAT?')
            if self.rp.rx_txt() == 'TD':
                break

        self.rp.tx_txt('ACQ:SOUR'+str(channel)+':DATA?')
        buff_string = self.rp.rx_txt()
        buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
        buff = list(map(float, buff_string))
        return buff

    def close(self):
        self.rp.close() 
        print("Red Pitaya connection closed.")