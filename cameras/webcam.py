#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_pi.py

import time
from datetime import datetime
import threading
import cv2
import copy
import os

from cameras.IFotocamera import IFotocamera

import multiprocessing as mp
import ctypes
import numpy as np

#from https://github.com/pibooth/pibooth/blob/master/pibooth/camera/opencv.py
def check_webcam():
    """Return True if a camera compatible with OpenCV is found.
    """
    if not cv2:
        return False  # OpenCV is not installed

    camera = cv2.VideoCapture(0)
    if camera.isOpened():
        camera.release()
        return True

    return False        

class Camera(IFotocamera):
    ##################################      
    #Common functions
    ##################################   
    def picture_take(self):
        if not(self.streamActive):
            self.frame = self._take_picture()
            self.frameAvalible = True
        
    def picture_show(self):
        if self.frameAvalible:
            return self.frame
        else:
            return []
            
    def picture_save(self, _folder="", _file=""):
        if self.frameAvalible:
            now = datetime.now()
            picFrame = copy.copy(self.frame);
            if(_file == ""):
                _file = now.strftime('%Y_%m_%d_%H_%M_%S') 
            picName = os.path.join(_folder, _file + ".jpg")
            cv2.imwrite(picName, picFrame)  
                
    def stream_start(self):
        #check if thread is active 
        if not(self.streamActive):
            self.thread = threading.Thread(target=self._stream_thread)
            self.streamActive = True
            self.thread.start()

    def stream_stop(self):
        #Stop stream, thread will be stoped
        self.streamActive = False
    
    def stream_capture(self):
        if self.frameAvalible:
            return self.frame
        else:
            return []
    
    def connect(self,  _fps: int = 0):
        if self.camera == None:
            self.camera =  cv2.VideoCapture(0)
            self.framerate = _fps   
    
    def disconnect(self):
        self.camera.release()
        self.camera = None
    ##################################      
    #Internal functions
    ##################################
    def __init__(self):
        self.subPorcessActive = True
        #################
        #Variables for handling camera
        #################
        self.camera = None
        #################
        #Variables for handling streaming
        #################
        self.frameAvalible = False
        self.frame = []  # current frame is stored here
        self.streamActive = False
        self.thread = None

    def _take_picture(self):
        check, frame = self.camera.read()
        return frame
        
    def _capture_stream(self):
        check, frame = self.camera.read()
        frame = cv2.flip(frame, 1)
        return frame

    def _stream_thread(self):
        _desiredCyleTime = 1 / self.framerate #run this thread only as fast as nessecarry
        _lastWakeUp = time.time()
        while(self.streamActive):
                _currentTime = time.time()
                if(_currentTime - _lastWakeUp > _desiredCyleTime):
                    _lastWakeUp = time.time()
                    #call camera to take picutre
                    self.frame = self._capture_stream()     
                    self.frameAvalible = True                                                            
                    #check cycle time with respect to given cycel time
        self.thread = None #stop thread
        self.frameAvalible = False
        self.frame=[] #delete picture
        
class Streamingcamera(IFotocamera): 
    def connect(self,  _fps: int = 0):
        pass

    def disconnect(self):
        pass

    def picture_take(self):
        pass

    def picture_show(self):
        if self.frameAvalible:
            return self.frame
        else:
            return []
            
    def picture_save(self, _folder="", _file=""):
        if self.frame:
            now = datetime.now()
            picFrame = copy.copy(self.frame);
            if(_file == ""):
                _file = now.strftime('%Y_%m_%d_%H_%M_%S') 
            picName = os.path.join(_folder, _file + ".jpg")
            cv2.imwrite(picName, picFrame)    

    def stream_start(self):
        #check if thread is active 
        if self.process == None:
            #from https://stackoverflow.com/questions/49191615/right-way-to-share-opencv-video-frame-as-numpy-array-between-multiprocessing-pro
            self.frame = mp.Array(ctypes.c_uint8, self.shape[0] * self.shape[1] * self.shape[2], lock=True)
            self.streamActive = mp.Value('i', lock=False)
            self.frameAvalible =  mp.Value('i', lock=True)
            self.process = mp.Process(target=_stream_process, args=(self.frame, self.streamActive, self.frameAvalible))
            self.process.start()

    def stream_stop(self):
        #Stop stream, thread will be stoped
        self.streamActive.value = False
    
    def stream_capture(self):
        if self.frameAvalible.value:
            arr = np.frombuffer(self.frame.get_obj(), dtype=np.uint8)
            b = arr.reshape(self.shape)
            return b
        else:
            return []
    
    ##################################      
    #Internal functions
    ##################################
    def __init__(self):
        #################
        #Variables for handling streaming
        #################
        self.process = None
        camera = cv2.VideoCapture(0)
        ret, frame = camera.read()
        self.shape = frame.shape 
        camera.release()

def _stream_process(frame, streamActive, frameAvalible):
    camera = cv2.VideoCapture(0)
    check, newFrame = camera.read()
    framerate = 30
    _desiredCyleTime = 1 / framerate #run this thread only as fast as nessecarry
    streamActive.value = True
    #from https://stackoverflow.com/questions/9754034/can-i-create-a-shared-multiarray-or-lists-of-lists-object-in-python-for-multipro
    arr = np.frombuffer(frame.get_obj(), dtype=np.uint8) #if lock true you need get_objct, lock flase don't need it)
    b = arr.reshape(newFrame.shape)
    _lastWakeUp = time.time()
    while(streamActive.value):
            _currentTime = time.time()
            if(_currentTime - _lastWakeUp > _desiredCyleTime):
                _lastWakeUp = time.time()
                check, frame = camera.read()
                frame = cv2.flip(frame, 1)
                b[:] = frame
                if check:
                    frameAvalible.value = True
    camera.release()