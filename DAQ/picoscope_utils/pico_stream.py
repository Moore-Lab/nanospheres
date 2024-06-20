# Based on PS2000 Series (A API) STREAMING MODE EXAMPLE

import ctypes
import numpy as np
from picosdk.ps4000a import ps4000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok
import time
import h5py
import scipy.io as sio

"""
Set parameters here
"""

# Channel E does not work... apparently it isn't a legit Key...

channels = ['A'] #['A', 'B', 'C', 'D', 'F', 'G', 'H']

# ranges: 0=10 mV, 1=20 mV, 2=50 mV, 3=100mV, 4=200 mV, 5=500 mV, 6=1000 mV, 7=2000 mV, 8=5000 mV, 9=10000 mV, 10=20000 mV, 11=50000 mV]
channel_ranges = [6] # [0, 0, 0, 0, 0, 0, 0]
analogue_offsets = [0.0] #[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

filename = 'D:/Lab Data/Picoscope Test/Tmp/test12' # Location to save data

enabled = 1
disabled = 0

ADC_convert = True # Convert to mV? This increases the dead time

# Size of capture
bufferLength = 1 # in seconds
numBuffersToCapture = 1 # just leave this at 1 for now - will probably need to play with this when want to look at data that hasn't yet been saved.
num_files = 1 # number of files t0 capture
sample_interval = 10 # in us

"""
End of set parameters
"""

"""
Now some useful functions
"""

def adc2mV2(bufferADC, range, maxADC):
    """ 
        adc2mc(
                c_short_Array           bufferADC
                int                     range
                c_int32                 maxADC
                )
               
        Takes a buffer of raw adc count values and converts it into millivolts
    """
    channelInputRanges = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000]
    vRange = np.zeros(shape=(len(bufferADC), len(bufferADC[0])), dtype=np.int16)
    for n, i in enumerate(range):
        vRange[n] += channelInputRanges[i]

    bufferV = (bufferADC * vRange) / maxADC.value

    return bufferV

def set_Channel(channel, channel_range, analogue_offset):
    # handle = chandle
    # channel = PS4000A_CHANNEL_A = 0
    # enabled = 1
    # coupling type = PS4000A_DC = 1
    # range = PS4000A_2V = 7
    # analogue offset = 0 V
    status["setCh"+channel] = ps.ps4000aSetChannel(chandle,
                                            ps.PS4000A_CHANNEL['PS4000A_CHANNEL_'+channel],
                                            enabled,
                                            ps.PS4000A_COUPLING['PS4000A_DC'],
                                            channel_range,
                                            analogue_offset)
    assert_pico_ok(status["setCh"+channel])
    return 1

def set_DataBuffer(channel, listpos):
    # Set data buffer location for data collection from channel A
    # handle = chandle
    # source = PS4000A_CHANNEL_A = 0
    # pointer to buffer max = ctypes.byref(bufferAMax)
    # pointer to buffer min = ctypes.byref(bufferAMin)
    # buffer length = maxSamples
    # segment index = 0
    # ratio mode = PS4000A_RATIO_MODE_NONE = 0
    status["setDataBuffers"+channel] = ps.ps4000aSetDataBuffers(chandle,
                                                        ps.PS4000A_CHANNEL['PS4000A_CHANNEL_'+channel],
                                                        bufferMaxl[listpos].ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                        None,
                                                        sizeOfOneBuffer,
                                                        memory_segment,
                                                        ps.PS4000A_RATIO_MODE['PS4000A_RATIO_MODE_NONE'])
    assert_pico_ok(status["setDataBuffers"+channel])
    return 1

def pico_TurnOn():
    # Create chandle and status ready for use
    chandle = ctypes.c_int16()
    status = {}

    # Open PicoScope 2000 Series device
    # Returns handle to chandle for use in future API functions
    status["openunit"] = ps.ps4000aOpenUnit(ctypes.byref(chandle), None)

    try:
        assert_pico_ok(status["openunit"])
    except:

        powerStatus = status["openunit"]

        if powerStatus == 286:
            status["changePowerSource"] = ps.ps4000aChangePowerSource(chandle, powerStatus)
        else:
            raise

        assert_pico_ok(status["changePowerSource"])
    return chandle, status

def streaming_callback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
    global nextSample, autoStopOuter, wasCalledBack
    wasCalledBack = True
    destEnd = nextSample + noOfSamples
    sourceEnd = startIndex + noOfSamples
    for n in range(len(channels)):
        bufferCompletel[n][nextSample:destEnd] = bufferMaxl[n][startIndex:sourceEnd]
    nextSample += noOfSamples
    if autoStop:
        autoStopOuter = True

def stream():
    # We are not triggering:
    maxPreTriggerSamples = 0
    autoStopOn = 1
    # No downsampling:
    downsampleRatio = 1
    status["runStreaming"] = ps.ps4000aRunStreaming(chandle,
                                                    ctypes.byref(sampleInterval),
                                                    sampleUnits,
                                                    maxPreTriggerSamples,
                                                    totalSamples,
                                                    autoStopOn,
                                                    downsampleRatio,
                                                    ps.PS4000A_RATIO_MODE['PS4000A_RATIO_MODE_NONE'],
                                                    sizeOfOneBuffer)
    assert_pico_ok(status["runStreaming"])

    #print("Capturing at sample interval %s ns" % actualSampleIntervalNs)

    # We need a big buffer, not registered with the driver, to keep our complete capture in.
    autoStopOuter = False
    wasCalledBack = False

    # Convert the python function into a C function pointer.
    cFuncPtr = ps.StreamingReadyType(streaming_callback)

    # Fetch data from the driver in a loop, copying it out of the registered buffers and into our complete one.
    while nextSample < totalSamples and not autoStopOuter:
        wasCalledBack = False
        status["getStreamingLastestValues"] = ps.ps4000aGetStreamingLatestValues(chandle, cFuncPtr, None)
        if not wasCalledBack:
            # If we weren't called back by the driver, this means no data is ready. Sleep for a short while before trying
            # again.
            time.sleep(0.01)

    #print("Done grabbing values.")


def save_data_hdf5(filename, data):
    """
    Saves data in HDF5. Does it in a simple way by looping through data and datasetnames
    filename: Filename of file you want to save
    data: the data you want to save as a dictionary
    """
    keys = list(data.keys())
    with h5py.File(filename, "w") as f:
        for key in keys:
            f[key] = data[key]
        #f.close()

def load_data_hdf5(filename):
    """
    Loads data in HDF5. Doesn't load metadata. Outputs as dictionary.
    filename: Filename of file you want to load
    """
    f = h5py.File(filename, "r")
    keys = list(f.keys())
    mdict = {}
    for key in keys:
        dataset = list(f[key])
        mdict[key] = dataset
    f.close()
    return mdict

"""
End of functions
"""

sizeOfOneBuffer = int(bufferLength/sample_interval*10**6)
totalSamples = sizeOfOneBuffer * numBuffersToCapture
total_length = totalSamples*sample_interval/10**6
# Turn on the picoscope
chandle, status = pico_TurnOn()

# Set up the channels
for n in range(len(channels)):
    set_Channel(channels[n], channel_ranges[n], analogue_offsets[n])

# Create buffers ready for assigning pointers for data collection
bufferMaxl = np.zeros(shape=(len(channels), sizeOfOneBuffer), dtype=np.int16)

memory_segment = 0 # Not 100% sure how this affects things but will mess around with it later to understand

# set up the buffer in the picoscope
for n, i in enumerate(channels):
    set_DataBuffer(i, n)

sampleInterval = ctypes.c_int32(sample_interval)
sampleUnits = ps.PS4000A_TIME_UNITS['PS4000A_US'] # sample_interval is in us
actualSampleInterval = sampleInterval.value
actualSampleIntervalNs = actualSampleInterval * 1000

# Begin streaming mode:
# Will loop through and stream num_files number of times. Each time saves a buffer of length totalSamples for each channel.

bufferCompletel = np.zeros(shape=(len(channels), totalSamples), dtype=np.int16)
for i in range(num_files):
    nextSample = 0
    stream()
    if ADC_convert: # if converting to mV will do that
        maxADC = ctypes.c_int16()
        status["maximumValue"] = ps.ps4000aMaximumValue(chandle, ctypes.byref(maxADC))
        assert_pico_ok(status["maximumValue"])
        adc2mVChlMax = adc2mV2(bufferCompletel, channel_ranges, maxADC)
    mdict = {'Sample interval (us)': [sample_interval]} # create a dictionary of saving data into
    for m, j in enumerate(channels): # add actual data to dictionary
        if ADC_convert:
            mdict[j] = adc2mVChlMax[m]
        else:
            mdict[j] = bufferCompletel[m]
    save_data_hdf5(filename+str(i)+'.hdf5', mdict)

# Stop the scope
# handle = chandle
status["stop"] = ps.ps4000aStop(chandle)
assert_pico_ok(status["stop"])

# Disconnect the scope
# handle = chandle
status["close"] = ps.ps4000aCloseUnit(chandle)
assert_pico_ok(status["close"])

# Display status returns
print(status)