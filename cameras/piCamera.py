#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_pi.py
#  
#  
#  
import io
import picamera
import cv2
import numpy as np
import time
from picamera.array import PiRGBArray
import subprocess

from cameras.ICamera import ICamera

#from https://github.com/pibooth/pibooth/blob/master/pibooth/camera/rpi.py
def pi_camera_connected():
    """Return True if a RPi camera is found.
    """
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


class Camera(ICamera):

    def __init__(self):
        self.camera = None
        self.stream = None
        self.rawCapture = None

    def initialize(self, _modus: str, _fps: int = 0):
        print("Logging: Init pi Camera")
        if _modus == 'capture_stream':
            if self.camera == None:
                self.camera = picamera.PiCamera()
                
                # camera setup
                self.camera.resolution = (640, 480) #480p
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

    #measurement 
    #15 fps, (640, 480),iso = 100, 
    #Sent 90 images in 6 seconds at 14.74fps (bytesIO)
    #Sent 89 images in 6 seconds at 14.73fps (rawData)

    #36 fps, (640, 480),iso = 100, 
    #Sent 101 images in 6 seconds at 16.82fps (bytesIO)
    #Sent 117 images in 6 seconds at 19.23fps (rawData)
    
    def capture_picture(self):
        raise NotImplementedError
            
    def capture_stream(self):   
        #wait for next caputre
        newFrameTimestamp = time.time()
        for data in self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True):
            # Debug to measure fps
            if False:
                lastFrameTimestamp = newFrameTimestamp
                newFrameTimestamp = time.time()
                currentFPS = 1 / (newFrameTimestamp - lastFrameTimestamp)
                print("Current FPS: %.3f" % (currentFPS))   
            #get data via rawCaputre
            frame = data.array
            self.rawCapture.truncate(0) # reset stream for next frame
            return frame
            
    def convert_to_cv2(self, _frame):
        return _frame