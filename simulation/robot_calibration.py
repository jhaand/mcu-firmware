#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fileinput
import argparse
import math
import os
import psutil
os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'
import pyqtgraph as pg
import pyqtgraph.exporters
from pyqtgraph import QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
import numpy as np
import re
from serial import *
import subprocess
import signal
import sys
from threading import Thread
from threading import Lock

BASE_PATH = "platforms/cogip2019-cortex-simulation/"
BIN_NAME = "cortex-simulation.elf"
BIN_PATH = BASE_PATH + "bin/cogip2019-cortex-native/" + BIN_NAME




class DataItemSameTime(pg.PlotDataItem):

    def __init__(self, *args, **kargs):
        pg.PlotDataItem.__init__(self, *args, **kargs)

        self.y_values =  np.array([])
        self.setData(y = self.y_values) # yvalues only

    def addPoint(self, value):
        self.y_values = np.append(self.y_values, [value])
        self.setData(y = self.y_values)


class CurveOverTime(pg.PlotItem):
    """
    This object manages two set of points over time series.

    One set represents commands ("Cmd") curve, the second set represents
    the measurements ("Meas").
    """

    def __init__(self, title=None, *args, **kargs):
        pg.PlotItem.__init__(self, title=title, *args, **kargs)

        self.setLabel('bottom', 'Time[20 ms steps]')
        self.setLabel('left', 'm.s-1 ?')
        self.showGrid(x = True, y = True)

        self._addDataItems()

        self.legend = self.addLegend()
        self.legend.addItem(self.dataItemCmd, 'Cmd')
        self.legend.addItem(self.dataItemMeas, 'Meas')


    def _addDataItems(self):
        # Green pen with few tranparency
        self.dataItemCmd = DataItemSameTime(pen = pg.mkPen(80, 255, 80, 200))
        self.addItem(self.dataItemCmd)
        # Red pen with few tranparency
        self.dataItemMeas = DataItemSameTime(pen = pg.mkPen(255, 80, 80, 200))
        self.addItem(self.dataItemMeas)


    def appendCommand(self, value):
        self.dataItemCmd.addPoint(value)


    def appendMeas(self, value):
        self.dataItemMeas.addPoint(value)


    def getData(self):
        t1, cmd = self.dataItemCmd.getData()
        _, meas = self.dataItemMeas.getData()

        return [t1, cmd, meas]


    def setLegends(self, cmd, meas):
        # FIXME: Following works once and this is ugly.
        self.legend.removeItem('Cmd')
        self.legend.removeItem('Meas')
        self.legend.addItem(self.dataItemCmd, cmd)
        self.legend.addItem(self.dataItemMeas, meas)


    def clear(self):
        pg.PlotItem.clear(self)
        self._addDataItems()


class MapView(pg.PlotItem):
    """
    This object allow a representation of the robot map.

    It draws a fixed rectangle for the game area, according to firmware's frame
    coordinates.
    """

    TABLE_WIDTH_MM = 3000
    TABLE_HEIGHT_MM = 2000

    ROBOT_WIDTH_MM = 354

    def __init__(self, title=None, *args, **kargs):
        pg.PlotItem.__init__(self, title=title, *args, **kargs)

        # Set fixed ratio and configure view area
        self.setXRange(-self.TABLE_WIDTH_MM / 2, self.TABLE_WIDTH_MM / 2)
        self.setYRange(0, self.TABLE_HEIGHT_MM)
        self.setAspectLocked(True, ratio = 1.0)

        # Draw a rectangle to represent the game area
        self.table = pg.QtGui.QGraphicsRectItem( -self.TABLE_WIDTH_MM / 2, 0, self.TABLE_WIDTH_MM, self.TABLE_HEIGHT_MM)
        self.table.setPen(pg.mkPen((255, 128, 128, 100))) # Red pen with lots of tranparency
        self.table.setBrush(pg.mkBrush((50, 50, 200, 50))) # Blue background with lots of tranparency
        self.addItem(self.table)

        # Draw a triangle to represent the robot
        self.robot_current = pg.QtGui.QGraphicsPolygonItem()
        self.robot_current.setPen(pg.mkPen((128, 255, 128, 100)))

        self.setRobotPoseCurrent(0., 0., 0.)
        self.addItem(self.robot_current)

        self.showGrid(x = True, y = True)

    def _calc_robot_polygon(self, x, y, theta):
        """
        Prepare a QPolygonF representing the robot by a triangle, given a pose
        @return: a QPolygonF object.
        """
        # angle coordinates translation
        theta = math.radians(theta)

        # 3 points around the gravity center (x, y)
        # all oriented following the theta angle
        x1 = (self.ROBOT_WIDTH_MM // 2) * math.cos(theta)
        y1 = (self.ROBOT_WIDTH_MM // 2) * math.sin(theta)
        x2 = (self.ROBOT_WIDTH_MM // 2) * math.cos(theta + 2.5 * (math.pi / 3.))
        y2 = (self.ROBOT_WIDTH_MM // 2) * math.sin(theta + 2.5 * (math.pi / 3.))
        x3 = (self.ROBOT_WIDTH_MM // 2) * math.cos(theta + 3.5 * (math.pi / 3.))
        y3 = (self.ROBOT_WIDTH_MM // 2) * math.sin(theta + 3.5 * (math.pi / 3.))
        points = [(x + x1, y + y1), (x + x2, y + y2), (x + x3, y + y3)]

        qpoints = [QtCore.QPointF(x, y) for (x, y) in points]
        qpoly = QtGui.QPolygonF(qpoints)

        return qpoly

    def setRobotPoseCurrent(self, x, y, theta):
        """
        Define current pose of the robot, and update view drawing accordingly.
        """
        qpoly = self._calc_robot_polygon(x, y, theta)
        self.robot_current.setPolygon(qpoly)

# Create plots window

class GraphWindow(QMainWindow):
    """
    Main QT Window classes.

    Embed a pg.GraphicsLayoutWidget() in its central widget to display graphs.
    """
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        # Create pyqtgraph layout widget
        self.graphicLayoutWidget = pg.GraphicsLayoutWidget()
        self.setCentralWidget(self.graphicLayoutWidget)

        #
        # Icon name:
        #  https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
        # Src:
        #  https://doc.qt.io/qtforpython/PySide2/QtGui/QIcon.html#PySide2.QtGui.PySide2.QtGui.QIcon.fromTheme
        exitIcon = QIcon.fromTheme("application-exit")
        exitAct = QAction(exitIcon, 'Exit application', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.triggered.connect(qApp.quit)

        saveAsIcon = QIcon.fromTheme("document-save-as")
        saveAsAct = QAction(saveAsIcon, 'Save Left & Right wheel to CSV', self)
        saveAsAct.setShortcut('Ctrl+S')
        saveAsAct.triggered.connect(self.saveAsActClicked)

        clearAllIcon = QIcon.fromTheme("edit-clear")
        clearAllAct = QAction(clearAllIcon, 'Clear graphs', self)
        clearAllAct.setShortcut('Ctrl+K')
        clearAllAct.triggered.connect(self.clearAllActClicked)

        # Register all actions in window toolbar
        self.toolbar = self.addToolBar("Main")
        self.toolbar.setStyleSheet("background-color:black; color:grey");
        self.toolbar.addAction(exitAct)
        self.toolbar.addAction(saveAsAct)
        self.toolbar.addAction(clearAllAct)

        # Add all graphes
        self.lin_speed = CurveOverTime('Linear speed')
        self.lin_speed.setLegends('speed_order', 'speed_current')
        self.addItem(self.lin_speed, row=0, col=1)

        self.ang_speed = CurveOverTime('Angular speed')
        self.ang_speed.setLegends('speed_order', 'speed_current')
        self.addItem(self.ang_speed, row=1, col=1)

        self.lw = CurveOverTime('Left wheel')
        self.lw.setLegends('motor_cmd', 'qdec_speed')
        self.addItem(self.lw, row=0, col=2)

        self.rw = CurveOverTime('Right wheel')
        self.rw.setLegends('motor_cmd', 'qdec_speed')
        self.addItem(self.rw, row=1, col=2)

        self.mb = MapView('Map')
        self.addItem(self.mb, row=0, col=3, rowspan=2)

        # Timer used to refresh plots
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self._update_plot)
        self.timer.start(10) # ms


    def saveAsActClicked(self):
        print("saveAsActClicked")

        import csv

        t, lw_cmd, lw_mes = self.lw.getData()
        _, rw_cmd, rw_mes = self.rw.getData()

        # Outputs saved in 'csv_outputs' subdir relative to this script location
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        OUT_DIR = os.path.join(SCRIPT_DIR, "csv_outputs")

        if not os.path.exists(OUT_DIR):
            print(f"Create {OUT_DIR}")
            os.mkdir(OUT_DIR)

        # Get a timestamp to ensure uniq filename
        from datetime import datetime
        fname = 'data_' + str(datetime.now()).replace(' ', '_') + '.csv'

        # Write CSV file
        with open(os.path.join(OUT_DIR, fname), 'w', newline='') as csvfile:
            w = csv.writer(csvfile, delimiter=',',
                           quotechar='|', quoting=csv.QUOTE_MINIMAL)
            # Header on first row
            w.writerow(['time', 'lw_cmd', 'lw_mes', 'rw_cmd', 'rw_mes'])
            # Left & Right wheel data on following rows
            for i in range(0, len(t)):
                w.writerow([t[i], lw_cmd[i], lw_mes[i], rw_cmd[i], rw_mes[i]])

            print(f"Data saved in '{fname}'")

    def clearAllActClicked(self):
        print("clearAllActClicked")

        self.lin_speed.clear()
        self.ang_speed.clear()
        self.lw.clear()
        self.rw.clear()
        #TODO: self.mb.clear()

    def _update_plot(self):

        while True:
            t = RobotTelemetry.pop()
            if not t:
                break

            (left, right) = t.motor_cmd
            self.lw.appendCommand(left)
            self.rw.appendCommand(right)

            (left, right) = t.qdec_speed
            self.lw.appendMeas(left)
            self.rw.appendMeas(right)

            (linear, angular) = t.speed_order
            self.lin_speed.appendCommand(linear)
            self.ang_speed.appendCommand(angular)

            (linear, angular) = t.speed_current
            self.lin_speed.appendMeas(linear)
            self.ang_speed.appendMeas(angular)

            (x, y, theta) = t.pose_current
            self.mb.setRobotPoseCurrent(x, y, theta)


    def addItem(self, widget, row=None, col=None, rowspan=1, colspan=1):
        """
        This methods makes this QtGui subclass compatible with pg.GraphicsWindow() API.
        """
        self.graphicLayoutWidget.addItem(widget, row, col, rowspan, colspan)





class RobotTelemetry():
    """
    Aggregates multi-lines measurements

    Class methods manages a thread safe FIFO of instances
    """

    telemetry_points = []
    lock = Lock()

    @classmethod
    def push(cls, point):
        """
        Store a telemetry record in FIFO.
        Intended to be called by Parser threads
        """
        cls.lock.acquire()
        cls.telemetry_points.append(point)
        cls.lock.release()

    @classmethod
    def pop(cls):
        """
        Load a telemetry record from FIFO.
        Intended to be called by Qt event loop, from refresh timer callback.
        """
        point = None

        cls.lock.acquire()
        if len(cls.telemetry_points):
            point = cls.telemetry_points.pop(0)
        cls.lock.release()

        return point

    def __init__(self, current_cycle):
        self.current_cycle = current_cycle # might not be needed...
        self.speed_order = (0., 0.)
        self.speed_current = (0., 0.)
        self.qdec_speed = (0, 0)
        self.motor_cmd = (0, 0)

        self.pose_order = (0., 0., 0.)
        self.pose_current = (0., 0., 0.)

    def set_speed_order(self, speed_lin, speed_order_ang):
        self.speed_order = (speed_lin, speed_order_ang)

    def set_speed_current(self, speed_lin, speed_ang):
        self.speed_current = (speed_lin, speed_ang)

    def set_qdec_speed(self, qdec_speed_left, qdec_speed_right):
        self.qdec_speed = (qdec_speed_left, qdec_speed_right)

    def set_motor_cmd(self, motor_cmd_left, motor_cmd_right):
        self.motor_cmd = (motor_cmd_left, motor_cmd_right)

    def set_pose_order(self, x, y, theta):
        self.pose_order = (x, y, theta)

    def set_pose_current(self, x, y, theta):
        self.pose_current = (x, y, theta)

    def dump_all(self):
        print("speed_order: " + str(self.speed_order)
              + " qdec_speed: " + str(self.qdec_speed)
              + " motor_cmd" + str(self.motor_cmd))


class Parser():
    END_PATTERN = '>>>>'
    RESET_PATTERN = '<<<< RESET >>>>'
    STOP_PATTERN = '<<<< STOP >>>>'
    ROBOT_OBJECT_PATTERN = '@robot@'
    QDEC_SPEED_PATTERN = '@qdec_speed@'
    MOTOR_CMD_PATTERN = '@motor_set@'
    POSE_ORDER_PATTERN = '@pose_order@'
    POSE_CURRENT_PATTERN = '@pose_current@'
    SPEED_ORDER_PATTERN = '@speed_order@'
    SPEED_CURRENT_PATTERN = '@speed_current@'

    def __init__(self):
        self.current_cycle = -1
        self.robot_telemetry = None

    def _decode(self, line):

        # Remove trailing spaces or line return
        line = line.rstrip().rstrip(',')
        if re.match(r'@.*@,.*', line) is not None:
            # Split parameters
            params = line.split(',')

            # Extract objects parameters
            obj_type = params[0]
            obj_id = params[1]
            obj_current_cycle = int(params[2])
            obj_param = params[3]

            # New multi-line measurement incoming
            if (obj_current_cycle != self.current_cycle):

                # If already some telemetry stored, send them to GUI
                if self.robot_telemetry:
                    self.robot_telemetry.dump_all()
                    RobotTelemetry.push(self.robot_telemetry)

                # New 'current_cycle' -> Start new telemetry record
                self.current_cycle = obj_current_cycle
                self.robot_telemetry = RobotTelemetry(self.current_cycle)

            assert (self.robot_telemetry is not None)

            if obj_type == self.ROBOT_OBJECT_PATTERN:
                if obj_param == self.QDEC_SPEED_PATTERN:
                    self.robot_telemetry.set_qdec_speed(int(params[4]), int(params[5]))
                elif obj_param == self.SPEED_ORDER_PATTERN:
                    self.robot_telemetry.set_speed_order(float(params[4]), float(params[5]))
                elif obj_param == self.SPEED_CURRENT_PATTERN:
                    self.robot_telemetry.set_speed_current(float(params[4]), float(params[5]))
                elif obj_param == self.POSE_ORDER_PATTERN:
                    self.robot_telemetry.set_pose_order(float(params[4]), float(params[5]), float(params[6]))
                elif obj_param == self.POSE_CURRENT_PATTERN:
                    self.robot_telemetry.set_pose_current(float(params[4]), float(params[5]), float(params[6]))
                elif obj_param == self.MOTOR_CMD_PATTERN:
                    self.robot_telemetry.set_motor_cmd(int(params[4]), int(params[5]))

    def parse(self, flow):
        while True:
            line = flow.readline().decode('utf-8')
            output = sys.stdout
            print('\x1b[0;35;40m' + line + '\033[0m', file=output, end='')
            output.flush()
            self._decode(line)
        print('Parsing finished')


class NativeParser(Parser):

    def parse(self, p):
        """
        Read subprocess 'p' outcoming character from stdout and parse them in
        upper class.
        """
        super(NativeParser, self).parse(p.stdout)

    def send(self, p):
        """
        Read this python script incoming character from stdin and when a line is
        completed, propagates the whole string to subprocess 'p' stdin stream.
        """
        for line in fileinput.input():
            p.stdin.write(line.encode('utf-8'))
            p.stdin.flush()

class SerialParser(Parser):
    def __init__(self, serial_port):
        super().__init__()
        self.ser = Serial(port=serial_port, baudrate=115200, timeout=1, writeTimeout=1)

    def parse(self):
        """
        Read serial port incoming character (i.e. MCU firwmare stdout) and parse
        them it in upper class
        """
        if self.ser.isOpen():
            while True:
                super(SerialParser, self).parse(self.ser)

    def send(self):
        """
        Read this python script incoming character from stdin and when a line is
        completed, propagates the whole string to serial port.
        """
        for line in fileinput.input():
            if self.ser.isOpen():
                self.ser.write(bytes(line, 'utf8'))

if __name__ == "__main__":

    # Parse command line arguments
    arg_parser = argparse.ArgumentParser(description='Launch PID measurement tool. Works on native board or real target through serial link.')
    arg_parser.add_argument(
        "-D", "--device",
        dest="uart_dev", default=None,
        help="Specify UART device, run on native board otherwise"
    )
    args = arg_parser.parse_args()

    # Kill all remaining bin instance
    process = filter(lambda p: BIN_NAME in p.name(), psutil.process_iter())
    for i in process:
        print(f"Kill remaining instance {i.pid}")
        os.kill(i.pid, signal.SIGKILL)
        try:
            os.waitpid(i.pid, 0)
        except OSError:
            pass

    # Start Qt app
    app = pg.QtGui.QApplication([])

    win = GraphWindow()
    win.setWindowTitle("PID loop monitor")
    win.resize(1600, 900)
    win.show()

    if args.uart_dev:
        p = None
        parser = SerialParser(args.uart_dev)
        thr_from_mcu = Thread(target=parser.parse)
        thr_to_mcu = Thread(target=parser.send)
    else:
        p = subprocess.Popen(BIN_PATH, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        parser = NativeParser()
        thr_from_mcu = Thread(target=parser.parse, args=(p,))
        thr_to_mcu = Thread(target=parser.send, args=(p,))

    thr_from_mcu.daemon = True
    thr_from_mcu.start()

    thr_to_mcu.daemon = True
    thr_to_mcu.start()


    if sys.flags.interactive != 1 or not hasattr(pg.QtCore, 'PYQT_VERSION'):
        app.exec_()

    print("Qt GUI closed... stop other processes.")
    if p:
        p.kill()
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
