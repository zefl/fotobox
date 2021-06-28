#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  cameraRecorder.py
#  
#  
# 

##############
#Notes:
#- could be an timer to close thread if not needed after certain time
# self.last_access = time.time() #reset timeout so at least 30 sec of capturing
#
############## 

import time
import threading
import multiprocessing as mp
import cv2
import copy
import os
import numpy as np
import requests
from datetime import datetime
from PIL import Image
import glob
#from audioRecorder import audio

from cameras.IFotocamera import IFotocamera


class CameraTimelapss():
    
    def __init__(self, camera: IFotocamera):
        self._camera = camera
        self._process = None
        self._mp_StopEvent = mp.Value('i', lock=False)
        self._mp_FrameQueue = mp.Queue(2)
        self._thread = None
        self._threadActive = False
        self._folder = "data/timelaps"
        self._picturePerMinute = 60
        
    def recording_start(self):
        #if no capturing is active start is
        if self._process == None:
            """create process will be implemented by child on virtual in this context"""
            self._process = mp.Process(target=_stream_recording,args=(self._mp_StopEvent,self._mp_FrameQueue))
            self._mp_StopEvent.value = False
            self._process.start()
        if self._threadActive == False:
            # start background frame thread
            self._thread = threading.Thread(target=self._thread_recording)
            #self.thread = threading.Timer(1/self.fps, self._thread_timer_recording)
            self._thread.start()
        
    def recording_stop(self):
        if self._process:
            self._mp_StopEvent.value = True
            self._process.join()
            self._process = None
        self._threadActive = False
            
    def recording_save(self, folder="", file=""):
        if folder == "":
            folder = self._folder
        if file == "":
            file = "timelaps_" + datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        frames = []
        print("Save Timelaps")
        _files = glob.glob('data/timelaps/*.jpg')
        minFrameSize= Image.open(_files[0]).size
        _files.sort(key=os.path.getctime)
        for _file in _files:
            image = Image.open(_file)
            frames.append(image)
            if image.size[0] * image.size[1] < minFrameSize[0] * minFrameSize[1]:
                minFrameSize = frames.size
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_file = os.path.join(folder, file +'.avi' )
        #used 30fps if 1 picture per second => 1 sec video 30 sec real life => 1hour real life     2 min video                           
        videoWriter = cv2.VideoWriter(video_file, fourcc, 60, minFrameSize) 
        for frame in frames:
            frame = frame.resize(minFrameSize, Image.ANTIALIAS)
            open_cv_image = np.array(frame) 
            # Convert RGB to BGR 
            open_cv_image = open_cv_image[:, :, ::-1].copy() 
            videoWriter.write(open_cv_image)
        videoWriter.release()
        print("End Timelaps")

    def _thread_recording(self):
        self._camera.connect()
        self._camera.stream_start()
        self._threadActive = True
        while(self._threadActive):
            time.sleep(self._picturePerMinute / 60)
            self._camera.picture_take()
            self._mp_FrameQueue.put(self._camera.picture_show())
        self._thread = None

def _stream_recording(stopEvent: mp.Value, queue: mp.Queue):
    while(True):
        #req = requests.get('http://127.0.0.1:5000/lastRawFrame')
        if not(queue.empty()):
            picName = os.path.join("data/timelaps", datetime.now().strftime('%Y_%m_%d_%H_%M_%S')  + ".jpg")
            cv2.imwrite(picName, queue.get())
        if stopEvent.value:
            break