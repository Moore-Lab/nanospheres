# -*- coding: utf-8 -*-
"""
Created on Fri May  5 16:20:17 2023

@author: microspheres
"""

  #
# Copyright (C) 2018-2019 Pico Technology Ltd. See LICENSE file for terms.
#
# PS2000 Series (A API) STREAMING MODE EXAMPLE - EDITING COPY - EDITED Spring 2023 (RM)
# This example demonstrates how to call the ps4000A driver API functions in order to open a device, setup a channel and collects streamed data (1 buffer).
# This code has been modified so it can be plotted as V against time in s.

import ctypes
import numpy as np
from picosdk.ps4000a import ps4000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok
import time
from datetime import datetime
import scipy.io as sio
from PIL import Image

def take_data(buff_size_td, num_buffs_td, sample_int_td):
    
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


    enabled = 1
    disabled = 0
    analogue_offset = 0.0

    # Set up channel A
    # handle = chandle
    # channel = PS4000A_CHANNEL_A = 0
    # enabled = 1
    # coupling type = PS4000A_DC = 1
    # range = PS4000A_2V = 7
    # analogue offset = 0 V
    channel_range = 7
    status["setChA"] = ps.ps4000aSetChannel(chandle,
                                        ps.PS4000A_CHANNEL['PS4000A_CHANNEL_A'],
                                        enabled,
                                        ps.PS4000A_COUPLING['PS4000A_DC'],
                                        channel_range,
                                        analogue_offset)
    assert_pico_ok(status["setChA"])

    # Size of capture 
    sizeOfOneBuffer = buff_size_td
    numBuffersToCapture = num_buffs_td

    totalSamples = sizeOfOneBuffer * numBuffersToCapture

    # Create buffers ready for assigning pointers for data collection
    bufferAMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)

    memory_segment = 0

    # Set data buffer location for data collection from channel A
    # handle = chandle
    # source = PS4000A_CHANNEL_A = 0
    # pointer to buffer max = ctypes.byref(bufferAMax)
    # pointer to buffer min = ctypes.byref(bufferAMin)
    # buffer length = maxSamples
    # segment index = 0
    # ratio mode = PS4000A_RATIO_MODE_NONE = 0
    status["setDataBuffersA"] = ps.ps4000aSetDataBuffers(chandle,
                                                     ps.PS4000A_CHANNEL['PS4000A_CHANNEL_A'],
                                                     bufferAMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                     None,
                                                     sizeOfOneBuffer,
                                                     memory_segment,
                                                     ps.PS4000A_RATIO_MODE['PS4000A_RATIO_MODE_NONE'])
    assert_pico_ok(status["setDataBuffersA"])

    # Begin streaming mode:
    sampleInterval = ctypes.c_int32(sample_int_td) ###REDUCED SAMPLE INTERVAL BY A FACTOR OF 10
    sampleUnits = ps.PS4000A_TIME_UNITS['PS4000A_US']
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

    actualSampleInterval = sampleInterval.value
    actualSampleIntervalNs = actualSampleInterval * 1000

    #print("Capturing at sample interval %s ns" % actualSampleIntervalNs)
     
    # We need a big buffer, not registered with the driver, to keep our complete capture in.
    
    bufferCompleteA = np.zeros(shape=totalSamples, dtype=np.int16)
    global nextSample, autoStopOuter, wasCalledBack
    nextSample = 0
    autoStopOuter = False
    wasCalledBack = False
    #global wasCalledBack, nextSample, autoStopOuter
    
    def streaming_callback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
        global wasCalledBack, nextSample, autoStopOuter
        wasCalledBack = True
        destEnd = nextSample + noOfSamples
        sourceEnd = startIndex + noOfSamples
        bufferCompleteA[nextSample:destEnd] = bufferAMax[startIndex:sourceEnd]
        nextSample += noOfSamples
        if autoStop:
            autoStopOuter = True
            
    # Convert the python function into a C function pointer.
    cFuncPtr = ps.StreamingReadyType(streaming_callback)
    
    # Fetch data from the driver in a loop, copying it out of the registered buffers and into our complete one.
    num = 0
    while nextSample < totalSamples and not autoStopOuter:
        wasCalledBack = False
        status["getStreamingLastestValues"] = ps.ps4000aGetStreamingLatestValues(chandle, cFuncPtr, None)
        if not wasCalledBack:
            # If we weren't called back by the driver, this means no data is ready. Sleep for a short while before trying
            # again.
            time.sleep(0.01)
        make_dict = {'bufferCompleteA': bufferCompleteA} #convert buffer into a dictionary so it can be read into matlab
      #  make_dict                                        #make the dictionary
      #  timestr = time.strftime('%Y%m%d-%H%M%S') #labels the files with the date/time they are created
        sio.savemat("D:\\Python\\buffer"+str(num)+".mat", make_dict) #save the file with the timestamp
        num+=1
    
    # Find maximum ADC count value
    # handle = chandle
    # pointer to value = ctypes.byref(maxADC)
    maxADC = ctypes.c_int16()
    status["maximumValue"] = ps.ps4000aMaximumValue(chandle, ctypes.byref(maxADC))
    assert_pico_ok(status["maximumValue"])

    # Convert ADC counts data to mV
    adc2mVChAMax = adc2mV(bufferCompleteA, channel_range, maxADC)
    adc2VChAMax = [i*10**(-3) for i in adc2mVChAMax] #convert mV to V 

    # Create time data
    time_int = np.linspace(0, (totalSamples - 1) * actualSampleInterval, totalSamples)

    # Plot data from channel A 
    
    plt.plot(time_int[:buff_size_td]*10**(-9), adc2VChAMax[:buff_size_td]) #slicing so it plots only one buffer of data       
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    timstmp = datetime.now()
    file_name = 'D:\Python\\takedata.' +  str(timstmp.strftime('%d-%m-%H-%M-%S'))+'.jpeg'
    plt.savefig(file_name)
   
    # Stop the scope
    # handle = chandle
    status["stop"] = ps.ps4000aStop(chandle)
    assert_pico_ok(status["stop"])

    # Disconnect the scope
    # handle = chandle
    status["close"] = ps.ps4000aCloseUnit(chandle)
    assert_pico_ok(status["close"])

    # Display status returns
    #print(status)
    image = Image.open(file_name)
    image.show()
    #return(image.show())
    
'''If you want to test run the function, uncomment the line of code below'''    
take_data(100,10,1000)
