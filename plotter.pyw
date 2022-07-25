import sys
import logging
import traceback
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QMessageBox
)
from widgets import PIVWidget, ControlsWidget
# basic logger functionality
log = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
log.addHandler(handler)

def show_exception_box(log_msg):
    """
    Checks if a QApplication instance is available and shows a messagebox with the exception message. 
    If unavailable (non-console application), log an additional notice.
    """
    #NOT IMPLEMENTED
    def onclick(button):
        if button.text() == "OK":
            QApplication.exit()
        elif button.text() == "Retry":
            pass


    if QApplication.instance() is not None:
            errorbox = QMessageBox()
            errorbox.setIcon(QMessageBox.Critical)
            errorbox.setText(f"Oops. An unexpected error occured:\n{log_msg}")
            errorbox.setStandardButtons(QMessageBox.Ok)
            errorbox.buttonClicked.connect(onclick)
            errorbox.exec_()
    else:
        log.debug("No QApplication instance available.")


 
class UncaughtHook(QObject):
    _exception_caught = pyqtSignal(object)
 
    def __init__(self, *args, **kwargs):
        super(UncaughtHook, self).__init__(*args, **kwargs)

        # this registers the exception_hook() function as hook with the Python interpreter
        sys.excepthook = self.exception_hook

        # connect signal to execute the message box function always on main thread
        self._exception_caught.connect(show_exception_box)
 
    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """
        Function handling uncaught exceptions.
        It is triggered each time an uncaught exception occurs. 
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # ignore keyboard interrupt to support console applications
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        else:
            exc_info = (exc_type, exc_value, exc_traceback)
            log_msg = '\n'.join([''.join(traceback.format_tb(exc_traceback)),
                                 '{0}: {1}'.format(exc_type.__name__, exc_value)])
            log.critical("Uncaught exception:\n {0}".format(log_msg), exc_info=exc_info)

            # trigger message box show
            self._exception_caught.emit(log_msg)

# create a global instance of our class to register the hook
qt_exception_hook = UncaughtHook()


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.piv_widget = PIVWidget()
        self.controls = ControlsWidget()
        self.controls.hide_lines.clicked.connect(self.piv_widget.piv.hide_line)
        self.controls.save_btn.clicked.connect(self.piv_widget.profile.save_profile)
        self.controls.regime_box.activated[str].connect(self.piv_widget.piv.set_field)
        self.controls.regime_box.activated[str].connect(self.piv_widget.profile.set_field)
        self.controls.slider.valueChanged.connect(self.piv_widget.piv.draw_line)
        self.controls.slider.valueChanged.connect(self.piv_widget.profile.draw_line)
        self.controls.pos_scale_slider.valueChanged.connect(self.piv_widget.piv.set_v_max)
        self.controls.neg_scale_slider.valueChanged.connect(self.piv_widget.piv.set_v_min)
        self.controls.streamlines_btn.clicked.connect(self.piv_widget.piv.hide_streamlines)
        self.controls.orientation_qbox.activated[str].connect(self.piv_widget.profile.change_orientation)
        self.controls.orientation_qbox.activated[str].connect(self.piv_widget.piv.change_orientation)
        self.piv_widget.piv.topChanged.connect(self.controls.top_LCD.display)
        self.piv_widget.piv.botChanged.connect(self.controls.bot_LCD.display)
        self.piv_widget.piv.lineChanged.connect(self.controls.slider_LCD.display)

        self.initUI()
   
    def initUI(self):

        layout = QVBoxLayout()
        layout.addWidget(self.piv_widget)
        layout.addWidget(self.controls)

        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("fusion")
    app.setFont(QFont("Helvetica", 12))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
