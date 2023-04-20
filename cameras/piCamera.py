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


# from https://github.com/pibooth/pibooth/blob/master/pibooth/camera/rpi.py
def check_piCamera():
    """Return True if a RPi camera is found."""
    if "picamera" not in sys.modules:
        return False

    if not picamera:
        return False  # picamera is not installed
    try:
        process = subprocess.Popen(
            ["vcgencmd", "get_camera"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, _stderr = process.communicate()
        if stdout and "detected=1" in stdout.decode("utf-8"):
            return True
    except OSError:
        pass
    return False


class Camera(CameraBase):
    def __init__(self):
        super().__init__()

    def _connect(self, _fps: int = 0):
        """There is a problem with closing the camera in one process and reopning it.
        Therfore the camera will always be a streaming camera
        """

    def connect(self, _fps: int = 0):
        print("[picInABox] Connect to pi camera")
        if self._camera == None:
            self._camera = picamera.PiCamera()
            self._framerate = _fps

            # camera setup
            self._camera.resolution = (640, 480)
            self._frameSize = 640 * 480 * 3
            self._camera.framerate = _fps
            self._camera.hflip = False
            self._camera.vflip = True
            self._camera.video_stabilization = True
            self._camera.iso = 400

            # let camera warm up
            self._camera.start_preview()
            time.sleep(2)
            self._camera.stop_preview()
            self._stream = io.BytesIO()
            self._rawCapture = PiRGBArray(self._camera)
            self._connected = True
            print("[picInABox] Connect done")

    def disconnect(self):
        if self._camera:
            print("[picInABox] Disconnect pi camera")
            self._connected = False
            # from https://www.raspberrypi.org/forums/viewtopic.php?t=227394
            self._camera.stop_preview()
            time.sleep(3)
            self._camera.close()
            self._rawCapture.close()
            self._stream.close()
            self._camera = None

    def frameSize(self):
        if self._frameSize:
            return self._frameSize
        else:
            return 0

    def _capture_stream(self):
        try:
            # wait for next caputre
            for data in self._camera.capture_continuous(
                self._rawCapture, format="bgr", use_video_port=True
            ):
                # get data via rawCaputre
                frame = data.array
                self._rawCapture.truncate(0)  # reset stream for next frame
                return frame
        except:
            print("[picInABox] Error in reading Pi Camera")
            raise RuntimeError("[picInABox] Error in reading Pi Camera")

    def _create_process(self):
        return mp.Process(
            target=_stream_runPicam,
            args=(
                self._mp_FrameQueues,
                self._mp_StopEvent,
                self._frameRate,
            ),
        )


"""Global Function which is called by subprocess

:param queue: queue of parent class which holds frame data
:param stopEvent : Eventflag which causes the process to stop
:param frameRate : static framerate on which the camera should work
"""


def _stream_runPicam(queues, stopEvent: mp.Value, frameRate):
    camera = Camera()
    camera._connect(frameRate)  # call private connect to create pi Camera instance
    stream_run(camera, queues, stopEvent, frameRate)
