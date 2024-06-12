import sys
import traceback
import numpy as np
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import picoscope_utils.Picoscope_control as pc

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

        self.setWindowTitle("My App")

        layout1 = QHBoxLayout()
        layout2 = QVBoxLayout()
        layout3 = QVBoxLayout()

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

        self.btn4 = QPushButton("Stop and close")
        self.btn4.clicked.connect(self.btn4_click)

        layout2.addWidget(self.btn1)
        layout2.addWidget(self.btn2)
        layout2.addWidget(self.btn3)
        layout2.addWidget(self.btn4)

        layout1.addLayout( layout2 )

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layout1.addWidget(self.canvas)

        l3_label1 = QLabel("Total time")
        l3_label2 = QLabel("Sampling interval")
        l3_label3 = QLabel("Buffer Size")

        self.l3_double1 = QSpinBox()
        self.l3_double1.setMinimum(1)
        self.l3_double1.setMaximum(99999)
        self.l3_double1.setSingleStep(1)
        self.l3_double1.valueChanged.connect(self.totalSample_changed)

        l3_double2 = QSpinBox()
        l3_double2.setMinimum(1)
        l3_double2.setMaximum(999)
        l3_double2.setSingleStep(1)
        
        l3_double3 = QSpinBox()
        l3_double3.setMinimum(1)
        l3_double3.setMaximum(999)
        l3_double3.setSingleStep(1)

        l3_drop1 = QComboBox()
        l3_drop1.addItems(["s", "ms", "us", "ns"])

        l3_drop2 = QComboBox()
        l3_drop2.addItems(["s", "ms", "us", "ns"])

        l3_drop3 = QComboBox()
        l3_drop3.addItems(["s", "ms", "us", "ns"])

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
        layout5.addWidget(l3_drop1)

        layout6.addWidget(l3_double2)
        layout6.addWidget(l3_drop2)

        layout7.addWidget(l3_double3)
        layout7.addWidget(l3_drop3)

        layout3.addLayout(layout4)
        layout3.addWidget(l3_label1)
        layout3.addLayout(layout5)
        layout3.addWidget(l3_label2)
        layout3.addLayout(layout6)
        layout3.addWidget(l3_label3)
        layout3.addLayout(layout7)

        layout1.addLayout(layout3)

        widget = QWidget()
        widget.setLayout(layout1)
        self.setCentralWidget(widget)

        #n_data = 50
        #self.xdata = list(range(n_data))
        #self.ydata = [random.randint(0, 10) for i in range(n_data)]
        
        # We need to store a reference to the plotted line
        # somewhere, so we can apply the new data to it.

        self._plot_ref = None
        #self.update_plot()

        #self.show()

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.totalSamples = 10000
        self.sampleInterval = 1000
        self.buffersize = 100

        self.PicoConnected = False

    def PicoConnect(self):
        self.pico = pc.PicoScope(channels = ["A"], buffersize = self.buffersize, sampleInterval = self.sampleInterval, sampleUnit = "US", totalSamples = self.totalSamples)
        self.pico.init_buffersComplete()

    def update_plot(self):
        # Drop off the first y element, append a new one.
        #self.ydata = self.pico.buffersComplete[0][self.i*110:self.i*110+1000]
        if not self.button2_is_checked:
            self.button3_is_checked = False
            self.btn3.setChecked(self.button3_is_checked)
            self.timer.stop()

        self.ydata = 1*self.pico.buffersComplete[0]
        #if len(self.ydata) < 1000:
        #    self.ydata = self.pico.buffersComplete[0][-1000:]
        self.xdata = np.linspace(0, self.totalSamples/self.sampleInterval, self.totalSamples) 
        # Note: we no longer need to clear the axis.
        if self._plot_ref is None:
            
            # First time we have no plot reference, so do a normal plot.
            # .plot returns a list of line <reference>s, as we're
            # only getting one we can take the first element.
            plot_refs = self.canvas.axes.plot(self.xdata, self.ydata, 'r')
            self.canvas.axes.set_ylim(-20000, 20000)
            self._plot_ref = plot_refs[0]
        else:
            # We have a reference, we can use it to update the data for that line.
            self._plot_ref.set_ydata(self.ydata)

        # Trigger the canvas to update and redraw.
        self.canvas.draw()

    def btn3_click(self):
        #self.worker_Stream()
        self.button3_is_checked = self.btn3.isChecked()
        if self.button3_is_checked and self.PicoConnected: 
            print("Plotting!")
            self.ydata = np.zeros(self.totalSamples)
            self.timer = QTimer()
            self.timer.setInterval(100)
            self.timer.timeout.connect(self.update_plot)
            self.timer.start()
        elif not self.PicoConnected:
            print('Not connected to a picoscope!')
            self.button3_is_checked = False
            self.btn3.setChecked(self.button3_is_checked)
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
                mdict = {'A': self.pico.buffersComplete[0]}
                filename = 'C:/Users/thoma/Documents/SIMPLE/Data/PicoTest/test.hdf5'
                self.pico.save_data_hdf5(filename, mdict)
            self.pico.stop()

    def Stream(self):
        if self.Check2_is_checked:
            while self.button2_is_checked and self.Check2_is_checked:
                self.pico.Stream()
                if self.Check1_is_checked:
                    mdict = {'A': self.pico.buffersComplete[0]}
                    filename = 'C:/Users/thoma/Documents/SIMPLE/Data/PicoTest/test.hdf5'
                    self.pico.save_data_hdf5(filename, mdict)
        else:
            self.pico.Stream()
            if self.Check1_is_checked:
                mdict = {'A': self.pico.buffersComplete[0]}
                filename = 'C:/Users/thoma/Documents/SIMPLE/Data/PicoTest/test.hdf5'
                self.pico.save_data_hdf5(filename, mdict)
            if self.Check2_is_checked:
                self.Stream()
        self.button2_is_checked = False
        self.btn2.setChecked(self.button2_is_checked)

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

    def totalSample_changed(self, i):
        self.totalSamples = i

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

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
print('Done')