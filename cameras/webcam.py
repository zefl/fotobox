#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_pi.py

import cv2
import multiprocessing as mp

from cameras.cameraBase import CameraBase
from cameras.cameraBase import stream_run


#from https://github.com/pibooth/pibooth/blob/master/pibooth/camera/opencv.py
def check_webcam():
    """Checks if the camera can be connected on the current system

    :returns: True if camera is found on system, false if camera type is not found on system
    """
    if not cv2:
        return False  # OpenCV is not installed

    camera = cv2.VideoCapture(0) #todo make it usable with raspi
    if camera.isOpened():
        camera.release()
        return True

    return False        

class Camera(CameraBase):
    def __init__(self):
        super().__init__()

    def connect(self,  fps: int = 0):
        if self._camera == None:
            self._camera =  cv2.VideoCapture(0)
            self._frameRate = fps
            self._frameSize = 0
            self._connected = True

    def disconnect(self):
        if self._camera:
            self._connected = False
            self._camera.release()
            self._camera = None

    def frameSize(self):
        if self._frameSize:
            return self._frameSize
        else:
            return 0

    def _take_picture(self):
        check, frame = self._camera.read()
        return frame
        
    def _capture_stream(self):
        """This function takes a frame as fast as possible
        
        :returns: The current frame picture
        """
        check, frame = self._camera.read()
        if check:
            frame = cv2.flip(frame, 1)
            if self._frameSize == 0:
                self._frameSize == len(frame)
        else:
            frame = []
        return frame

    def _create_process(self):
        return mp.Process(target=_stream_runWebcam, args=(self._mp_FrameQueues, self._mp_StopEvent, self._frameRate,))

"""Global Function which is called by subprocess

:param queue: queue of parent class which holds frame data
:param stopEvent : Eventflag which causes the process to stop
:param frameRate : static framerate on which the camera should work
"""
def _stream_runWebcam(queue : mp.Queue, stopEvent: mp.Value, frameRate):
    camera = Camera()
    stream_run(camera, queue, stopEvent, frameRate)