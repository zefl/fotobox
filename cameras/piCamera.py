try:
    import libcamera
    from picamera2 import Picamera2
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
    if "picamera2" not in sys.modules:
        return False

    if not Picamera2:
        return False  # picamera is not installed

    # TODO check if camera is detected
    return True


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
            self._camera = Picamera2()
            self._framerate = _fps

            # camera setup
            self._camera.framerate = _fps
            config = self._camera.create_preview_configuration({"format": "RGB888"})
            config["transform"] = libcamera.Transform(hflip=0, vflip=1)
            config["controls"]["NoiseReductionMode"] = libcamera.controls.draft.NoiseReductionModeEnum.Fast
            self._camera.configure(config)
            self._camera.set_controls({"ExposureTime": 10000, "AnalogueGain": 8.0})
            # Old settting, but for now it seems fine with the settings above
            # self._camera.video_stabilization = True
            # self._camera.iso = 400

            # Default is (640,480)
            self._frameSize = config["main"]["size"][0] * config["main"]["size"][1] * 3
            self._camera.start()
            time.sleep(2)
            self._stream = io.BytesIO()
            self._connected = True
            print("[picInABox] Connect done")

    def disconnect(self):
        if self._camera:
            print("[picInABox] Disconnect pi camera")
            self._connected = False
            # from https://www.raspberrypi.org/forums/viewtopic.php?t=227394
            self._camera.stop()
            time.sleep(3)
            self._camera.close()
            self._stream.close()
            self._camera = None

    def frameSize(self):
        if self._frameSize:
            return self._frameSize
        else:
            return 0

    def _capture_stream(self):
        try:
            # get data via rawCaputre
            frame = self._camera.capture_array("main")
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
