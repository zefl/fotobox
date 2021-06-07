#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_pi.py

import copy
import cv2
from datetime import datetime
import multiprocessing as mp
import time
import os

from cameras.IFotocamera import IFotocamera


class CameraBase(IFotocamera):
    def __init__(self):
        """Variables for handling camera
        """
        self._camera = None
        """Variables for static picture
        """
        self._frame =[]
        self._frameAvalible = False
        """Variables for handling streaming
        """
        self._process = None
        self._mp_StopEvent = mp.Value('i', lock=False)
        self._mp_FrameQueue = mp.Queue(2)
        self._frameRate = 30

    """Interface functions
    """  
    def picture_take(self):
        """If subporcess is active use frame form this one to take picture"""
        if self._process.is_alive():
            self._frame = self._mp_FrameQueue.get()
            self._frameAvalible = True   
        else:
            """Check if camera is still connect"""
            if self._camera == None:
                self.connect()
            self._frame = self._take_picture()
            self._frameAvalible = True
        
    def picture_show(self):
        if self._frameAvalible:
            self._frameAvalible = False
            return self._frame
        else:
            return []
            
    def picture_save(self, folder="", file=""):
        if self._frameAvalible:
            now = datetime.now()
            picFrame = copy.copy(self._frame);
            if(file == ""):
                """create new filename if no filename was given"""
                file = now.strftime('%Y_%m_%d_%H_%M_%S') 
            picName = os.path.join(folder, file + ".jpg")
            cv2.imwrite(picName, picFrame)  
                
    def stream_start(self):
        """check if thread is active"""
        if self._process == None:
            self.disconnect()
            self._process = self._create_process()
            self._process.start()

    def stream_stop(self):
        #Stop stream, thread will be stoped
        self._threadStopEvent = True
        self._process.join()
        self.connect()
    
    def stream_show(self):
        if not(self._mp_FrameQueue.empty()):
            return self._mp_FrameQueue.get()
        else:
            return []
    
    """Specific Functions
    """ 
    def connect(self,  fps: int = 0):
        raise NotImplementedError
    
    def disconnect(self):
        raise NotImplementedError

    def _take_picture(self):
        raise NotImplementedError
        
    def _capture_stream(self):
        raise NotImplementedError

    def _create_process(self):
        raise NotImplementedError

"""Global Function which is called by subprocess

:param queue: queue of parent class which holds frame data
:param stopEvent : Eventflag which causes the process to stop
:param frameRate : static framerate on which the camera should work
:param streamCamera : specific instansiation of child class
"""
def stream_run(streamCamera : CameraBase, queue : mp.Queue, stopEvent: mp.Value, frameRate : int):
    streamCamera.connect(frameRate)
    desiredCyleTime = 1 / frameRate #run this thread only as fast as nessecarry
    nextFrameTime = 0
    while True:
            currentTime = time.time()
            if(currentTime > nextFrameTime):
                nextFrameTime = currentTime + desiredCyleTime
                #call camera to take picutre
                if not(queue.full()):
                    queue.put(streamCamera._capture_stream())                                                            
            if stopEvent.value:
                break;
    stopEvent.value = False
    queue.close() #check if i need to 
    streamCamera.disconnect()