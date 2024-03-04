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

    def __init__(self, channels, buffersize, sampleInterval, sampleUnit, totalSamples):
        self._channels = channels
        self._buffersize = buffersize
        self._sampleInterval = sampleInterval
        self._sampleUnit = sampleUnit
        self._totalSamples = totalSamples
        self.numChannels = len(channels)

        self.open()
        self.setSampleinterval(sampleInterval)
        self.setSampleunits(sampleUnit)
        self.setTotalsamples(totalSamples)
        for cn, channel in enumerate(channels):
            self.setChannel(channel = channel)
            # Create buffers ready for assigning pointers for data collection
            self.bufferMax = np.zeros(shape=(self.numChannels, self._buffersize), dtype=np.int16)
            self.setBuffersize(channel = channel, cn = cn)
    
    def open(self):
        self.chandle = ctypes.c_int16()
        self.status = {}

        # Open 4000 series PicoScope
        # Returns handle to chandle for use in future API functions
        self.status["openunit"] = ps.ps4000aOpenUnit(ctypes.byref(self.chandle), None)
        assert_pico_ok(self.status["openunit"])

    def setChannel(self, channel = "A", channel_range = 6, analogue_offset = 0.0):
        enabled = 1
        disabled = 0
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

    def Stream(self):
        self.buffersComplete = np.zeros(shape=(self.numChannels, self._totalSamples), dtype=np.int16)
        self.nextSample = 0
        self.autoStopOuter = False
        self.wasCalledBack = False
        self.makeCfunctionpointer()
        #Begin streaming
        # We are not triggering:
        maxPreTriggerSamples = 0
        autoStopOn = 1
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
        self.status["close"] = ps.ps4000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

    def plot(self, buffer):
        plt.plot(buffer)
        plt.show()

    def save2HDF5(self, filename, buffer):
        with h5py.File(filename, 'w') as f:
            f['dataset'] = buffer

pico = PicoScope(channels = ["A", "B"], buffersize = 10000, sampleInterval = 100, sampleUnit = "US", totalSamples = 10000)
pico.Stream()
pico.plot(pico.buffersComplete[0])
pico.stop()
pico.close()