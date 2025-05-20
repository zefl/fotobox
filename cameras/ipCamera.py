from cameras.cameraBase import CameraBase
from cameras.cameraBase import stream_run

import requests
import multiprocessing as mp
import numpy as np
import json


def check_ipcam():
    return True


class Camera(CameraBase):
    def __init__(self):
        super().__init__()

    def connect(self, fps: int = 0):
        print("[picInABox] Connect to ip webcam")
        if self._camera == None:
            self._ip = "http://127.0.0.1:5002"
            self._frameRate = fps
            self._frameSize = 0
            self._connected = True
            print("[picInABox] Connect done")

    def disconnect(self):
        if self._camera:
            print("[picInABox] Disconnect webcam")
            self._connected = False
            self._camera.release()
            self._camera = None

    def frameSize(self):
        if self._frameSize:
            return self._frameSize
        else:
            return 0

    def _take_picture(self):
        response = requests.get(f"{self._ip}/api/controlCamera")
        if response.status_code == 200:
            return response.content
        return None

    def _capture_stream(self):
        import time

        response = requests.get(f"{self._ip}/lastRawFrame")
        if response.status_code == 200:
            data = json.loads(response.content)
            frame = np.array(data, dtype=np.uint8)
            self._frameSize == len(frame)
        else:
            frame = []
        return frame

    def _create_process(self):
        return mp.Process(
            target=_stream_runWebcam,
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


def _stream_runWebcam(queue: mp.Queue, stopEvent: mp.Value, frameRate):
    camera = Camera()
    stream_run(camera, queue, stopEvent, frameRate)
