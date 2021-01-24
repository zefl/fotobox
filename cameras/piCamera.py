#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_pi.py
#  
#  
# 
try: 
    import picamera
    from picamera.array import PiRGBArray
except ImportError:
    pass  # gphoto2 is not supported if run on windows
    
import io
import cv2
import numpy as np
import time
from datetime import datetime
import subprocess
import sys
import os

from cameras.IFotocamera import IFotocamera

#from https://github.com/pibooth/pibooth/blob/master/pibooth/camera/rpi.py
def check_piCamera():
    """Return True if a RPi camera is found.
    """
    if 'picamera' not in sys.modules:
        return False
    
    if not picamera:
        return False  # picamera is not installed
    try:
        process = subprocess.Popen(['vcgencmd', 'get_camera'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _stderr = process.communicate()
        if stdout and u'detected=1' in stdout.decode('utf-8'):
            return True
    except OSError:
        pass
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
            # start background frame thread
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
    
    ##################################      
    #Internal function
    ##################################
    def __init__(self):
        #################
        #Variables for handling camera
        #################
        self.camera = None
        self.stream = None
        self.rawCapture = None
        #################
        #Variables for handling streaming
        #################
        self.frameAvalible = False
        self.frame = []  # current frame is stored here
        self.streamActive = False
        self.thread = None

    def connect(self, _fps: int = 0):
        if self.camera == None:
            self.camera = picamera.PiCamera()
            self.framerate = _fps            
            
            # camera setup
            self.camera.resolution = (640, 480)
            self.camera.framerate = _fps
            self.camera.hflip = False
            self.camera.vflip = True
            self.camera.video_stabilization = True
            self.camera.iso = 100

            # let camera warm up
            self.camera.start_preview()
            time.sleep(2)
            self.camera.stop_preview()
            
            self.stream = io.BytesIO()
            self.rawCapture = PiRGBArray(self.camera)
            
    def disconnect(self):
        #from https://www.raspberrypi.org/forums/viewtopic.php?t=227394
        self.camera.close()
        self.camera = None
        
    def _capture_stream(self):
        #wait for next caputre
        for data in self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True):
            #get data via rawCaputre
            frame = data.array
            self.rawCapture.truncate(0) # reset stream for next frame
            self.frameAvalible = True
            return frame
            
    def _stream_thread(self):
        _desiredCyleTime = 1 / self.framerate #run this thread only as fast as nessecarry
        while(self.streamActive):
                self.streamActive = True
                _startTimeCature = time.time()
                #call camera to take picutre
                self.frame = self._capture_stream()                                                                 
                #check cycle time with respect to given cycel time
                _endTimeCature = time.time()
                _cyleTime = _endTimeCature - _startTimeCature
                _waitTime = _desiredCyleTime - _cyleTime
                if _waitTime > 0:
                    time.sleep(_waitTime)
                else:
                    #print("Warning: Camera cannot take picture with given fps")       
                    pass
        self.thread = None #stop thread
        self.frameAvalible = False
        self.frame=[] #delete picture