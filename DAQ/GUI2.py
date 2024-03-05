import sys
import random
import numpy as np
from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt6.QtGui import QPalette, QColor

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import picoscope_utils.Picoscope_control as pc

class Color(QWidget):

    def __init__(self, color):
        super(Color, self).__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(palette)

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

        layout1.setContentsMargins(0,0,0,0)
        layout1.setSpacing(20)

        self.button_is_checked = False

        self.btn1 = QPushButton("red")
        self.btn1.setCheckable(True)
        self.btn1.clicked.connect(self.btn1_click)
        self.btn1.setChecked(self.button_is_checked)

        self.btn2 = QPushButton("yellow")
        self.btn2.clicked.connect(self.btn2_click)

        btn3 = QPushButton("purple")

        layout2.addWidget(self.btn1)
        layout2.addWidget(self.btn2)
        layout2.addWidget(btn3)

        layout1.addLayout( layout2 )

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layout1.addWidget(self.canvas)

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

        self.pico = pc.PicoScope(channels = ["A"], buffersize = 100, sampleInterval = 1000, sampleUnit = "US", totalSamples = 100)


    def update_plot(self):
        # Drop off the first y element, append a new one.
        self.ydata = self.pico.buffersComplete[0]
        self.xdata = np.linspace(0, 0.1, 100)

        # Note: we no longer need to clear the axis.
        if self._plot_ref is None:
            # First time we have no plot reference, so do a normal plot.
            # .plot returns a list of line <reference>s, as we're
            # only getting one we can take the first element.
            plot_refs = self.canvas.axes.plot(self.xdata, self.ydata, 'r')
            self._plot_ref = plot_refs[0]
        else:
            # We have a reference, we can use it to update the data for that line.
            self._plot_ref.set_ydata(self.ydata)

        # Trigger the canvas to update and redraw.
        self.canvas.draw()

    def btn1_click(self):
        self.button_is_checked = self.btn1.isChecked()
        print("Clicked!")
        print(self.btn1.isChecked())
        # Setup a timer to trigger the redraw by calling update_plot.
        if self.button_is_checked:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(100)
            self.timer.timeout.connect(self.Stream)
            self.timer.start()
        else:
            self.timer.stop()

    def Stream(self):
        self.pico.Stream()
        self.update_plot()

    def btn2_click(self):
        self.pico.stop()
        self.pico.close()

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
print('Done')