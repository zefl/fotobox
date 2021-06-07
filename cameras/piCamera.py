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
import time
import subprocess
import sys
import multiprocessing as mp

from cameras.cameraBase import CameraBase
from cameras.cameraBase import stream_run


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

class Camera(CameraBase):
    def __init__(self):
        super().__init__()

    def connect(self, _fps: int = 0):
        if self._camera == None:
            self._camera = picamera.PiCamera()
            self._framerate = _fps            
            
            # camera setup
            self._camera.resolution = (640, 480)
            self._camera.framerate = _fps
            self._camera.hflip = False
            self._camera.vflip = True
            self._camera.video_stabilization = True
            self._camera.iso = 100

            # let camera warm up
            self._camera.start_preview()
            time.sleep(2)
            self._camera.stop_preview()
            
            self._stream = io.BytesIO()
            self._rawCapture = PiRGBArray(self.camera)
            
    def disconnect(self):
        #from https://www.raspberrypi.org/forums/viewtopic.php?t=227394
        self._camera.close()
        self._camera = None

    def _take_picture(self):
        raise NotImplementedError
        
    def _capture_stream(self):
        #wait for next caputre
        for data in self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True):
            #get data via rawCaputre
            frame = data.array
            self.rawCapture.truncate(0) # reset stream for next frame
            return frame

    def _create_process(self):
        return mp.Process(target=_stream_runPicam, args=(self._mp_FrameQueue, self._mp_StopEvent, self._frameRate,))

"""Global Function which is called by subprocess

:param queue: queue of parent class which holds frame data
:param stopEvent : Eventflag which causes the process to stop
:param frameRate : static framerate on which the camera should work
"""
def _stream_runPicam(queue : mp.Queue, stopEvent: mp.Value, frameRate):
    camera = Camera()
    stream_run(camera, queue, stopEvent, frameRate)