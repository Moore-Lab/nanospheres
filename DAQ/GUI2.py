import sys
import traceback
import numpy as np
import scipy.signal as scisig
import time
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

sys.path.insert(1, 'C:/Users/microspheres/Documents/Nanosphere github/nanospheres')

import DAQ.picoscope_utils.Picoscope_control as pc
import Control.src.RIGOL_control.DG822.DG822_control as rig

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(list)

class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them

        result = self.fn(*self.args, **self.kwargs)

class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Charge monitor")
        self.PicoConnected = False
        self.totalSamples = 100000
        self.sampleInterval = 1000
        self.buffersize = 100
        self.global_multiplier = {'s': 1000000000, 'ms': 1000000, 'us': 1000, 'ns': 1}
        self.totaltime_unit = 's'
        self.sampleInterval_unit = 'us'
        self.buffersize_unit = 'us'
        self.channel = "D"
        self.range = 0

        self.RIGOLConnected = False
        self.RIGOLOutputOn = False
        self.VOLT_PULSE = 4000  
        self.FREQ_PULSE = 0.2
        self.VOLT_SIN = 3
        self.FREQ_SIN = 30000
        self._VISA_ADDRESS_rigol = 'USB0::0x1AB1::0x0643::DG8A261500548::INSTR'


        layout1 = QHBoxLayout()
        layout2 = QVBoxLayout()
        layout3 = QVBoxLayout()

        self.title1 = QLabel("Picoscope")

        layout1.setContentsMargins(0,0,0,0)
        layout1.setSpacing(20)

        self.btn1 = QPushButton("Connect")
        self.btn1.clicked.connect(self.btn1_click)

        self.button2_is_checked = False
        self.btn2 = QPushButton("Run")
        self.btn2.setCheckable(True)
        self.btn2.clicked.connect(self.btn2_click)
        self.btn2.setChecked(self.button2_is_checked)

        self.button3_is_checked = False
        self.btn3 = QPushButton("Show")
        self.btn3.setCheckable(True)
        self.btn3.clicked.connect(self.btn3_click)
        self.btn3.setChecked(self.button3_is_checked)

        self.button3b_is_checked = False
        self.btn3b = QPushButton("Show PSD")
        self.btn3b.setCheckable(True)
        self.btn3b.clicked.connect(self.btn3b_click)
        self.btn3b.setChecked(self.button3b_is_checked)

        self.btn4 = QPushButton("Stop and close")
        self.btn4.clicked.connect(self.btn4_click)
        
        layout2.addWidget(self.title1)
        layout2.addWidget(self.btn1)
        layout2.addWidget(self.btn2)
        layout2.addWidget(self.btn3)
        layout2.addWidget(self.btn3b)
        layout2.addWidget(self.btn4)

        layout1.addLayout( layout2 )

        layout_canvas = QVBoxLayout()
        layout_channels = QHBoxLayout()

        self.canvas_drop_channel = QComboBox()
        self.canvas_drop_channel.addItems(["A", "B", "C", "D", "E", "F", "G", "H"])
        self.canvas_drop_channel.currentIndexChanged.connect(self.channel_changed)

        self.canvas_drop_range = QComboBox()
        self.canvas_drop_range.addItems(["10 mV", "20 mV", "50 mV", "100mV", "200mV", "500mV", "1V", "2V", "5V", "10V", "20V", "50V"])
        self.canvas_drop_range.currentIndexChanged.connect(self.range_changed)

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.canvas2 = MplCanvas(self, width=5, height=4, dpi=100)

        layout_channels.addWidget(self.canvas_drop_channel)
        layout_channels.addWidget(self.canvas_drop_range)
        layout_canvas.addLayout(layout_channels)
        layout_canvas.addWidget(self.canvas)
        layout_canvas.addWidget(self.canvas2)
        layout1.addLayout(layout_canvas)

        l3_label1 = QLabel("Total time")
        l3_label2 = QLabel("Sampling interval")
        l3_label3 = QLabel("Buffer Size")

        self.l3_double1 = QSpinBox()
        self.l3_double1.setMinimum(1)
        self.l3_double1.setMaximum(99999)
        self.l3_double1.setSingleStep(1)
        self.l3_double1.valueChanged.connect(self.totalSample_changed)
        self.l3_double1.setValue(int(self.totalSamples/self.sampleInterval))

        self.l3_double2 = QSpinBox()
        self.l3_double2.setMinimum(1)
        self.l3_double2.setMaximum(99999)
        self.l3_double2.setSingleStep(1)
        #self.l3_double2.valueChanged.connect(self.sampleInterval_changed)
        self.l3_double2.setValue(self.sampleInterval)
        
        self.l3_double3 = QSpinBox()
        self.l3_double3.setMinimum(1)
        self.l3_double3.setMaximum(99999)
        self.l3_double3.setSingleStep(1)
        self.l3_double3.setValue(self.buffersize)

        self.l3_drop1 = QComboBox()
        self.l3_drop1.addItems(["s", "ms", "us", "ns"])

        self.l3_drop2 = QComboBox()
        self.l3_drop2.addItems(["s", "ms", "us", "ns"])
        self.l3_drop2.setCurrentIndex(2)

        self.l3_drop3 = QComboBox()
        self.l3_drop3.addItems(["s", "ms", "us", "ns"])
        self.l3_drop3.setCurrentIndex(2)


        self.Check1_is_checked = False
        self.l3_Check1 = QCheckBox('Save data')
        self.l3_Check1.stateChanged.connect(self.check1_changed)
        self.l3_Check1.setChecked(self.Check1_is_checked)

        self.Check2_is_checked = False
        self.l3_Check2 = QCheckBox('Run until stopped')
        self.l3_Check2.stateChanged.connect(self.check2_changed)
        self.l3_Check2.setChecked(self.Check2_is_checked)

        layout4 = QHBoxLayout()
        layout5 = QHBoxLayout()
        layout6 = QHBoxLayout()
        layout7 = QHBoxLayout()

        layout4.addWidget(self.l3_Check1)
        layout4.addWidget(self.l3_Check2)

        layout5.addWidget(self.l3_double1)
        layout5.addWidget(self.l3_drop1)

        layout6.addWidget(self.l3_double2)
        layout6.addWidget(self.l3_drop2)

        layout7.addWidget(self.l3_double3)
        layout7.addWidget(self.l3_drop3)

        self.filename_box = QLineEdit('D:/Experiment/Calibration/test.hdf5')

        layout3.addLayout(layout4)
        layout3.addWidget(self.filename_box)
        layout3.addWidget(l3_label1)
        layout3.addLayout(layout5)
        layout3.addWidget(l3_label2)
        layout3.addLayout(layout6)
        layout3.addWidget(l3_label3)
        layout3.addLayout(layout7)

        layout1.addLayout(layout3)

        layout8 = QVBoxLayout()

        self.title2 = QLabel("RIGOL function generator")
        
        self.btn5 = QPushButton("Connect")
        self.btn5.clicked.connect(self.btn5_click)

        self.button6_is_checked = False
        self.btn6 = QPushButton("Run")
        self.btn6.setCheckable(True)
        self.btn6.clicked.connect(self.btn6_click)
        self.btn6.setChecked(self.button6_is_checked)

        self.btn7 = QPushButton("Stop")
        self.btn7.clicked.connect(self.btn7_click)

        layout8.addWidget(self.title2)
        layout8.addWidget(self.btn5)
        layout8.addWidget(self.btn6)
        layout8.addWidget(self.btn7)

        layout1.addLayout( layout8 )

        widget = QWidget()
        widget.setLayout(layout1)
        self.setCentralWidget(widget)

        #n_data = 50
        #self.xdata = list(range(n_data))
        #self.ydata = [random.randint(0, 10) for i in range(n_data)]
        
        # We need to store a reference to the plotted line
        # somewhere, so we can apply the new data to it.

        self._plot_ref = None
        self._plot_ref2 = None
        #self.update_plot()

        #self.show()

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        

    def PicoConnect(self):
        print(self.totalSamples)
        self.pico = pc.PicoScope(channels = [self.channel], buffersize = self.buffersize, sampleInterval = self.sampleInterval, sampleUnit = "US", totalSamples = self.totalSamples, ranges={self.channel:self.range})
        self.pico.init_buffersComplete()

    def update_plot(self):
        # Drop off the first y element, append a new one.
        #self.ydata = self.pico.buffersComplete[0][self.i*110:self.i*110+1000]
        if not self.button2_is_checked:
            self.button3_is_checked = False
            self.btn3.setChecked(self.button3_is_checked)
            self.timer.stop()

        self.ydata = self.pico.buffersComplete[0]
        #if len(self.ydata) < 1000:
        #    self.ydata = self.pico.buffersComplete[0][-1000:]
        self.xdata = np.linspace(0, self.totalSamples*self.sampleInterval/1000000, self.totalSamples) 
        # Note: we no longer need to clear the axis.
        if self._plot_ref is None:
            # First time we have no plot reference, so do a normal plot.
            # .plot returns a list of line <reference>s, as we're
            # only getting one we can take the first element.
            plot_refs = self.canvas.axes.plot(self.xdata, self.ydata, 'r')
            self.canvas.axes.set_ylim(-33000, 33000)
            self.canvas.axes.set_xlabel('Time (s)')
            self.canvas.axes.set_ylabel('Charge (arb)')
            self._plot_ref = plot_refs[0]
        else:
            # We have a reference, we can use it to update the data for that line.
            self._plot_ref.set_ydata(self.ydata)

        # Trigger the canvas to update and redraw.
        self.canvas.draw()

    def update_plot2(self):
        # Drop off the first y element, append a new one.
        #self.ydata = self.pico.buffersComplete[0][self.i*110:self.i*110+1000]
        if not self.button2_is_checked:
            self.button3b_is_checked = False
            self.btn3b.setChecked(self.button3b_is_checked)
            self.timer.stop()

        PSD = scisig.welch(self.pico.buffersComplete[0][:1000000], fs = 1/self.sampleInterval, nperseg = 10000)

        self.ydata2 = PSD[1]
        #if len(self.ydata) < 1000:
        #    self.ydata = self.pico.buffersComplete[0][-1000:]
        self.xdata2 = PSD[0]
        # Note: we no longer need to clear the axis.
        if self._plot_ref2 is None:
            # First time we have no plot reference, so do a normal plot.
            # .plot returns a list of line <reference>s, as we're
            # only getting one we can take the first element.
            plot_refs2 = self.canvas2.axes.plot(self.xdata2, self.ydata2, 'r')
            #self.canvas2.axes.set_ylim(-33000, 33000)
            self.canvas2.axes.set_xlabel('Time (s)')
            self.canvas2.axes.set_ylabel('Charge (arb)')
            self.canvas2.axes.set_yscale('log')
            self._plot_ref2 = plot_refs2[0]
        else:
            # We have a reference, we can use it to update the data for that line.
            self._plot_ref2.set_ydata(self.ydata2)

        # Trigger the canvas to update and redraw.
        self.canvas2.draw()

    def continous_plot1(self):
        if self.button3_is_checked:
            self.ydata = np.zeros(self.totalSamples)
            self.timer = QTimer()
            self.timer.setInterval(100)
            self.timer.timeout.connect(self.update_plot)
            self.timer.start()

    def btn3_click(self):
        #self.worker_Stream()
        self.button3_is_checked = self.btn3.isChecked()
        if self.button3_is_checked and self.PicoConnected: 
            print("Plotting!")
            worker_plot1 = Worker(self.continous_plot1)
            self.threadpool.start(worker_plot1)
        elif not self.PicoConnected:
            print('Not connected to a picoscope!')
            self.button3_is_checked = False
            self.btn3.setChecked(self.button3_is_checked)
        else:
            self.timer.stop()

    def btn3b_click(self):
        #self.worker_Stream()
        self.button3b_is_checked = self.btn3b.isChecked()
        if self.button3b_is_checked and self.PicoConnected: 
            print("Plotting!")
            worker_plot2 = Worker(self.continous_plot(self.update_plot2, 1000, 5001))
            self.threadpool.start(worker_plot2)
        elif not self.PicoConnected:
            print('Not connected to a picoscope!')
            self.button3b_is_checked = False
            self.btn3b.setChecked(self.button3b_is_checked)
        else:
            self.timer.stop()
        

    #def Stream(self):
    #    self.update_plot()

    def worker_Stream(self):
        print('Streaming')
        worker = Worker(self.Stream)
        # Execute
        self.threadpool.start(worker)

    def btn1_click(self):
        if not self.PicoConnected: 
            print('Connecting...')
            self.PicoConnect()
            self.PicoConnected = True
            print('Connected') 
        else:
            print('Already Connected!') 

    def btn2_click(self):
        self.button2_is_checked = self.btn2.isChecked()
        if self.button2_is_checked and self.PicoConnected: 
            print('Streaming')
            worker = Worker(self.Stream)
            # Execute
            self.threadpool.start(worker)
        elif not self.PicoConnected:
            print('Not connected to a picoscope!')
            self.button2_is_checked = False
            self.btn2.setChecked(self.button2_is_checked)
        else: 
            print('Stopping')
            if self.Check1_is_checked:
                print('Saving...')
                print(self.pico._channels)
                print(self.pico._ranges)
                #output = self.adc2mV2(self.pico.buffersComplete[0], channels = self.pico._channels, range = self.pico._ranges)
                output = self.pico.buffersComplete[0]/32767*10
                Tint = self.sampleInterval*self.global_multiplier[self.sampleInterval_unit]/10**9
                mdict = {'D': output, 'Tinterval': [Tint]}
                filename = self.filename_box.text()
                self.pico.save_data_hdf5(filename, mdict)
                print('Saved!')
            self.pico.stop()

    def Stream(self):
        if self.Check2_is_checked:
            while self.button2_is_checked and self.Check2_is_checked:
                self.pico.Stream()
                if self.Check1_is_checked:
                    print('Saving...')
                    output = self.pico.buffersComplete[0]/32767*10
                    Tint = self.sampleInterval*self.global_multiplier[self.sampleInterval_unit]/10**9
                    mdict = {'D': output, 'Tinterval': [Tint]}
                    filename = self.filename_box.text()
                    self.pico.save_data_hdf5(filename, mdict)
                    print('Saved!')
        else:
            self.pico.Stream()
            if self.Check1_is_checked:
                print('Saving...')
                output = self.pico.buffersComplete[0]/32767*10
                Tint = self.sampleInterval*self.global_multiplier[self.sampleInterval_unit]/10**9
                mdict = {'D': output, 'Tinterval': [Tint]}
                filename = self.filename_box.text()
                self.pico.save_data_hdf5(filename, mdict)
                print('Saved!')
            if self.Check2_is_checked:
                self.Stream()
        
        print('End stream1')
        self.button2_is_checked = False
        self.btn2.setChecked(self.button2_is_checked)
        print('End stream2')
        self._plot_ref = None
        self.canvas.axes.cla()
        print('End stream3')

    def btn4_click(self):
        if self.PicoConnected:
            self.button2_is_checked = False
            self.btn2.setChecked(self.button2_is_checked)
            print('Stopping')
            self.pico.stop()
            print('Closed')
            self.pico.close()
            self.PicoConnected = False
        else:
            print('Already closed!')

    def totalSample_changed(self, totalTime):
        self.totalSamples = int(totalTime*self.global_multiplier[self.totaltime_unit]/(self.sampleInterval*self.global_multiplier[self.sampleInterval_unit]))
        self._plot_ref = None
        if self.PicoConnected:
            self.pico.reinititialiseChannels(self.buffersize, self.sampleInterval, self.totalSamples)
            

    def sampleInterval_changed(self, sampleInterval):
        self.totalSamples = int(self.totalSamples*self.sampleInterval/sampleInterval)
        self.sampleInterval = sampleInterval
        print(self.totalSamples)
        if self.PicoConnected:
            self.pico.reinititialiseChannels(self.buffersize, self.sampleInterval, self.totalSamples)

    def check1_changed(self):
        if not self.Check1_is_checked:
            self.Check1_is_checked = True
        else:
            self.Check1_is_checked = False

    def check2_changed(self):
        if not self.Check2_is_checked:
            self.Check2_is_checked = True
            self.l3_double1.setDisabled(True)
        else:
            self.Check2_is_checked = False
            self.l3_double1.setDisabled(False)

    def btn5_click(self):
        if not self.RIGOLConnected:
            print('Connnecting...')
            self.DG822 = rig.FuncGen(self._VISA_ADDRESS_rigol)
            self.RIGOLConnected = True
            control_voltage = self.VOLT_PULSE/500

            self.DG822.sin_wave(channel = 1, amp=self.VOLT_SIN, freq=self.FREQ_SIN, )
            self.DG822.pulse(channel = 2, amp=control_voltage, duty=4, freq=self.FREQ_PULSE, off=control_voltage/2)
            print('Connected')
        else:
            print('Already Connected!')


    def btn6_click(self):
        if self.RIGOLConnected:
            self.button6_is_checked = self.btn6.isChecked()
            self.RIGOLOutputOn = True
            self.DG822.turn_on(channel = 1)
            print('Drive on')
            time.sleep(5)
            self.DG822.turn_on(channel = 2)
            print('HV triggered')

    def btn7_click(self):
        if self.button6_is_checked:
            self.button6_is_checked = False
            self.btn6.setChecked(self.button6_is_checked)
        
        if self.RIGOLConnected and self.RIGOLOutputOn:
            self.DG822.turn_off(channel = 2)
            print('HV switched off')
            time.sleep(5)
            self.DG822.turn_off(channel = 1)
            print('Drive off')

    def channel_changed(self):
        self.channel = self.canvas_drop_channel.currentText()
        if self.PicoConnected:
            print(self.canvas_drop_channel.currentIndex())
            print(self.canvas_drop_channel.currentText())
            self.pico.setChannel(channel = self.channel, channel_range = self.range, analogue_offset = 0.0)
            self.pico.reinititialiseChannels(self.buffersize, self.sampleInterval, self.totalSamples)
    
    def range_changed(self):
        self.range = self.canvas_drop_range.currentIndex()
        if self.PicoConnected:
            print(self.canvas_drop_range.currentIndex())
            print(self.canvas_drop_range.currentText())
            self.pico.setChannel(channel = self.channel, channel_range = self.range, analogue_offset = 0.0)
            self.pico.reinititialiseChannels(self.buffersize, self.sampleInterval, self.totalSamples)

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
print('Done')