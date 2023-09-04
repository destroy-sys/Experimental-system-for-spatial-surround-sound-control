import requests
import json
import numpy as np
PI = 3.14159
import multiprocessing as mp


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



class http_client():
    def __init__(self):
        # header
        self.headers = {'content-type':'application/json'}
        self.url="http://127.0.0.1:9425/"
        self.msg_queue = mp.Queue(100)



    def send_play_control(self):
        # try:
        #     return_mess = requests.get(self.url + 'play', timeout=0.5)
        #     status = True
        # except:
        #     status = False
        return_mess = requests.get(self.url + 'play',headers=self.headers)
        print('start to play')
        #print(return_mess.text)
        status = True
        return status

    def send_stop_control(self):
        try:
            return_mess = requests.get(self.url + 'stop', timeout=0.5)
            status = True
        except:
            status = False
        return status