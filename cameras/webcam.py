#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_pi.py
#  
#  
#  
import time
import threading
import cv2
import copy
from cameras.ICamera import ICamera


class webCam(ICamera):

    def __init__(self):
        self.videoCap = None

    def __del__(self):
        if self.videoCap != None:
            self.videoCap.release()

    def initialize(self, _modus: str, _fps: int = 0):
        if _modus == 'capture_stream':
            if self.videoCap == None:
                self.videoCap =  cv2.VideoCapture(0)
        elif _modus == 'capture_picture':
            if self.videoCap == None:
                self.videoCap =  cv2.VideoCapture(0)
    
    def capture_stream(self):   
        check, frame = self.videoCap.read()
        frame = cv2.flip(frame, 1)
        return frame

    def capture_picture(self):   
        check, frame = self.videoCap.read()
        return frame    
    
    def convert_to_cv2(self, _frame):
        return _frame