from labjack import ljm

class LabJack:
    def __init__(self):
        self.handle = None
        self.info = None
        self.numAddresses = None

    def open(self):
        handle = ljm.openS("T7", "ANY", "ANY")

        self.info = ljm.getHandleInfo(handle)
        print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
            "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
            (self.info[0], self.info[1], self.info[2], ljm.numberToIP(self.info[3]), self.info[4], self.info[5]))

        self.handle = handle
        self.deviceType = self.info[0]


    def config(self, sample_rate=1000, num_samps = 100, channel_list=[0,1], voltage_range=10):
                
        # Stream Configuration
        aScanListNames = []#["AIN0", "AIN1"]  # Scan list names to stream
        for channel in channel_list:
            aScanListNames.append("AIN" + str(channel))
        numAddresses = len(channel_list)
        aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
        scanRate = sample_rate
        scansPerRead = int(sample_rate*numAddresses)

        self.numAddresses = numAddresses

        # When streaming, negative channels and ranges can be configured for
        # individual analog inputs, but the stream has only one settling time and
        # resolution.

        if self.deviceType == ljm.constants.dtT4:
            # LabJack T4 configuration

            # Stream settling is 0 (default) and
            # stream resolution index is 0 (default).
            aNames = ["STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
            aValues = [0, 0]
        else:
            # LabJack T7 and T8 configuration

            # Ensure triggered stream is disabled.
            ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)
            # Enabling internally-clocked stream.
            ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

            # AIN0 and AIN1 ranges are +/-10 V and stream resolution index is
            # 0 (default).
            aNames = []
            aValues = []
            for i in range(numAddresses):
                aNames.append("AIN" + str(i) + "_RANGE")
                aValues.append(voltage_range)

            aNames.extend(["STREAM_RESOLUTION_INDEX"])
            aValues.extend([0])

            # Negative channel and settling configurations do not apply to the T8
            if self.deviceType == ljm.constants.dtT7:
                #     Negative Channel = 199 (Single-ended)
                #     Settling = 0 (auto)
                for i in range(numAddresses):
                    aNames.extend(["AIN" + str(i) + "_NEGATIVE_CH"])
                    aValues.extend([199])
                aNames.extend(["STREAM_SETTLING_US"])
                aValues.extend([0])

        # Write the analog inputs' negative channels (when applicable), ranges,
        # stream settling time and stream resolution configuration.
        numFrames = len(aNames)
        ljm.eWriteNames(self.handle, numFrames, aNames, aValues)

        # Configure and start stream
        scanRate = ljm.eStreamStart(self.handle, scansPerRead, numAddresses, aScanList, scanRate)
        print("\nStream started with a scan rate of %0.0f Hz." % scanRate)

    def close(self):
        ljm.close(self.handle)

    def read_analog_in(self, num_scans=1):

        totScans = 0
        totSkip = 0

        data_out = []

        while totScans < num_scans:

            ret = ljm.eStreamRead(self.handle)
            aData = ret[0]
            print("got data: ", len(aData))
            scans = len(aData) / self.numAddresses
            totScans += scans
            
            # Count the skipped samples which are indicated by -9999 values. Missed
            # samples occur after a device's stream buffer overflows and are
            # reported after auto-recover mode ends.
            curSkip = aData.count(-9999.0)
            totSkip += curSkip
        
            data_out.append(aData)

        return data_out, totSkip