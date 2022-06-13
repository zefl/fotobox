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
import sys
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
        self._folder = "data/timelaps/"
        self._picturePerMinute = 60
        self._save_percent = 0
        self._save_step = "None"
        self._remaining_time = time.time()
        
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
        # TODO wait for finish 
        if folder == "":
            folder = self._folder
        if file == "":
            file = "timelaps_" + datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        print("Save Timelaps")
        _files = glob.glob(folder+'*.jpg')
        minFrameSize = (0,0)
        sorted(_files)
        self._save_step = "Bildgröße ermitteln"
        start_time = time.time()
        for _file in _files:
            try:
                self._save_percent = (_files.index(_file) / len(_files)) * 100
                image = Image.open(_file)
                minPixel = minFrameSize[0] * minFrameSize[1]
                currentPixel = image.size[0] * image.size[1]
                if minPixel == 0 or currentPixel < minPixel:
                    if currentPixel != 0:
                        minFrameSize = image.size
                elapsed_time = time.time() - start_time
                estimated_time = (elapsed_time / _files.index(_file)) * len(_files)
                self._remaining_time = estimated_time - elapsed_time
            except:
                 print(f"Unexpected error: {sys.exc_info()[0]} in {_file}")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_file = os.path.join(folder, file +'.avi' )
        # used 24fps                       
        videoWriter = cv2.VideoWriter(video_file, fourcc, 24, minFrameSize) 
        self._save_step = "Rendern der Timelaps"
        start_time = time.time()
        for _file in _files:
            try:
                self._save_percent = (_files.index(_file)/len(_files))*100
                frame = Image.open(_file)
                frame = frame.resize(minFrameSize, Image.ANTIALIAS)
                open_cv_image = np.array(frame) 
                # Convert RGB to BGR 
                open_cv_image = open_cv_image[:, :, ::-1].copy() 
                videoWriter.write(open_cv_image)
                elapsed_time = time.time() - start_time
                estimated_time = (elapsed_time / _files.index(_file)) * len(_files)
                self._remaining_time = estimated_time - elapsed_time
            except:
                print("Error in Pricture skiped")
        videoWriter.release()
        self._save_step = "Rendern Fertig"
        self._save_percent = 0
        self._save_percent = 0

        print("End Timelaps")
        
    def status_save(self):
        return {"step" : self._save_step, "percent" : self._save_percent, "run_time" : self._remaining_time}

    def _thread_recording(self):
        self._camera.connect()
        self._camera.stream_start()
        self._threadActive = True
        while(self._threadActive):
            time.sleep(self._picturePerMinute / 60)
            try:
                self._camera.picture_take()
            except:
                print("Error in timelaps picture take")
            self._mp_FrameQueue.put(self._camera.picture_show())
        self._thread = None

def _stream_recording(stopEvent: mp.Value, queue: mp.Queue):
    while(True):
        #req = requests.get('http://127.0.0.1:5000/lastRawFrame')
        if not(queue.empty()):
            number_of_files = len(glob.glob('data/timelaps/*'))
            picName = os.path.join("data/timelaps", f'foto_{(number_of_files + 1):08}'  + ".jpg")
            cv2.imwrite(picName, queue.get())
        if stopEvent.value:
            break