#! /usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Dieter Vansteenwegen'
__project__ = 'Novastar_MCTRL300_basic_controller'
__project_link__ = 'https://github.com/dietervansteenwegen/Novastar_MCTRL300_basic_controller'

from typing import List
import novastar_mctrl300.mctrl300 as mctrl300
import serial.serialutil
from novastar_mctrl300 import serports
from PyQt5 import QtWidgets
import logging
import logging.handlers
import datetime as dt

from .main_window import Ui_MainWindow

LOG_FMT = (
    '%(asctime)s|%(levelname)-8.8s|%(module)-15.15s|%(lineno)-0.3d|'
    '%(funcName)-20.20s |%(message)s'
)
DATEFMT = '%d/%m/%Y %H:%M:%S'
LOGFILE = './logfile.log'
LOGMAXBYTES = 500000


class MilliSecondsFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # sourcery skip: lift-return-into-if, remove-unnecessary-else
        ct = dt.datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime(DATEFMT)
            s = f'{t}.{int(record.msecs)}'
        return s


def setup_logger() -> logging.Logger:
    """Setup logging.
    Returns logger object with (at least) 1 streamhandler to stdout.

    Returns:
        logging.Logger: configured logger object
    """
    logger = logging.getLogger()  # DON'T specifiy name in order to create root logger!
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()  # handler to stdout
    stream_handler.setLevel(logging.ERROR)
    stream_handler.setFormatter(MilliSecondsFormatter(LOG_FMT))
    logger.addHandler(stream_handler)
    return logger


def add_rotating_file(logger: logging.Logger) -> logging.Logger:
    rot_fil_handler = logging.handlers.RotatingFileHandler(
        LOGFILE,
        maxBytes=LOGMAXBYTES,
        backupCount=3,
    )
    rot_fil_handler.doRollover()
    rot_fil_handler.setLevel(logging.DEBUG)
    rot_fil_handler.setFormatter(MilliSecondsFormatter(LOG_FMT))
    logger.addHandler(rot_fil_handler)

    return logger


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        log = setup_logger()
        self.log = add_rotating_file(log)
        self.log.debug('Starting')
        self.setupUi(self)
        self._refresh_serial_ports()
        self.serport = None
        self.led_screen = None
        self.state = 1
        self._connect_slots()
        self._update_to_state()
        self._set_up_timer_brightness()

    def _set_up_timer_brightness(self):
        # TODO: Timer querying brightness and setting slider value + label
        # TODO: Code for setting/getting brightness
        pass

    def _connect_slots(self):
        self.btn_serial_refresh.clicked.connect(self._refresh_serial_ports)
        self.btn_serial_open.clicked.connect(lambda checked: self._open_serial_port(checked))
        self.cmb_output.currentIndexChanged.connect(lambda index: self._output_changed(index))
        self.btn_blackout.clicked.connect(self._pattern_black)
        self.btn_blue.clicked.connect(self._pattern_blue)
        self.btn_freeze.clicked.connect(self._pattern_freeze)
        self.btn_green.clicked.connect(self._pattern_green)
        self.btn_normal.clicked.connect(self._pattern_normal)
        self.btn_red.clicked.connect(self._pattern_red)
        self.btn_slash.clicked.connect(self._pattern_slash)
        self.btn_white.clicked.connect(self._pattern_white)
        self.sldr_brightness.sliderMoved.connect(self._brightness_slider_moved)
        self.set_normal.triggered.connect(self._pattern_normal)
        self.set_red.triggered.connect(self._pattern_red)
        self.set_green.triggered.connect(self._pattern_green)
        self.set_blue.triggered.connect(self._pattern_blue)
        self.set_white.triggered.connect(self._pattern_white)
        self.set_slash.triggered.connect(self._pattern_slash)
        # self.set_blackout.triggered.connect(self._pattern_blackout)
        self.set_freeze.triggered.connect(self._pattern_freeze)
        self.log.debug('Signals/slots connected')

    def _brightness_slider_moved(self, v):
        # TODO: send out brightness set commands
        self.lbl_brightness_value.setText(str(v))
        if self.led_screen:
            self.led_screen.set_brightness(self.selected_port, v)

    def _output_changed(self, index: int):
        if index == 0 or self.serport is None:
            self.led_screen = None
            self._change_state_to(2)
        elif index == 1:
            self.led_screen = mctrl300.MCTRL300(serport=self.serport)
            self.selected_port = 1
            self._change_state_to(3)
            self._update_brightness_from_screen()
        elif index == 2:
            self.led_screen = mctrl300.MCTRL300(serport=self.serport)
            self.selected_port = 2
            self._change_state_to(3)
            self._update_brightness_from_screen()

    def _update_brightness_from_screen(self) -> None:
        brightness = self.led_screen.get_brightness(self.selected_port)
        self.log.debug(f'Querying brightness from output {self.selected_port}')
        if brightness is not None:
            self.lbl_brightness_value.setText(brightness.__str__())
            self.sldr_brightness.setValue(brightness)
            self.log.debug(f'Response: {brightness}')
        else:
            QtWidgets.QMessageBox.critical(
                self,
                'No reply from screen',
                'Screen did not reply when requesting current brightness'
                f' from output {self.selected_port}. Check connections and configuration...',
                buttons=QtWidgets.QMessageBox.Ok,
            )
            self.log.error('Issue while getting brightness.', exc_info=True)
            self.cmb_output.setCurrentIndex(0)
            self._change_state_to(2)

    def _refresh_serial_ports(self) -> None:
        self.lst_serial_ports.clear()
        self.serial_available_ports: List = []
        for port in sorted(serports.get_available_ports()):
            self.serial_available_ports.append(port)
            self.log.debug(f'Found serial port: {port[1:]}')
            self.lst_serial_ports.addItem(f' {port[1]}  ({port[2]}, {port[3]})')
            # if port[3][:6] == 'CP2102':
            # TODO: color item in list green (this is a possible controller)
        if len(self.serial_available_ports) > 0:
            self.btn_serial_open.setEnabled(True)
            self.lst_serial_ports.setCurrentRow(0)
        else:
            self.btn_serial_open.setEnabled(False)
            self.lbl_serial_status.setText('No ports found...')
            self.lbl_serial_status.setStyleSheet('background-color:orange')
            self._change_state_to(1)

    def _open_serial_port(self, checked) -> None:
        if checked:
            if len(self.serial_available_ports) == 0:
                # self.lbl_serial_status.setText('No serial ports')
                self.btn_serial_open.setChecked(False)
                self._change_state_to(1)
                return
            index = self.lst_serial_ports.currentRow()
            try:
                p = self.serial_available_ports[index]
                self.log.debug(f'opening serial port {p[1:]}')
                self.serport = serports.Mctrl300Serial(p[1])
            except (FileNotFoundError, serial.serialutil.SerialException):
                self.log.exception('Issue during opening.')
                self._refresh_serial_ports()
                self.btn_serial_open.setChecked(False)
                self._change_state_to(1)
            if self.serport and self.serport.isOpen():
                self.lbl_serial_status.setText(f'Opened {self.serial_available_ports[index][1]}')
                self.log.debug('Port open.')
                self.btn_serial_open.setText(
                    f'Click to close {self.serial_available_ports[index][1]}', )
                self.lbl_serial_status.setStyleSheet('background-color:green')
                self._change_state_to(2)
            else:
                self.log.error(f'Issue during opening port {p}.')
                self.lbl_serial_status.setText('Error opening port. See logs.')
                self.lbl_serial_status.setStyleSheet('background-color:red')
                self.serport = None
                self._change_state_to(1)
        else:
            if self.serport:
                self.serport.close()
                self.log.debug(f'Closed {self.serport}')
            self.lbl_serial_status.setText('Closed serial port')
            self.lbl_serial_status.setStyleSheet('background-color:orange')
            self.btn_serial_open.setText('Click to open selected port')
            self._change_state_to(1)

    def _change_state_to(self, state: int):
        if state == 2 and self.cmb_output.currentIndex() > 0:
            state = 3
        self.state = state
        self._update_to_state()

    def _update_to_state(self):
        self.cmb_output.setEnabled(self.state > 1)
        self.menubar_pattern.setEnabled(self.state > 2)
        self.sldr_brightness.setEnabled(self.state > 2)
        self.btn_normal.setEnabled(self.state > 2)
        self.btn_red.setEnabled(self.state > 2)
        self.btn_green.setEnabled(self.state > 2)
        self.btn_blue.setEnabled(self.state > 2)
        self.btn_white.setEnabled(self.state > 2)
        self.btn_slash.setEnabled(self.state > 2)
        # self.btn_freeze.setEnabled(self.state > 2)
        # self.btn_blackout.setEnabled(self.state > 2)
        self.btn_freeze.setEnabled(False)
        self.btn_blackout.setEnabled(False)

    def _pattern_red(self):
        if self.led_screen:
            self.led_screen.set_pattern(mctrl300.MCTRL300.PATTERN_RED, self.selected_port)
            self.btn_red.setChecked(True)
            self.log.debug(f'Output {self.selected_port} set to RED')

    def _pattern_blue(self):
        if self.led_screen:
            self.led_screen.set_pattern(mctrl300.MCTRL300.PATTERN_BLUE, self.selected_port)
            self.btn_blue.setChecked(True)

    def _pattern_green(self):
        if self.led_screen:
            self.led_screen.set_pattern(mctrl300.MCTRL300.PATTERN_GREEN, self.selected_port)
            self.btn_green.setChecked(True)

    def _pattern_white(self):
        if self.led_screen:
            self.led_screen.set_pattern(mctrl300.MCTRL300.PATTERN_WHITE, self.selected_port)
            self.btn_white.setChecked(True)

    def _pattern_slash(self):
        if self.led_screen:
            self.led_screen.set_pattern(mctrl300.MCTRL300.PATTERN_SLASH, self.selected_port)
            self.btn_slash.setChecked(True)

    def _pattern_normal(self):
        if self.led_screen:
            self.led_screen.deactivate_pattern(self.selected_port)
            self.btn_normal.setChecked(True)

    def _pattern_black(self):
        if self.led_screen:
            self.led_screen.set_pattern(mctrl300.MCTRL300.PATTERN_RED, self.selected_port)
            self.btn_black.setChecked(True)

    def _pattern_freeze(self):
        if self.led_screen:
            self.led_screen.set_pattern(mctrl300.MCTRL300.PATTERN_RED, self.selected_port)
            self.btn_freeze.setChecked(True)


def start_gui():
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
