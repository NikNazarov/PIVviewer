import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
plt.ioff()
import numpy as np
from PlotterFunctions import Database, save_table, autoscale_y, make_name
from scipy.interpolate import RectBivariateSpline
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import (
    QFrame,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QTextEdit,
    QWidget,
    QComboBox,
    QSlider,
    QLabel,
    QLCDNumber,
    QMessageBox
)


def show_message(message: str) -> None:
    msgbox = QMessageBox()
    msgbox.setIcon(QMessageBox.Information)
    msgbox.setText(message)
    msgbox.setStandardButtons(QMessageBox.Ok)
    msgbox.buttonClicked.connect(msgbox.close)
    msgbox.exec_()


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self,  parent=None, width=6, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)
        self.axes  = self.fig.add_subplot(1, 1, 1)
        self.key   = None
        self.line  = None
        self.field = None
        self.fig.tight_layout()
        self.data  = Database()
        self.x_data = None
        self.y_data = None
        self.orientation = True #True for horizontal and False for vertical

    def change_orientation(self, key):
        self.orientation = not self.orientation
        if self.line is None:
            return
        self.line.remove()
        self.line = None
    
    def update_canvas(self):
        self.fig.canvas.draw()

class PIVcanvas(MplCanvas):
    topChanged  = pyqtSignal(float)
    botChanged  = pyqtSignal(float)
    lineChanged = pyqtSignal(float)
    def __init__(self):
        super().__init__()
    
        self.coords      = None
        self.cb          = None
        self.streamlines = None
        self.pos_scale   = 1.
        self.neg_scale   = 1.
        self.visible_lines = False
        self.visible_line = True
        self.img_data = None
        self.axes.axis("off")

    def change_orientation(self, key):
        self.orientation = not self.orientation
        if self.line is None:
            return
        self.line.remove()
        self.line = None

    def draw_horizontal(self, value):
        if self.line is None:
            self.line, = self.axes.plot(self.x_data, np.ones_like(self.x_data)*self.y_data[value], 
                            linewidth=1.5, color="white")
        self.line.set_ydata(np.ones_like(self.x_data)*self.y_data[value])
        self.lineChanged.emit(self.y_data[value])

    def draw_vertical(self, value):
        if self.line is None:
            self.line, = self.axes.plot(np.ones_like(self.y_data)*self.x_data[value], 
            self.y_data, linewidth=1.5, color="white")
        self.line.set_xdata(np.ones_like(self.y_data)*self.x_data[value])
        self.lineChanged.emit(self.x_data[value])
    

    def draw_line(self, value):
        if self.x_data is None:
            return
        if self.orientation:
            self.draw_horizontal(value)
        else:
            self.draw_vertical(value)
        self.update_canvas()

    def hide_line(self):
        if self.line is None:
            return
        self.visible_line = not self.visible_line
        self.line.set_visible(self.visible_line)
        self.update_canvas()

    def set_coords(self):
        if self.coords is not None:
            return
        
        piv_data = self.data.get()
        x, y = [*piv_data.values()][:2]
        self.coords = x, y
        self.x_data = x[0]
        self.y_data = y[:, 0]
    
    def set_field(self, key):
        self.set_coords()
        self.key = key
        piv_data = self.data.get()
        field = piv_data[key]
        self.pos_avg = np.max(np.abs(field), initial=0)
        self.neg_avg = -self.pos_avg
        if isinstance(self.cb, matplotlib.colorbar.Colorbar):
            self.cb.remove()
        if isinstance(self.img_data, matplotlib.collections.QuadMesh):
            self.img_data.remove()
        self.img_data = self.axes.pcolormesh(*self.coords, 
                                            field, 
                                            cmap="jet", 
                                            shading='auto',
                                            vmin=self.neg_avg*self.neg_scale,
                                            vmax=self.pos_avg*self.pos_scale,
                                            )
        self.cb = self.fig.colorbar(self.img_data, ax=self.axes)
        self.update_canvas()

    def set_v_max(self, value):
        if self.img_data is None:
            return
        value = (value-1000)/1000
        if value*self.pos_avg <= self.neg_avg*self.neg_scale:
            return
        self.pos_scale = value
        self.topChanged.emit(value*self.pos_avg)
        self.set_field(self.key)

    def set_v_min(self, value):
        if self.img_data is None:
            return
        value = (1000-value)/1000
        if value*self.neg_avg >= self.pos_scale*self.pos_avg:
            return
        self.neg_scale = value
        self.botChanged.emit(value*self.neg_avg)
        self.set_field(self.key)

    def draw_stremlines(self):
        piv_data = self.data.get()
        u, v = [*piv_data.values()][2:4]
        x0 = self.x_data
        y0 = self.y_data
        xi = np.linspace(x0.min(), x0.max(), y0.size)
        yi = np.linspace(y0.min(), y0.max(), x0.size)
        ui = RectBivariateSpline(x0, y0, u.T)(xi, yi)
        vi = RectBivariateSpline(x0, y0, v.T)(xi, yi)
        self.streamlines = self.axes.streamplot(xi, yi, ui.T, vi.T, 
            density=4, linewidth=.8, arrowsize=.8, color="black"
            )
        self.update_canvas()

    def hide_streamlines(self):
        if self.streamlines is None:
            self.draw_stremlines()
        self.visible_lines = not self.visible_lines
        self.streamlines.lines.set_visible(self.visible_lines)
        self.streamlines.arrows.set_visible(self.visible_lines)
        self.update_canvas()

class ProfileCanvas(MplCanvas):
    def __init__(self):
        super().__init__()
        self.axes  = self.fig.add_subplot(1, 1, 1)
        self.axes.autoscale(True)
        self.axes.grid(linestyle = '--', linewidth = 0.7)

    def set_field(self, key):
        piv_data = self.data.get()
        self.field = piv_data[key]
        self.key = key
        x, y =  [*piv_data.values()][:2]
        self.x_data = x[0]
        self.y_data = y[:, 0]

    def draw_horizontal(self, value):
        if self.line is None:
            self.line, = self.axes.plot(self.x_data, self.field[value,:], 
                    linewidth=.8, color="red", marker='s')
        self.line.set_ydata(self.field[value,:])

    def draw_vertical(self, value):
        if self.line is None:
            self.line, = self.axes.plot(self.y_data, self.field[:,value], 
                    linewidth=.8, color="red", marker='s')
        self.line.set_ydata(self.field[:,value])

    def draw_line(self, value):
        if self.field is None:
            return
        if self.orientation:
            self.draw_horizontal(value)
        else:
            self.draw_vertical(value)
        autoscale_y(self.axes)
        self.update_canvas()
    
    def save_profile(self):
        if self.line is None:
            return
        x_data = self.line.get_xdata()
        y_data = self.line.get_ydata()
        data = {
            "x[mm]" if self.orientation else "y[mm]": x_data,
            self.key: y_data
        }
        filename, save_dir = make_name(self.data.name, self.key, self.orientation)
        save_table(filename, save_dir, data)
        show_message(f"Profile{self.key} saved in \n{save_dir}")

        

class PIVWidget(QWidget):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.piv     = PIVcanvas()
        self.profile = ProfileCanvas()
        self.initUI()


    def initUI(self):
        piv_toolbar     = NavigationToolbar(self.piv, self)
        profile_toolbar = NavigationToolbar(self.profile, self)
        piv_box = QVBoxLayout()
        piv_box.addWidget(piv_toolbar)
        piv_box.addWidget(self.piv)

        profile_box = QVBoxLayout()
        profile_box.addWidget(profile_toolbar)
        profile_box.addWidget(self.profile)

        layout = QHBoxLayout()
        layout.addLayout(piv_box)
        layout.addLayout(profile_box)

        self.setLayout(layout)

class ListSlider(QSlider):
    elementChanged = pyqtSignal(int)

    def __init__(self, values=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimum(0)
        self._values = []
        self.valueChanged.connect(self._on_value_changed)
        self.values = values or []

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._values = values
        maximum = max(0, len(self._values) - 1)
        self.setMaximum(maximum)
        self.setValue(0)

    @pyqtSlot(int)
    def _on_value_changed(self, index):
        value = self.values[index]
        self.elementChanged.emit(value)
    
class ControlsWidget(QWidget):
    fieldchosen = pyqtSignal(str)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filename = QTextEdit()
        self.regime_box = QComboBox()
        self.data = Database()
        self.setFixedHeight(120)

        self.initUI()
    def initUI(self):
        file_box = QHBoxLayout()
        file_button = QPushButton("Select file")
        file_button.clicked.connect(self.open_dialog)
        self.filename.setFixedHeight(35)
        file_box.addWidget(self.filename)
        file_box.addWidget(file_button)

        control_v = QVBoxLayout()

        control_v.addLayout(file_box)

        settings_h = QHBoxLayout()

        settings_h.addWidget(self.regime_box)

        control_v.addLayout(settings_h)

        bottom_left_frame = QFrame()
        bottom_left_frame.setLayout(control_v)
        bottom_left_frame.setLineWidth(1)
        bottom_left_frame.setFrameStyle(QFrame.Panel)        


        self.pos_scale_slider = ListSlider(orientation=Qt.Horizontal)
        self.neg_scale_slider = ListSlider(orientation=Qt.Horizontal)
        self.pos_scale_slider.setFixedWidth(200)
        self.neg_scale_slider.setFixedWidth(200)

        self.slider_LCD = QLCDNumber()
        self.slider_LCD.setFrameShape(QFrame.NoFrame)
        self.slider_LCD.setSegmentStyle(QLCDNumber.Flat)

        self.save_btn = QPushButton("Save profile")
        self.slider = ListSlider(orientation=Qt.Horizontal)
        self.streamlines_btn = QPushButton("Show streamlines")
        self.streamlines_btn.clicked.connect(self.hide_streamlines)
        self.orientation_qbox = QComboBox()
        self.orientation_qbox.setFixedWidth(100)
        self.hide_lines = QPushButton("Hide line")
        self.hide_lines.clicked.connect(self.hide_profile_lines)
        slider_box = QHBoxLayout()
        slider_box.addWidget(self.slider)
        slider_box.addWidget(self.slider_LCD)
        slider_box.addWidget(self.orientation_qbox)
        hide_box = QHBoxLayout()
        hide_box.addWidget(self.save_btn)
        hide_box.addWidget(self.streamlines_btn)
        hide_box.addWidget(self.hide_lines)
        bottom_right_box = QVBoxLayout()
        bottom_right_box.addLayout(slider_box)
        bottom_right_box.addLayout(hide_box)

        
        bottom_right_frame = QFrame()
        bottom_right_frame.setLayout(bottom_right_box)
        bottom_right_frame.setLineWidth(1)
        bottom_right_frame.setFrameStyle(QFrame.Panel)

        self.top_LCD = QLCDNumber()
        self.bot_LCD = QLCDNumber()
        self.top_LCD.setFrameShape(QFrame.NoFrame)
        self.bot_LCD.setFrameShape(QFrame.NoFrame)
        self.top_LCD.setSegmentStyle(QLCDNumber.Flat)
        self.bot_LCD.setSegmentStyle(QLCDNumber.Flat)

        slider_top_box = QHBoxLayout()
        slider_top_box.addWidget(QLabel("Max scale"))
        slider_top_box.addWidget(self.top_LCD)

        slider_bot_box = QHBoxLayout()
        slider_bot_box.addWidget(QLabel("Min scale"))
        slider_bot_box.addWidget(self.bot_LCD)

        sliders_box = QVBoxLayout()
        sliders_box.addLayout(slider_top_box)
        sliders_box.addWidget(self.pos_scale_slider)
        sliders_box.addLayout(slider_bot_box)
        sliders_box.addWidget(self.neg_scale_slider)

        main_box = QHBoxLayout()
        main_box.addWidget(bottom_left_frame)
        main_box.addLayout(sliders_box)
        main_box.addWidget(bottom_right_frame)

        self.setLayout(main_box)
    
    def hide_streamlines(self):
        if self.streamlines_btn.text() == "Hide streamlines":
            self.streamlines_btn.setText("Show streamlines")
        else:
            self.streamlines_btn.setText("Hide streamlines")

    def hide_profile_lines(self):
        if self.hide_lines.text() == "Hide line":
            self.hide_lines.setText("Show line")
        else:
            self.hide_lines.setText("Hide line")

    @pyqtSlot(str)
    def on_activated(self, key):
        if key is None:
            return
        self.fieldchosen.emit(key)

    @pyqtSlot(str)
    def on_orientation(self, key):
        piv_data = self.data.get()
        if key == "Horizontal":
            self.slider.values = piv_data[[*piv_data.keys()][1]][:, 0]
        else:
            self.slider.values = piv_data[[*piv_data.keys()][0]][0]

        self.fieldchosen.emit(key)
        
    def open_dialog(self, checked):
        name, check = QFileDialog.getOpenFileName()
        if not check:
            return
        self.filename.setText(name)
        self.data.load(name)
        piv_data = self.data.get()
        self.regime_box.clear()
        self.regime_box.addItems([*piv_data.keys()][2:])
        self.regime_box.activated[str].connect(self.on_activated)
        self.orientation_qbox.clear()
        self.orientation_qbox.addItems(["Horizontal", "Vertical"])
        self.orientation_qbox.activated[str].connect(self.on_orientation)
        self.slider.values = piv_data[[*piv_data.keys()][1]][:, 0]
        self.slider.setValue(0)
        self.pos_scale_slider.values = list(range(2000))
        self.pos_scale_slider.setValue(1999)
        self.neg_scale_slider.values = list(range(2000))
        self.neg_scale_slider.setValue(0)
