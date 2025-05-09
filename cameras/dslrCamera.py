try:
    import gphoto2 as gp
except ImportError:
    pass  # gphoto2 is not supported if run on windows

import multiprocessing as mp
import io
from PIL import Image
import numpy as np
import psutil
from fnmatch import fnmatchcase
import sys
import time

from cameras.cameraBase import CameraBase
from cameras.cameraBase import stream_run


# from https://github.com/pibooth/pibooth/blob/master/pibooth/camera/gphoto.py
def check_dslrCamera():
    """Return True if a camera compatible with gPhoto2 is found."""
    if "gphoto2" not in sys.modules:
        return False

    # not sure if we need this anymore
    # try:
    #     from utils.utils import resetUsbViaName

    #     resetOkay = resetUsbViaName("Canon, Inc. EOS 700D")
    #     if not (resetOkay):
    #         return False
    # except:
    #     print("Not on linux system")

    if not gp:
        return False  # gPhoto2 is not installed

    if hasattr(gp, "gp_camera_autodetect"):
        # gPhoto2 version 2.5+
        cameras = gp.check_result(gp.gp_camera_autodetect())
    else:
        port_info_list = gp.PortInfoList()
        port_info_list.load()
        abilities_list = gp.CameraAbilitiesList()
        abilities_list.load()
        cameras = abilities_list.detect(port_info_list)

    if cameras:
        return True

    return False


class Camera(CameraBase):
    def __init__(self):
        super().__init__()

    def connect(self, _fps: int = 0):
        if self._camera == None:
            self._cancleGphotoPrcess()
            self._camera = gp.Camera()
            self._frameRate = _fps
            self._frameSize = 0  # todo get framesize from camera
            self._lastCapture = None

            # camera setup
            self._camera.init()
            # Camera does not support info
            # text = self._camera.get_summary()
            # print(f"[picInABox] Connect to dslr {text}")
            self._connected = True

    def disconnect(self):
        print("[picInABox] Disconnect dslr camera")
        if self._camera:
            self._connected = False
            self._camera.exit()
            self._camera = None

    def _cancleGphotoPrcess(self):
        for proc in psutil.process_iter():
            if fnmatchcase(proc.name(), "*gphoto2*"):
                try:
                    proc.kill()
                except psutil.AccessDenied:
                    raise EnvironmentError(
                        "Can not kill '{}', root access is required. "
                        "(kill it manually before starting pibooth)".format(proc.name())
                    )

    def set_config_value(self, section, option, value):
        """Set camera configuration. This method don't send the updated
        configuration to the camera (avoid connection flooding if several
        values have to be changed)
        """
        try:
            # LOGGER.debug('Setting option %s/%s=%s', section, option, value)
            config = self._camera.get_config()
            child = config.get_child_by_name(section).get_child_by_name(option)
            if child.get_type() == gp.GP_WIDGET_RADIO:
                choices = [c for c in child.get_choices()]
            else:
                choices = None
            data_type = type(child.get_value())
            value = data_type(value)  # Cast value
            if choices and value not in choices:
                # LOGGER.warning(
                #    "Invalid value '%s' for option %s (possible choices: %s), trying to set it anyway", value, option, choices)
                print("invalid")
            child.set_value(value)
            self._camera.set_config(config)
        except gp.GPhoto2Error as ex:
            # LOGGER.error('Unsupported option %s/%s=%s (%s), configure your DSLR manually', section, option, value, ex)
            print("Error")

    def quit(self):
        gp.check_result(gp.gp_camera_exit(self._camera))

    def frameSize(self):
        if self._frameSize:
            return self._frameSize
        else:
            return 0

    def _take_picture(self):
        # self.set_config_value('actions', 'viewfinder', 0)
        self._lastCapture = self._camera.capture(gp.GP_CAPTURE_IMAGE)
        time.sleep(0.3)  # Necessary to let the time for the camera to save the image
        None

    def _save_picture(self, pic_targert):
        if self._lastCapture:
            camera_file = self._camera.file_get(
                self._lastCapture.folder, self._lastCapture.name, gp.GP_FILE_TYPE_NORMAL
            )
            camera_file.save(pic_targert)
            self._lastCapture = None

    def _capture_stream(self):
        try:
            camFile = self._camera.capture_preview()
            file_data = camFile.get_data_and_size()
            image = Image.open(io.BytesIO(file_data))
            flipped_img = image.transpose(Image.FLIP_LEFT_RIGHT)
            frame = np.array(flipped_img)[:, :, ::-1]
            return frame
        except:
            print("[picInABox] Error in reading DSLR Camera")
            raise RuntimeError("[picInABox] Error in reading DSLR Camera")

    def _create_process(self):
        return mp.Process(
            target=_stream_runDslrCam,
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


def _stream_runDslrCam(queues, stopEvent: mp.Value, frameRate):
    camera = Camera()
    camera.connect(frameRate)
    stream_run(camera, queues, stopEvent, frameRate)
