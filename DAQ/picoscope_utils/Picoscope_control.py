"""
Script containing class to control PicoScope
"""

import ctypes
import numpy as np

from picosdk.ps4000a import ps4000a as ps
from picosdk.functions import adc2mV, assert_pico_ok

import time

import matplotlib.pyplot as plt

import h5py


class PicoScope:
    """
    Class to control PicoScope

    """

    def __init__(self, channels, buffersize, sampleInterval, sampleUnit, totalSamples, ranges):
        self._channels = channels
        self._buffersize = buffersize
        self._sampleInterval = sampleInterval
        self._sampleUnit = sampleUnit
        self._totalSamples = totalSamples
        self.numChannels = len(channels)
        self._ranges = ranges
        self.Stream_status = 0

        self.open()
        self.setSampleinterval(sampleInterval)
        self.setSampleunits(sampleUnit)
        self.setTotalsamples(totalSamples)
        self.bufferMax = np.zeros(shape=(self.numChannels, self._buffersize), dtype=np.int16)
        for cn, channel in enumerate(channels):
            self.setChannel(channel = channel, channel_range=ranges[channel])
            # Create buffers ready for assigning pointers for data collection
            self.setBuffersize(channel = channel, cn = cn)
    
    def open(self):
        print('Connecting to picoscope...')
        self.chandle = ctypes.c_int16()
        self.status = {}

        # Open 4000 series PicoScope
        # Returns handle to chandle for use in future API functions
        self.status["openunit"] = ps.ps4000aOpenUnit(ctypes.byref(self.chandle), None)
        assert_pico_ok(self.status["openunit"])
        print('Connected to picoscope!')

    def setChannel(self, channel = "A", channel_range = 6, analogue_offset = 0.0):
        enabled = 1
        disabled = 0
        self._ranges[channel] = channel_range
        self.status["setCh"+channel] = ps.ps4000aSetChannel(self.chandle,
                                                ps.PS4000A_CHANNEL['PS4000A_CHANNEL_'+channel],
                                                enabled,
                                                ps.PS4000A_COUPLING['PS4000A_DC'],
                                                channel_range,
                                                analogue_offset)
        assert_pico_ok(self.status["setCh"+channel])

    def setBuffersize(self, channel, cn):
        memory_segment = 0

        self.status["setDataBuffers"+channel] = ps.ps4000aSetDataBuffers(self.chandle,
                                                            ps.PS4000A_CHANNEL['PS4000A_CHANNEL_'+channel],
                                                            self.bufferMax[cn].ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                            None,
                                                            self._buffersize,
                                                            memory_segment,
                                                            ps.PS4000A_RATIO_MODE['PS4000A_RATIO_MODE_NONE'])
        assert_pico_ok(self.status["setDataBuffers"+channel])
    
    def setSampleinterval(self, sampleInterval):
        self._sampleInterval = sampleInterval
        self.sampleIntervalC = ctypes.c_int32(sampleInterval)

    def setSampleunits(self, sampleUnit):
        self._sampleUnit = sampleUnit
        self.sampleUnits = ps.PS4000A_TIME_UNITS['PS4000A_'+sampleUnit]

    def setTotalsamples(self, totalSamples):
        self._totalSamples = totalSamples
        totalSamples = totalSamples

    def reinititialiseChannels(self, buffersize, sampleInterval, totalSamples):
        self._buffersize = buffersize

        self.setSampleinterval(sampleInterval)
        self.setTotalsamples(totalSamples)

        self.bufferMax = np.zeros(shape=(self.numChannels, self._buffersize), dtype=np.int16)

        for cn, channel in enumerate(self._channels):
            # Create buffers ready for assigning pointers for data collection
            self.setBuffersize(channel = channel, cn = cn)


    def makeCfunctionpointer(self):

        def streaming_callback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
            self.wasCalledBack = True
            destEnd = self.nextSample + noOfSamples
            sourceEnd = startIndex + noOfSamples
            for n in range(self.numChannels):
                self.buffersComplete[n][self.nextSample:destEnd] = self.bufferMax[n][startIndex:sourceEnd]
            self.nextSample += noOfSamples
            if autoStop:
                self.autoStopOuter = True

        # Convert the python function into a C function pointer.
        self.cFuncPtr = ps.StreamingReadyType(streaming_callback)

    def setTrigger(self, enable=1, source=0, thresh=1024, delay=0, type="RISING", auto_trig_delay=0):
        ### set up the trigger
        trig_dict = {"ABOVE": 0, "BELOW": 1, "RISING": 2, "FALLING": 3, "RISING_OR_FALLING": 4}
        if not type in trig_dict:
            print("Failed to set trigger: ", type)
            return
        ps.ps4000aSetSimpleTrigger(self.chandle, enable, source, thresh, trig_dict[type], delay, auto_trig_delay)

    def getTimebase(self, samp_time, maxSamples):
        ### get the timebase from the picoscope
        ## sample time, samp_time in ns
        timebase = int(samp_time/12.5) - 1 ## 12.5 ns per sample for 4000A
        timeIntervalns = ctypes.c_float()
        returnedMaxSamples = ctypes.c_int32()
        ps.ps4000aGetTimebase2(self.chandle, timebase, maxSamples, ctypes.byref(timeIntervalns), ctypes.byref(returnedMaxSamples), 0)
        return timeIntervalns, returnedMaxSamples

    def triggeredCapture(self, preTriggerSamples, postTriggerSamples):
        
        timebase = int(self._sampleInterval/12.5) - 1 ## 12.5 ns per sample for 4000A
        ## take triggered data
        ps.ps4000aRunBlock(self.chandle, preTriggerSamples, postTriggerSamples, timebase, None, 0, None, None)

        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            self.status["isReady"] = ps.ps4000aIsReady(self.chandle, ctypes.byref(ready))

        overflow = ctypes.c_int16()
        cmaxSamples = ctypes.c_int32(self._buffersize)
        ps.ps4000aGetValues(self.chandle, 0, ctypes.byref(cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
          
        maxADC = ctypes.c_int16(32767)

        outData = np.zeros_like(self.bufferMax)
        for j,cn in enumerate(self._channels):
            chRange = self._channels[cn]
            outData[j,:] = adc2mV(self.bufferMax[j,:], chRange, maxADC)

        outTime = np.linspace(0, (self.bufferMax - 1) * self._sampleInterval, cmaxSamples.value)

        return outTime, outData

    def init_buffersComplete(self):
        self.buffersComplete = np.zeros(shape=(self.numChannels, self._totalSamples), dtype=np.int16)

    def Stream(self):
        self.Stream_status = 1
        self.init_buffersComplete()
        self.nextSample = 0
        self.autoStopOuter = False
        self.wasCalledBack = False
        self.makeCfunctionpointer()
        #Begin streaming
        # We are not triggering:
        maxPreTriggerSamples = 0
        autoStopOn = 0
        # No downsampling:
        downsampleRatio = 1
        self.status["runStreaming"] = ps.ps4000aRunStreaming(self.chandle,
                                                        ctypes.byref(self.sampleIntervalC),
                                                        self.sampleUnits,
                                                        maxPreTriggerSamples,
                                                        self._totalSamples,
                                                        autoStopOn,
                                                        downsampleRatio,
                                                        ps.PS4000A_RATIO_MODE['PS4000A_RATIO_MODE_NONE'],
                                                        self._buffersize)
        assert_pico_ok(self.status["runStreaming"])

        #nextSample = 0
        #autoStopOuter = False

        while self.nextSample < self._totalSamples and not self.autoStopOuter:
            self.wasCalledBack = False
            self.status["getStreamingLastestValues"] = ps.ps4000aGetStreamingLatestValues(self.chandle, self.cFuncPtr, None)
            if not self.wasCalledBack:
                # If we weren't called back by the driver, this means no data is ready. Sleep for a short while before trying
                # again.
                time.sleep(0.01)
        self.Stream_status = 0

    #def plot(self, buffers):
    #    for buffer in buffers:
    #        plt.plot(buffer)
    #        plt.show()

    def stop(self):            
        # Stop the scope
        # handle = chandle
        self.status["stop"] = ps.ps4000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])

    def close(self):
        # Disconnect the scope
        # handle = chandle
        self.autoStopOuter = True
        self.status["close"] = ps.ps4000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

    def plot(self, buffer):
        plt.plot(buffer)
        plt.show()

    def save_data_hdf5(self, filename, data):
        """
        Saves data in HDF5. Does it in a simple way by looping through data and datasetnames
        filename: Filename of file you want to save
        data: the data you want to save as a dictionary
        """
        keys = list(data.keys())
        with h5py.File(filename, "w") as f:
            for key in keys:
                f[key] = data[key]


if __name__ == "__main__":
    pico = PicoScope(channels = ["A", "B"], buffersize = 10000, sampleInterval = 100, sampleUnit = "US", totalSamples = 10000, ranges = {'A':7, 'B':7})
    pico.Stream()
    pico.plot(pico.buffersComplete[0])
    pico.stop()
    pico.close()