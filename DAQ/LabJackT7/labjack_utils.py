from labjack import ljm
import numpy as np

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


    def config(self, sample_rate=1000, num_samps_to_read = 100, channel_list=[0,1], voltage_range=10,
               stream_out=False, stream_out_channel=0, stream_out_data=[0]):
                
        # Stream Configuration
        aScanListNames = []#["AIN0", "AIN1"]  # Scan list names to stream
        for channel in channel_list:
            aScanListNames.append("AIN" + str(channel))
        numAddresses = len(channel_list)
        aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
        scanRate = sample_rate
        scansPerRead = int(num_samps_to_read)
        print("Scans per read: ", scansPerRead)

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

        TOTAL_NUM_CHANNELS = numAddresses

        if stream_out:


            ljm.initializeAperiodicStreamOut(self.handle, 0, 3000, sample_rate)
            # Write some data to the buffer before the stream starts
            ljm.writeAperiodicStreamOut(self.handle, 0, len(stream_out_data), stream_out_data)
            ljm.writeAperiodicStreamOut(self.handle, 0, len(stream_out_data), stream_out_data)  

            #TOTAL_NUM_CHANNELS += 1
            #STREAM_OUT_NAME = "STREAM_OUT0"
            #STREAM_OUT_CHANNEL = "DAC" + str(stream_out_channel)
            #NUM_SAMPLES = len(stream_out_data)
            #ljm.eWriteName(self.handle, f"{STREAM_OUT_NAME}_TARGET", ljm.nameToAddress(STREAM_OUT_CHANNEL)[0])  # Set target as DAC0
            #ljm.eWriteName(self.handle, f"{STREAM_OUT_NAME}_BUFFER_SIZE", 4*NUM_SAMPLES)  # Set buffer size
            #ljm.eWriteName(self.handle, "STREAM_OUT0_ENABLE", 1)

            # Load the buffer into STREAM_OUT0
            #print("Loading ", stream_out_data)
            #ljm.eWriteName(self.handle, "STREAM_OUT0_LOOP_SIZE", NUM_SAMPLES)
            #for i in range(NUM_SAMPLES):
            #    ljm.eWriteName(self.handle, f"{STREAM_OUT_NAME}_BUFFER_F32", stream_out_data[i])
            #ljm.eWriteNameArray(self.handle, f"{STREAM_OUT_NAME}_BUFFER_F32", NUM_SAMPLES, stream_out_data.tolist())

            # Write values to the stream-out buffer
            #ljm.eWriteName(self.handle, "STREAM_OUT0_LOOP_SIZE", 6)
            #ljm.eWriteName(self.handle, "STREAM_OUT0_BUFFER_F32", 0.0)  # 0.0 V
            #ljm.eWriteName(self.handle, "STREAM_OUT0_BUFFER_F32", 1.0)  # 1.0 V
            #ljm.eWriteName(self.handle, "STREAM_OUT0_BUFFER_F32", 2.0)  # 2.0 V
            #ljm.eWriteName(self.handle, "STREAM_OUT0_BUFFER_F32", 3.0)  # 3.0 V
            #ljm.eWriteName(self.handle, "STREAM_OUT0_BUFFER_F32", 4.0)  # 4.0 V
            #ljm.eWriteName(self.handle, "STREAM_OUT0_BUFFER_F32", 5.0)  # 5.0 V

            #ljm.eWriteName(self.handle, "STREAM_OUT0_SET_LOOP", 1)
            #print("STREAM_OUT0_BUFFER_STATUS = %f" % (ljm.eReadName(self.handle, "STREAM_OUT0_BUFFER_STATUS")))



            aScanList.extend(ljm.nameToAddress("STREAM_OUT0"))
            TOTAL_NUM_CHANNELS += 1
            #print(TOTAL_NUM_CHANNELS, aScanList)

        # Configure and start stream
        scanRate = ljm.eStreamStart(self.handle, scansPerRead, TOTAL_NUM_CHANNELS, aScanList, scanRate)
        print("\nStream started with a scan rate of %0.0f Hz." % scanRate)

    def close(self):
        ljm.close(self.handle)

    def write_analog_out(self, channel, voltage):
        name = "DAC" + str(channel)
        value = voltage 
        ljm.eWriteName(self.handle, name, value) 

    def read_analog_in(self, num_scans=1, stream_out=False, stream_out_channel=0, stream_out_data=[0]):

        totScans = 0
        totSkip = 0
        nChan = self.numAddresses

        data_out = []

        while totScans < num_scans:

            if(stream_out):
                ljm.writeAperiodicStreamOut(self.handle, stream_out_channel, len(stream_out_data), stream_out_data)


            ret = ljm.eStreamRead(self.handle)
            aData = ret[0]
            print("got data: ", len(aData))
            
            # Count the skipped samples which are indicated by -9999 values. Missed
            # samples occur after a device's stream buffer overflows and are
            # reported after auto-recover mode ends.
            curSkip = aData.count(-9999.0)
            totSkip += curSkip
        
            aData = np.reshape(aData, (-1,nChan))
            data_out.append(aData)

            totScans += 1

        return data_out, totSkip
    
    def stream_analog_out(self, channel_list=[0], sample_rate=1000, writeData=[0]):

        streamOutIndex = 0
        scansPerRead = int(sample_rate/2)

        # The desired stream channels
        # Up to 4 out-streams can be ran at once
        scanListNames = ["STREAM_OUT0"]
        scanList = ljm.namesToAddresses(len(scanListNames), scanListNames)[0]

        out_channel_addr = []
        for channel in channel_list:
            name = "DAC" + str(channel)
            out_channel_addr.append(ljm.nameToAddress(name)[0])
        print("streaming to channels: ", out_channel_addr)  

        for targetAddr in out_channel_addr:
            ljm.periodicStreamOut(self.handle, streamOutIndex, targetAddr, sample_rate, len(writeData), writeData)
        
        actualScanRate = ljm.eStreamStart(self.handle, scansPerRead, len(scanList), scanList, sample_rate)
        print("Stream started with scan rate of %f Hz\n" % (sample_rate))

        return actualScanRate