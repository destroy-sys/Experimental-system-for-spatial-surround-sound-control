#!/usr/bin/env python
# -*- coding: utf-8 -*-


from bottle import *
import numpy as np
import multiprocessing as mp
import time
import jack, json
import http.server
from itertools import islice

from scipy.io.wavfile import write
# from gevent import monkey; monkey.patch_all()

#init queue
global mp_queue
mp_queue = mp.Queue(2)
global state_play
state_play = False
global first_play
first_play = False
global play_queue
play_queue = mp.Queue()

# mp_queue.put(1, block=False)
# mp_queue.put(1, block=False)

class spatial_audio_processor(mp.Process):
    def __init__(self):
        super(spatial_audio_processor, self).__init__()

        global mp_queue
        self.mp_queue = mp_queue
        global play_queue
        self.play_queue =play_queue
        self.state_play = True
        # 启用的objecs_id 
        self.dbap_obj_id = []
        self.broaden_obj_id = []        

        # object source port 
        self.dbap_obj_port = []
        self.broaden_obj_port = []

        self.__jackStatus_flag = mp.Event()
        self.__jackStatus_flag.clear()

    def run(self):

        self.client = jack.Client('spatial_audio_processor')
        if self.client.status.server_started:
            print('JACK server started')
        if self.client.status.name_not_unique:
            print('unique name {0!r} assigned'.format(self.client.name))


        @self.client.set_client_registration_callback
        def client_registration(name, register):
            print('client', repr(name), ['unregistered', 'registered'][register])

        # 帧长由jack服务器决定
        @self.client.set_blocksize_callback
        def blocksize(blocksize):
            print('setting blocksize to', blocksize)

        # 采样率由jack服务器决定
        @self.client.set_samplerate_callback
        def samplerate(samplerate):
            print('setting samplerate to', samplerate)

        # 帧播放回调
        @self.client.set_process_callback
        def process(frames):

           # get dbap input frame signal
            out_frame_sig = np.zeros([24, frames])
            temp_idx = 0
            for i in range(24):
                out_frame_sig[temp_idx, :] = self.client.inports[i].get_array()
                temp_idx = temp_idx+1

            if self.state_play == False :
                out_frame_sig = np.zeros([24, frames])
            # for i in range(self.ls_num):
            #     self.client.outports[i].get_array()[:] = out_frame_sig[i, :]

            for i in range(24):
                self.client.outports[i].get_array()[:] = out_frame_sig[i, :]

        # 意外错误退出
        @self.client.set_shutdown_callback
        def shutdown(status, reason):
            print('JACK shutdown!')
            print('status:', status)
            print('reason:', reason)
            self.__jackStatus_flag.set()

        # create two port pairs
        for number in range(32):
            self.client.inports.register('input_{0}'.format(number+1))

        for number in range(32):
            self.client.outports.register('output_{0}'.format(number+1))

        with self.client:
            capture = self.client.get_ports(is_physical=False, is_output=True)
            if not capture:
                raise RuntimeError('No physical capture ports')

            # 物理输入连接到虚拟输出
            playback = self.client.get_ports(is_physical=True, is_input=True)
            if not playback:
                raise RuntimeError('No physical playback ports')

            # if (len(self.client.outports) == (len(playback)-2)):
            #     for src, dest in zip(self.client.outports, playback):
            #         self.client.connect(src, dest)

            print('jack client running!')
            self.__jackStatus_flag.wait()
            print('jack client stopped!')

    def start_jack_client(self):
        with self.client:
            # 物理输入连接到虚拟输出
            playback = self.client.get_ports(is_physical=True, is_input=True)
            if not playback:
                raise RuntimeError('No physical playback ports')
        if (len(self.client.outports) == (len(playback)-2)):
            for src, dest in zip(self.client.outports, playback):
                self.client.connect(src, dest)

    def stop_jack_client(self):
        with self.client:
            # 物理输入连接到虚拟输出
            playback = self.client.get_ports(is_physical=True, is_input=True)
            if not playback:
                raise RuntimeError('No physical playback ports')
        if (len(self.client.outports) == (len(playback))):
            for src, dest in zip(self.client.outports, playback):
                self.client.disconnect(src, dest)

    def stop_jack_client(self):
        self.__jackStatus_flag.set()




#HTTPSERVER模块 http_server
class http_server_test(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        print(self.requestline)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        global spatial_audio_server
        global state_play
        global first_play
        global play_queue

        global now_param
        if self.path == '/play':
            print('start to play')
            # self.wfile.write(b'{"status": "success"}')
            # # bug here
            # # 传入扬声器位置

            if state_play == False :
                state_play = True
                play_queue.put(state_play, block=False)
                if first_play == False :
                    first_play = True
                    spatial_audio_server = spatial_audio_processor()
                    spatial_audio_server.start()

        elif self.path == '/stop':
            # self.wfile.write(b'{"status": "success"}')
            if state_play == True :
                state_play = False
                play_queue.put(state_play, block=False)
                if first_play == True:
                    spatial_audio_server.state_play = False

                print('stop success')







if __name__ == '__main__':

    server1 = http.server.HTTPServer(('localhost', 9425), http_server_test)
    # server1 = http.server.HTTPServer(('169.254.110.101', 9425), http_server_test)
    # print(server1.http_server_test.type)
    print('Starting server, use <Ctrl-C> to stop')
    server1.serve_forever()

    time.sleep(1000000)






















