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

        self.button_is_checked = False

        self.btn1 = QPushButton("Show")
        self.btn1.setCheckable(True)
        self.btn1.clicked.connect(self.btn1_click)
        self.btn1.setChecked(self.button_is_checked)

        self.btn2 = QPushButton("Run")
        self.btn2.clicked.connect(self.btn2_click)

        self.btn3 = QPushButton("Close")
        self.btn3.clicked.connect(self.btn3_click)

        layout2.addWidget(self.btn1)
        layout2.addWidget(self.btn2)
        layout2.addWidget(self.btn3)

        layout1.addLayout( layout2 )

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layout1.addWidget(self.canvas)

        l3_label1 = QLabel("Total time")
        l3_label2 = QLabel("Sampling interval")
        l3_label3 = QLabel("Buffer Size")

        l3_double1 = QSpinBox()
        l3_double1.setMinimum(1)
        l3_double1.setMaximum(99999)
        l3_double1.setSingleStep(1)
        l3_double1.valueChanged.connect(self.totalSample_changed)

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

        layout4 = QHBoxLayout()
        layout5 = QHBoxLayout()
        layout6 = QHBoxLayout()

        layout4.addWidget(l3_double1)
        layout4.addWidget(l3_drop1)

        layout5.addWidget(l3_double2)
        layout5.addWidget(l3_drop2)

        layout6.addWidget(l3_double3)
        layout6.addWidget(l3_drop3)

        layout3.addWidget(l3_label1)
        layout3.addLayout(layout4)
        layout3.addWidget(l3_label2)
        layout3.addLayout(layout5)
        layout3.addWidget(l3_label3)
        layout3.addLayout(layout6)

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

        self.totalSamples = 3000
        self.sampleInterval = 1000
        self.buffersize = 100

        self.PicoConnect()

    def PicoConnect(self):
        self.pico = pc.PicoScope(channels = ["A"], buffersize = self.buffersize, sampleInterval = self.sampleInterval, sampleUnit = "US", totalSamples = self.totalSamples)

    def update_plot(self):
        # Drop off the first y element, append a new one.
        self.ydata = self.pico.buffersComplete[0][self.i*100:self.i*100+1000]
        self.xdata = np.linspace(0, 1, 1000) 
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

    def stepi(self):
        self.i += 1

    def btn1_click(self):
        self.button_is_checked = self.btn1.isChecked()
        print("Plotting!")
        if self.button_is_checked:
            self.i = 0
            self.timer = QTimer()
            self.timer.setInterval(100)
            self.timer.timeout.connect(self.update_plot)
            self.timer.timeout.connect(self.stepi)
            self.timer.start()
        else:
            self.timer.stop()
        

    #def Stream(self):
    #    self.update_plot()

    def btn2_click(self):
        print('Streaming')
        worker = Worker(self.Stream)
        # Execute
        self.threadpool.start(worker)

    def Stream(self):
        self.pico.Stream()

    def btn3_click(self):
        self.pico.stop()
        self.pico.close()

    def totalSample_changed(self, i):
        self.totalSamples = i

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
print('Done')