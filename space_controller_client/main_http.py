# -*- coding: UTF-8 -*-
"""
Object-based Sound Reproduction Demo

@author: Zhu Jun

2021/9/15

"""
import threading as td 
import scipy.io as io 
import  json, math, copy, os, datetime, time
import numpy as np
from sys import argv, exit
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, QThread, pyqtSignal, Qt, QObject
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QAction, QMessageBox, \
    QWidget, QLabel, QStackedWidget, QGridLayout, QComboBox, QListWidget, QPushButton, \
    QGroupBox, QRadioButton, QVBoxLayout, QHBoxLayout, QSlider, QStyle, QStyleOptionSlider, QSplashScreen, \
    QDial, QDesktopWidget, QGraphicsScene, QDockWidget, QLineEdit, QScrollArea, QFrame

from PyQt5.QtGui import QIcon, QPixmap, QFont, QPalette, QPainter, QPen, QVector3D, QWindow
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QMutex,QObject, QPoint, QCoreApplication, QTimer
from PyQt5.Qt import QSize, QQuaternion
from PyQt5.QtDataVisualization import Q3DScatter, QScatter3DSeries, QScatterDataItem, Q3DCamera, \
    QValue3DAxis, Q3DTheme, QAbstract3DGraph, QCustom3DItem
import win32gui, win32con

from http_send_mes import http_client

PI = 3.14159


def cart2sph( x, y, z):
    azimuth = np.arctan2(y, x)
    elevation = np.arctan2(z, np.sqrt(x ** 2 + y ** 2))
    r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
    return  azimuth, elevation, r

def sph2cart( azimuth, elevation, r):
    x = r * np.cos(elevation) * np.cos(azimuth)
    y = r * np.cos(elevation) * np.sin(azimuth)
    z = r * np.sin(elevation)
    return x, y, z



class main_ui(QMainWindow):
    def __init__(self):
        super(main_ui, self).__init__()

        # 元数据参数
        self.max_port_num = 32
        self.max_objects_num = 32

        # 初始化客户端
        self.http_client = http_client()

        # 移动到屏幕左上角
        self.move(0, 0)

        # 屏幕尺寸-->窗口尺寸
        self.screen = QDesktopWidget()
        self.screen_size = self.screen.availableGeometry()
        self.widget_size = []
        self.widget_size.append(self.screen_size.width())
        self.widget_size.append(self.screen_size.height())

        # 创建状态栏
        self.status_bar = self.statusBar()
        
        # 初始化各面板
        self.object_pannel_init()      # 元数据控制器
        self.toolbar_init()            # 工具栏
        self.soundscape_pannel_ini()   # 3D显示
        self.loudspeaker_setting_pannel()   # 扬声器设置

        # 主界面设置
        self.main_widget_layout = QHBoxLayout()
        self.main_widget_layout.addWidget(self.objects_3Dpannel_winodow)
        self.main_widget_layout.addWidget(self.object_pannel)
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_widget_layout)

        # 切换窗
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.main_widget)
        self.stacked_widget.addWidget(self.loudspeaker_setting_widget)
        self.stacked_widget.setCurrentIndex(0)
        self.setCentralWidget(self.stacked_widget)

        # # 传感器
        # self.object_pos_sensor = sensor(self)
        # self.object_pos_sensor.start()
        # self.object_pos_sensor.calibration_ahead()

        # # Qtimer 
        # self.timer = QTimer(self)
        # self.timer.timeout.connect(lambda: self.obj_pos_change(self.object_pos_sensor.pos_theta, self.object_pos_sensor.pos_phi))
        # self.timer.start(20)
    
    def obj_pos_change(self, theta, phi):
        self.object_pannel.objects_controller[0].azi_dial.setValue(int(theta))
        self.object_pannel.objects_controller[0].ele_dial.setValue(int(phi))


########################## Toolbar 设置#######################################
    def toolbar_init(self):
        self.back_to_main_pannel = QAction('主界面')
        self.loudspeaker_layout = QAction('扬声器布局')
        self.save_current_metadata = QAction('保存当前元数据')
        self.load_metadata = QAction('加载元数据')

        self.toolbar = self.addToolBar('toolbar')
        self.toolbar.addAction(self.back_to_main_pannel)
        self.toolbar.addAction(self.loudspeaker_layout)
        self.toolbar.addAction(self.save_current_metadata)
        self.toolbar.addAction(self.load_metadata)

        self.back_to_main_pannel.triggered.connect(self.show_main_pannel)
        self.loudspeaker_layout.triggered.connect(self.show_loudspeaker_pannel)
        self.save_current_metadata.triggered.connect(self.save_current_metadata_callback)
        self.load_metadata.triggered.connect(self.load_metadata_callback)

################## toolbar callback ############################

    def show_main_pannel(self):
        self.stacked_widget.setCurrentIndex(0)

    def show_loudspeaker_pannel(self):
        self.stacked_widget.setCurrentIndex(1)

    def save_current_metadata_callback(self):
        # 保存当前元数据metadata
        metadata = [{} for i in range(self.max_objects_num)]
        for i in range(self.max_objects_num):
            # on_off
            if not self.object_pannel.objects_controller[i].on_button.isChecked():
                metadata[i]['on_off'] = False
            else:
                metadata[i]['on_off'] = True
            # azi, ele, r, width, gain
            metadata[i]['azi'] = self.object_pannel.objects_controller[i].azi_dial.value()
            metadata[i]['ele'] = self.object_pannel.objects_controller[i].ele_dial.value()
            metadata[i]['r'] = self.object_pannel.objects_controller[i].dis_dial.value()
            metadata[i]['width'] = self.object_pannel.objects_controller[i].width_dial.value()
            metadata[i]['gain'] = self.object_pannel.objects_controller[i].gain_dial.value()
            metadata[i]['port'] = self.object_pannel.objects_controller[i].port.currentIndex()

        np.save('./config/metadata.npy', metadata)

    def load_metadata_callback(self):
        # 加载元数据
        self.stop_play()
        load_data = np.load('./config/metadata.npy', allow_pickle=True)
        metadata = load_data.tolist()
        for i in range(self.max_objects_num):
            # on_off
            if metadata[i]['on_off'] == False:
                self.object_pannel.objects_controller[i].on_button.setChecked(False)
            else:
                self.object_pannel.objects_controller[i].on_button.setChecked(True)
            # azi, ele, r, width, gain
            self.object_pannel.objects_controller[i].azi_dial.setValue(metadata[i]['azi'])
            self.object_pannel.objects_controller[i].ele_dial.setValue(metadata[i]['ele'])
            self.object_pannel.objects_controller[i].dis_dial.setValue(metadata[i]['r'])
            self.object_pannel.objects_controller[i].width_dial.setValue(metadata[i]['width'])
            self.object_pannel.objects_controller[i].gain_dial.setValue(metadata[i]['gain'])
            self.object_pannel.objects_controller[i].port.setCurrentIndex(metadata[i]['port'])

    def object_button_callback(self, objects_item_idx):
        # object_button_callback: 当点击按钮时触发
        self.object_pannel.objects_setting_widget.setCurrentIndex(objects_item_idx)

    def send_object_metadata(self, object_id, dial_id):
        # send_object_metadata: 发送改变的元数据
        msg = {}
        msg['object_id'] = object_id + 1
        if dial_id == 1 or dial_id == 2 or dial_id == 3: 
            # azi, ele or r 
            azi = self.object_pannel.objects_controller[object_id].azi_dial.value()/180*np.pi
            ele = self.object_pannel.objects_controller[object_id].ele_dial.value()/180*np.pi
            dis = self.object_pannel.objects_controller[object_id].dis_dial.value()
            x, y, z = sph2cart(-azi, ele, dis)
            msg['position_cart'] = [round(x,2), round(y,2), round(z,2)]

        elif dial_id == 4:
            # width 
            val = self.object_pannel.objects_controller[object_id].width_dial.value() 
            if val == 0 and self.object_pannel.objects_controller[object_id].on_button.isChecked():
                msg['object_type'] = 'dbap'
            elif val == 0 and not self.object_pannel.objects_controller[object_id].on_button.isChecked():
                msg['object_type'] = 'off'
            elif self.object_pannel.objects_controller[object_id].on_button.isChecked():
                msg['broaden_level'] = val
                msg['object_type'] = 'broaden'
            else:
                msg['broaden_level'] = val

        elif dial_id == 5:
            # gain
            msg['object_gain'] = round(10**(self.object_pannel.objects_controller[object_id].gain_dial.value()/20),2)

        elif dial_id == 6:
            # on/off 
            val = self.object_pannel.objects_controller[object_id].width_dial.value() 
            if not self.object_pannel.objects_controller[object_id].on_button.isChecked():
                msg['object_type'] = 'off'
            elif val == 0:
                msg['object_type'] = 'dbap'
            else:
                msg['object_type'] = 'broaden' 
                
        elif dial_id == 7:
            # port 
            val = self.object_pannel.objects_controller[object_id].port.currentIndex()
            msg['source_port'] = val

        elif dial_id == 8: 
            # 去相关
            val = self.object_pannel.decorrelation.isChecked()
            if val:
                msg['decorrelate'] = True
            else:
                msg['decorrelate'] = False




    def change_object_param_label(self, value, object_id, dial_id):
        # change_object_param_label: 当滑动条改变时，改变元数据label中的值
        if dial_id == 1:
            self.object_pannel.objects_controller[object_id].azi_value_label.setText( str(value) + '°')
        elif dial_id == 2:
            self.object_pannel.objects_controller[object_id].ele_value_label.setText( str(value) + '°')
        elif dial_id == 3:
            self.object_pannel.objects_controller[object_id].dis_value_label.setText( str(value) + 'm')
        elif dial_id == 4:
            self.object_pannel.objects_controller[object_id].width_value_label.setText( str(value))
        elif dial_id == 5:
            self.object_pannel.objects_controller[object_id].gain_value_label.setText( str(value) + 'dB')
    

    def change_3d(self, object_id):
        # 检查是开启还是关闭
        if self.object_pannel.objects_controller[object_id].on_button.isChecked():
        # 球坐标转直角坐标
            azi = self.object_pannel.objects_controller[object_id].azi_dial.value()/180*np.pi
            ele = self.object_pannel.objects_controller[object_id].ele_dial.value()/180*np.pi
            dis = self.object_pannel.objects_controller[object_id].dis_dial.value()
            dis = (dis + 30)*0.1
            x, y, z = sph2cart(-azi, ele, dis)

            # 改3D UI
            self.series_sum[object_id].dataProxy().setItem(0, QScatterDataItem(QVector3D(-x, z,-y )))
            self.series_sum[object_id].setItemSize(0.1)
            width_val = self.object_pannel.objects_controller[object_id].width_dial.value()
            if  width_val != 0:
                self.series_sum[object_id].setItemSize(0.1+0.012*(width_val))

        elif not self.object_pannel.objects_controller[object_id].on_button.isChecked():
            self.series_sum[object_id].dataProxy().setItem(0, QScatterDataItem(QVector3D(0, 0, 0)))
            self.series_sum[object_id].setItemSize(0.00000001)

    def selected_item_changed(self):
        # selected_item_changed: 3dtree中选中的item改变时触发
        if not not self.objects_3Dpannel.selectedSeries():
            now_object_index = int((self.objects_3Dpannel.selectedSeries()).name)
            self.object_pannel.objects_setting_widget.setCurrentIndex(now_object_index)

    def start_play(self):
        send_msg = []
        for i in range(self.max_objects_num+1):
            send_msg.append({})

        # # 整体发送元数据，保证服务器端与客户端的元数据一致
        # decorrelation
        send_msg[self.max_objects_num]['object_id'] = 0
        if self.object_pannel.decorrelation.isChecked():
            send_msg[self.max_objects_num]['decorrelate'] = True
        else:
            send_msg[self.max_objects_num]['decorrelate'] = False

        for i in range(self.max_objects_num):
            # object_id
            send_msg[i]['object_id'] = i+1
            # object_type
            if not self.object_pannel.objects_controller[i].on_button.isChecked():
                send_msg[i]['object_type'] = 'off'
            elif self.object_pannel.objects_controller[i].width_dial.value() == 0:
                send_msg[i]['object_type'] = 'dbap'
            else:
                send_msg[i]['object_type'] = 'broaden'

            # position_cart
            azi = self.object_pannel.objects_controller[i].azi_dial.value()/180*np.pi
            ele = self.object_pannel.objects_controller[i].ele_dial.value()/180*np.pi
            dis = self.object_pannel.objects_controller[i].dis_dial.value()
            x, y, z = sph2cart(-azi, ele, dis)
            send_msg[i]['position_cart'] = [round(x,2), round(y,2), round(z,2)]
            # broaden_level
            send_msg[i]['broaden_level'] = self.object_pannel.objects_controller[i].width_dial.value()
            # gain
            send_msg[i]['object_gain'] = round(10**(self.object_pannel.objects_controller[i].gain_dial.value()/20),2)
            # port 
            send_msg[i]['source_port'] = self.object_pannel.objects_controller[i].port.currentIndex()

        status = self.http_client.send_play_control()

        if not status:
            # 将状态栏设置为“与服务器连接出错”
            self.status_bar.showMessage('与服务器连接出错: send play control')
            self.status_bar.setStyleSheet('color:red')
        else:
            self.status_bar.showMessage('与服务器链接成功')
            self.status_bar.setStyleSheet('color:green')

    def stop_play(self):
        # 停止服务器播放
        status = self.http_client.send_stop_control()
        if not status:
            # 将状态栏设置为“与服务器连接出错”
            self.status_bar.showMessage('与服务器连接出错: send stop control')
            self.status_bar.setStyleSheet('color:red')
        else:
            self.status_bar.showMessage('与服务器链接成功')
            self.status_bar.setStyleSheet('color:green')

    def load_loudspeaker_setting(self):
        # 读取扬声器位置文件
        f = open('./config/deafult_loudspeaker_setting.json', 'r')
        deafultset = json.loads(f.read())
        ls_position = deafultset['position_sph']
        ls_rotation = deafultset['rotation']

        # 画扬声器位置
        # 加入听音位头模型
        head_model = QCustom3DItem()
        head_model.setMeshFile('./png/head2.obj')
        head_model.setPosition(QVector3D(0, -3, 0))
        head_model.setScaling(QVector3D(1.5,1.5,1.5))
        rotation = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), -90)
        head_model.setRotation(rotation)
        self.loudspeaker_3Dlayout.addCustomItem(head_model)

        # 发包
        self.http_client.send_loudspeaker_setup(ls_position)
        ls_model = [i for i in range(len(ls_position))]
        for i in range(len(ls_position)) :
            ls_model[i] = QCustom3DItem()
            ls_model[i].setMeshFile('./png/loudspeaker.obj')
            x, y, z = sph2cart(ls_position[i][0]/180*PI, ls_position[i][1]/180*PI, ls_position[i][2])
            ls_model[i].setPosition(QVector3D(-x, z,-y))
            ls_model[i].setScaling(QVector3D(0.05, 0.05, 0.05))
            # 1 2 3 分别为 z， x， y/
            # y 正方向和球坐标一致/ z 正方形为向下旋转
            rota_y = ls_rotation[i][0] - 90
            rota_z = -ls_rotation[i][1]
            rotation = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), rota_y) * \
                       QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), rota_z)
            ls_model[i].setRotation(rotation)
            self.loudspeaker_3Dlayout.addCustomItem(ls_model[i])

    def clear_loudspeaker_setting(self):
        self.loudspeaker_3Dlayout.removeCustomItems()


####################### 扬声器布局设置区域 ##############################################
    def loudspeaker_setting_pannel(self):
        # 三维扬声器布局显示
        self.loudspeaker_3Dlayout = Q3DScatter()
        self.loudspeaker_3Dlayout.setFlags(self.objects_3Dpannel.flags() ^ Qt.FramelessWindowHint)
        self.loudspeaker_3Dlayout.setTitle('loudspeaker')
        self.loudspeaker_3Dlayout.axisX().setRange(-15, 15)
        self.loudspeaker_3Dlayout.axisY().setRange(-15, 15)
        self.loudspeaker_3Dlayout.axisZ().setRange(-15, 15)
        # 关阴影
        self.loudspeaker_3Dlayout.setShadowQuality(QAbstract3DGraph.ShadowQuality())

        # remove black broaden
        self.loudspeaker_3Dlayout.showFullScreen()
        hwnd = win32gui.FindWindowEx(0, 0, None,"loudspeaker")
        window = QWindow.fromWinId(hwnd)
        self.loudspeaker_3Dlayout_winodow = QWidget.createWindowContainer(window)
        # 设置最大化长宽
        self.loudspeaker_3Dlayout_winodow.setMaximumSize(int(self.widget_size[0]*0.7), int(self.widget_size[1]))

        # 调整相机位置，更好的角度来观察散点
        camera = self.objects_3Dpannel.scene().activeCamera()
        camera.setCameraPreset(Q3DCamera.CameraPresetFront)

        # 扬声器设置右面板
        pannel = QWidget(self)
        pannel.setMaximumSize(int(self.widget_size[0] * 0.29), int(self.widget_size[1]))
        load_button = QPushButton('载入配置')
        load_button.setMaximumHeight(50)
        load_button.pressed.connect(self.load_loudspeaker_setting)
        clear_button = QPushButton('清除')
        clear_button.setMaximumHeight(50)
        clear_button.pressed.connect(self.clear_loudspeaker_setting)

        layout_right_pannel = QVBoxLayout()
        layout_button = QHBoxLayout()
        layout_button.addWidget(load_button)
        layout_button.addWidget(clear_button)
        button_widget = QWidget()
        button_widget.setLayout(layout_button)
        layout_right_pannel.addWidget(button_widget)
        pannel.setLayout(layout_right_pannel)

        # 总
        layout_left_right = QHBoxLayout()
        layout_left_right.addWidget(self.loudspeaker_3Dlayout_winodow)
        layout_left_right.addWidget(pannel)
        self.loudspeaker_setting_widget = QWidget()
        self.loudspeaker_setting_widget.setLayout(layout_left_right)

####################### objects 设置区域 ##############################################
    def object_pannel_init(self):
        # self.object_pannel  整个右边的面板
        self.object_pannel = QWidget()
        # 初始化个部件
        self.objects_general_setting_pannel()
        self.objects_setting_pannel()
        self.play_stop_button_init()
        # 组合
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.object_pannel.general_setting_widget)
        main_layout.addWidget(self.object_pannel.objects_setting_widget)
        main_layout.addWidget(self.button_widget)
        self.object_pannel.setLayout(main_layout)
        self.object_pannel.setMaximumSize(int(self.widget_size[0]*0.29), int(self.widget_size[1]))

    def objects_general_setting_pannel(self):
        # objects_pannel: 选择objects 与 总体objects属性设置
        self.object_pannel.general_setting_widget = QWidget()

        # list widget
        self.object_pannel.objects_list_widget = QListWidget()
        self.object_pannel.objects_list_widget.setMaximumHeight(int(self.widget_size[1]*0.2))
        self.object_pannel.objects_list_widget.setMaximumWidth(int(self.widget_size[0]*0.29/3))
        objects_list = ['Object'+str(i+1) for i in range(self.max_objects_num)]
        self.object_pannel.objects_list_widget.addItems(objects_list)
        self.object_pannel.objects_list_widget.setCurrentRow(0)
        self.object_pannel.objects_list_widget.itemClicked.connect(lambda: self.object_button_callback(\
                                self.object_pannel.objects_list_widget.currentRow()))
        
        # label 
        choose_obj_label = QLabel('Objects')
        # temp_label = QLabel('Objects')

        # 去相关开关
        decor_label = QLabel('去相关: ')
        self.object_pannel.decorrelation = QRadioButton('on')
        self.object_pannel.decorrelation.setChecked(False)
        self.object_pannel.decorrelation.toggled.connect(lambda: self.send_object_metadata(-1, 8))

        layout = QGridLayout()
        layout.addWidget(choose_obj_label, 0, 0, alignment=Qt.AlignCenter)
        # layout.addWidget(temp_label, 1, 0, alignment=Qt.AlignCenter)
        layout.addWidget(self.object_pannel.objects_list_widget, 0, 1, 3, 1)
        layout.addWidget(decor_label, 1, 3, 1, 1,alignment=Qt.AlignRight)
        layout.addWidget(self.object_pannel.decorrelation, 1, 4, 1, 1)

        self.object_pannel.general_setting_widget.setLayout(layout)


    # def object_scroll_area(self):
    #     # 滚动object选择区域
    #     self.object_pannel.objects = QScrollArea(self)
    #     layout = QHBoxLayout()
    #     widget = QWidget()
    #     objects_sum = [i for i in range(self.max_objects_num)]
    #     for i in range(self.max_objects_num):
    #         objects_sum[i] = QPushButton('object' + str(i+1))
    #         objects_sum[i].setFixedSize(int(self.widget_size[0]*0.3*0.2), 100)
    #         objects_sum[i].clicked.connect(lambda: self.object_button_callback(self.sender().text()))
    #         layout.addWidget(objects_sum[i])
    #     widget.setLayout(layout)
    #     self.object_pannel.objects.setWidget(widget)
    #     self.object_pannel.objects.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    #     self.object_pannel.objects.setMaximumHeight(int(self.widget_size[1]*0.1))
    #     self.object_pannel.objects.setMinimumHeight(int(150))
    #     self.object_pannel.objects.setMaximumWidth(int(self.widget_size[0]*0.29/2))
    
    def objects_setting_pannel(self):
        # objects_setting_pannel：目标源设置，12个目标元控制面板可切换
        # 可切换面板
        self.object_pannel.objects_setting_widget = QStackedWidget()
        self.object_pannel.objects_controller = [i for i in range(self.max_objects_num)]
        for i in range(self.max_objects_num):
            self.single_object_control_pannel(i)
            self.object_pannel.objects_setting_widget.addWidget(self.object_pannel.objects_controller[i])
        
    
    def single_object_control_pannel(self, object_id):
        # single_object_control_pannel: 单个目标元控制面板

        self.object_pannel.objects_controller[object_id] = QWidget()
        
        # 方位角旋钮
        self.object_pannel.objects_controller[object_id].azi_dial = QDial()
        self.object_pannel.objects_controller[object_id].azi_dial.setRange(-180, 180)
        self.object_pannel.objects_controller[object_id].azi_dial.setValue(0)
        self.object_pannel.objects_controller[object_id].azi_dial.setNotchesVisible(True)
        self.object_pannel.objects_controller[object_id].azi_dial.setFixedSize(int(self.widget_size[0]*0.1), int(self.widget_size[0]*0.04))
        self.object_pannel.objects_controller[object_id].azi_dial.valueChanged.connect(lambda: self.change_object_param_label(self.sender().value(),object_id, 1))
        self.object_pannel.objects_controller[object_id].azi_dial.valueChanged.connect(lambda: self.change_3d(object_id))
        self.object_pannel.objects_controller[object_id].azi_dial.valueChanged.connect(lambda: self.send_object_metadata(object_id, 1))


        # 仰角旋钮
        self.object_pannel.objects_controller[object_id].ele_dial = QDial()
        self.object_pannel.objects_controller[object_id].ele_dial.setRange(0, 90)
        self.object_pannel.objects_controller[object_id].ele_dial.setValue(0)
        self.object_pannel.objects_controller[object_id].ele_dial.setNotchesVisible(True)
        self.object_pannel.objects_controller[object_id].ele_dial.setFixedSize(int(self.widget_size[0]*0.1), int(self.widget_size[0]*0.04))
        self.object_pannel.objects_controller[object_id].ele_dial.valueChanged.connect(lambda: self.change_object_param_label(self.sender().value(),object_id, 2))
        self.object_pannel.objects_controller[object_id].ele_dial.valueChanged.connect(lambda: self.change_3d(object_id))
        self.object_pannel.objects_controller[object_id].ele_dial.valueChanged.connect(lambda: self.send_object_metadata(object_id, 2))

        # 距离旋钮
        self.object_pannel.objects_controller[object_id].dis_dial = QDial()
        self.object_pannel.objects_controller[object_id].dis_dial.setRange(0, 100)
        self.object_pannel.objects_controller[object_id].dis_dial.setValue(50)
        self.object_pannel.objects_controller[object_id].dis_dial.setNotchesVisible(True)
        self.object_pannel.objects_controller[object_id].dis_dial.setFixedSize(int(self.widget_size[0]*0.1), int(self.widget_size[0]*0.04))
        self.object_pannel.objects_controller[object_id].dis_dial.valueChanged.connect(lambda: self.change_object_param_label(self.sender().value(),object_id, 3))
        self.object_pannel.objects_controller[object_id].dis_dial.valueChanged.connect(lambda: self.change_3d(object_id))
        self.object_pannel.objects_controller[object_id].dis_dial.valueChanged.connect(lambda: self.send_object_metadata(object_id, 3))

        # 展宽旋钮
        self.object_pannel.objects_controller[object_id].width_dial = QDial()
        self.object_pannel.objects_controller[object_id].width_dial.setRange(0, 9)
        self.object_pannel.objects_controller[object_id].width_dial.setValue(0)
        self.object_pannel.objects_controller[object_id].width_dial.setNotchesVisible(True)
        self.object_pannel.objects_controller[object_id].width_dial.setFixedSize(int(self.widget_size[0]*0.1), int(self.widget_size[0]*0.04))
        self.object_pannel.objects_controller[object_id].width_dial.valueChanged.connect(lambda: self.change_object_param_label(self.sender().value(),object_id, 4))
        self.object_pannel.objects_controller[object_id].width_dial.valueChanged.connect(lambda: self.change_3d(object_id))
        self.object_pannel.objects_controller[object_id].width_dial.valueChanged.connect(lambda: self.send_object_metadata(object_id, 4))

        # 增益旋钮
        self.object_pannel.objects_controller[object_id].gain_dial = QDial()
        self.object_pannel.objects_controller[object_id].gain_dial.setRange(-30, 30)
        self.object_pannel.objects_controller[object_id].gain_dial.setValue(0)
        self.object_pannel.objects_controller[object_id].gain_dial.setNotchesVisible(True)
        self.object_pannel.objects_controller[object_id].gain_dial.setFixedSize(int(self.widget_size[0]*0.1), int(self.widget_size[0]*0.04))
        self.object_pannel.objects_controller[object_id].gain_dial.valueChanged.connect(lambda: self.change_object_param_label(self.sender().value(),object_id, 5))
        self.object_pannel.objects_controller[object_id].gain_dial.valueChanged.connect(lambda: self.send_object_metadata(object_id, 5))

        # 标签
        azi_label = QLabel('方位角')
        ele_label = QLabel('仰角')
        dis_label = QLabel('距离')
        width_label = QLabel('展宽')
        gain_label = QLabel('增益')
        
        # 当前目标元现实
        object_label = QLabel('Object' + str(object_id+1))
        object_label.setFixedHeight(int(self.widget_size[1]*0.05))

        # 状态二选开关
        self.object_pannel.objects_controller[object_id].on_button = QRadioButton('on')
        self.object_pannel.objects_controller[object_id].on_button.toggled.connect(lambda: self.change_3d(object_id))
        self.object_pannel.objects_controller[object_id].on_button.toggled.connect(lambda: self.send_object_metadata(object_id, 6))
        self.object_pannel.objects_controller[object_id].on_button.setChecked(False)

        # 输入端口
        self.object_pannel.objects_controller[object_id].port = QComboBox()
        self.object_pannel.objects_controller[object_id].port.setMaximumWidth(int(self.widget_size[0]*0.1))
        object_port_list = ['port'+str(i+1) for i in range(self.max_port_num)]
        self.object_pannel.objects_controller[object_id].port.addItems(object_port_list)
        self.object_pannel.objects_controller[object_id].port.currentIndexChanged.connect(lambda: self.send_object_metadata(object_id, 7))

        # value 标签
        self.object_pannel.objects_controller[object_id].azi_value_label = QLabel('0 °')
        self.object_pannel.objects_controller[object_id].ele_value_label = QLabel('0 °')
        self.object_pannel.objects_controller[object_id].dis_value_label = QLabel('50 m')
        self.object_pannel.objects_controller[object_id].width_value_label = QLabel('0')
        self.object_pannel.objects_controller[object_id].gain_value_label = QLabel('0 dB')

    
        # 网格排布
        layout = QGridLayout()
        layout.setContentsMargins(60, 0, 0, 0)
        layout.addWidget(object_label, 0, 0)
        layout.addWidget(azi_label, 1, 0)
        layout.addWidget(ele_label, 2, 0)
        layout.addWidget(dis_label, 3, 0)
        layout.addWidget(width_label, 4, 0)
        layout.addWidget(gain_label, 5, 0)

        layout.addWidget(self.object_pannel.objects_controller[object_id].on_button, 0, 1, alignment=Qt.AlignCenter)
        layout.addWidget(self.object_pannel.objects_controller[object_id].azi_dial, 1, 1)
        layout.addWidget(self.object_pannel.objects_controller[object_id].ele_dial, 2, 1)
        layout.addWidget(self.object_pannel.objects_controller[object_id].dis_dial, 3, 1)
        layout.addWidget(self.object_pannel.objects_controller[object_id].width_dial, 4, 1)
        layout.addWidget(self.object_pannel.objects_controller[object_id].gain_dial, 5, 1)

        layout.addWidget(self.object_pannel.objects_controller[object_id].port, 0, 2)
        layout.addWidget(self.object_pannel.objects_controller[object_id].azi_value_label, 1, 2)
        layout.addWidget(self.object_pannel.objects_controller[object_id].ele_value_label, 2, 2)
        layout.addWidget(self.object_pannel.objects_controller[object_id].dis_value_label, 3, 2)
        layout.addWidget(self.object_pannel.objects_controller[object_id].width_value_label, 4, 2)
        layout.addWidget(self.object_pannel.objects_controller[object_id].gain_value_label, 5, 2)


        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 2)


        self.object_pannel.objects_controller[object_id].setLayout(layout)
        self.object_pannel.objects_controller[object_id].setMaximumSize(int(self.widget_size[0]*0.3), int(self.widget_size[1]*0.8))
        self.object_pannel.objects_controller[object_id].setMinimumSize(int(self.widget_size[0]*0.3), int(self.widget_size[1]*0.45))
        
    def play_stop_button_init(self):
        self.object_pannel.play_button = QPushButton('开始')
        self.object_pannel.stop_button = QPushButton('停止')
        self.object_pannel.play_button.pressed.connect(self.start_play)
        self.object_pannel.stop_button.pressed.connect(self.stop_play)
        self.object_pannel.play_button.setFixedHeight(int(self.widget_size[1]*0.04))
        self.object_pannel.stop_button.setFixedHeight(int(self.widget_size[1]*0.04))
        
        layout = QHBoxLayout()
        layout.addWidget(self.object_pannel.play_button)
        layout.addWidget(self.object_pannel.stop_button)
        self.button_widget = QWidget()
        self.button_widget.setLayout(layout)
        self.button_widget.setFixedHeight(int(self.widget_size[1]*0.05))    


################################3D obects 显示区域########################################################
    def soundscape_pannel_ini(self):
        self.objects_3Dpannel = Q3DScatter()
        self.objects_3Dpannel.setFlags(self.objects_3Dpannel.flags() ^ Qt.FramelessWindowHint)
        self.objects_3Dpannel.setTitle('viewer')
        self.objects_3Dpannel.axisX().setRange(-15, 15)
        self.objects_3Dpannel.axisY().setRange(-15, 15)
        self.objects_3Dpannel.axisZ().setRange(-15, 15)
        # 关阴影
        self.objects_3Dpannel.setShadowQuality(QAbstract3DGraph.ShadowQuality())

        # 选中目标切换时的回调
        self.objects_3Dpannel.selectedSeriesChanged.connect(self.selected_item_changed)

        # 加入听音位头模型
        head_model = QCustom3DItem()
        head_model.setMeshFile('./png/head2.obj')
        head_model.setPosition(QVector3D(0, -3, 0))
        head_model.setScaling(QVector3D(1.5,1.5,1.5))
        rotation = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), -90)
        head_model.setRotation(rotation)
        self.objects_3Dpannel.addCustomItem(head_model)


        # remove black broaden
        self.objects_3Dpannel.showFullScreen()
        hwnd = win32gui.FindWindowEx(0, 0, None,"viewer")
        window = QWindow.fromWinId(hwnd)
        self.objects_3Dpannel_winodow = QWidget.createWindowContainer(window)
        self.objects_3Dpannel_winodow.setMaximumSize(int(self.widget_size[0]*0.7), int(self.widget_size[1]))
        self.objects_3Dpannel_winodow.setMinimumSize(int(self.widget_size[0]*0.7*0.5), int(0.5*self.widget_size[1]))
        self.soundscape_item_init()

        # 调整相机位置，更好的角度来观察散点
        camera = self.objects_3Dpannel.scene().activeCamera()
        camera.setCameraPreset(Q3DCamera.CameraPresetFront)

    def soundscape_item_init(self):
        self.series_sum = [i for i in range(self.max_objects_num)]
        for i in range(self.max_objects_num):
            self.series_sum[i] = QScatter3DSeries()
            self.series_sum[i].name = str(i)
            self.series_sum[i].dataProxy().addItem(QScatterDataItem(QVector3D(0, 0, 0)))
            self.series_sum[i].setItemSize(0.000000000001)
            self.objects_3Dpannel.addSeries(self.series_sum[i])


################################################################################################

if __name__ == '__main__':
    load_data = np.load('./config/metadata.npy', allow_pickle=True)
    metadata = load_data.tolist()
    json_data  = json.dumps(metadata)

    # fp = open('metadata_save.json',mode = 'w')
    # json.dumps(metadata, fp, indent=4)

    with open('metadata_save.json',mode = 'w', encoding = 'utf-8') as fp:
        fp.write(json.dumps(metadata,indent=2,ensure_ascii=False))

    app = QApplication(argv)
    demo = main_ui()
    demo.show()
    exit(app.exec())

