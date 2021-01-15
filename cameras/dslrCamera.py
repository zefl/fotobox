#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  dslrCamera.py
#  
#  
#  

try:
    import gphoto2 as gp
except ImportError:
    pass  # gphoto2 is not supported if run on windows

import io
from PIL import Image, ImageFilter
import copy
import numpy as np
import psutil
from fnmatch import fnmatchcase
import sys

from cameras.ICamera import ICamera

#from https://github.com/pibooth/pibooth/blob/master/pibooth/camera/gphoto.py
def dsl_camera_connected():
    """Return True if a camera compatible with gPhoto2 is found.
    """
    if 'gphoto2' not in sys.modules:
        return False
     
    if not gp:
        return False  # gPhoto2 is not installed
    if hasattr(gp, 'gp_camera_autodetect'):
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

class Camera(ICamera):
    def __init__(self):
        self.cancleGphotoPrcess()
        self.camera = gp.Camera()
        self.camera.init()
        text = self.camera.get_summary()
        print(text)

    def initialize(self, _modus: str, _fps: int = 0):
        pass
        
    def __del__(self):
        print("close DLSR camera")
        self.camera.exit()
    
    #from pipooth utils
    def cancleGphotoPrcess(self):
        print("Kill gphoto process")
        for proc in psutil.process_iter():
            if fnmatchcase(proc.name(), "*gphoto2*"):
                try:
                    proc.kill()
                except psutil.AccessDenied:
                    raise EnvironmentError("Can not kill '{}', root access is required. "
                                           "(kill it manually before starting pibooth)".format(proc.name()))
        
    def set_config_value(self, section, option, value):
        """Set camera configuration. This method don't send the updated
        configuration to the camera (avoid connection flooding if several
        values have to be changed)
        """
        try:
            #LOGGER.debug('Setting option %s/%s=%s', section, option, value)
            config = self.camera.get_config()
            child = config.get_child_by_name(section).get_child_by_name(option)
            if child.get_type() == gp.GP_WIDGET_RADIO:
                choices = [c for c in child.get_choices()]
            else:
                choices = None
            data_type = type(child.get_value())
            value = data_type(value)  # Cast value
            if choices and value not in choices:
                #LOGGER.warning(
                #    "Invalid value '%s' for option %s (possible choices: %s), trying to set it anyway", value, option, choices)
                print("invalid")
            child.set_value(value)
            self.camera.set_config(config)
        except gp.GPhoto2Error as ex:
            #LOGGER.error('Unsupported option %s/%s=%s (%s), configure your DSLR manually', section, option, value, ex)
            print("Error")

    def quit(self):
        gp.check_result(gp.gp_camera_exit(camera))

    def convert_to_cv2(self, _frame):
        open_cv_image = np.array(_frame)
        frame = open_cv_image[:, :, ::-1].copy()
        return frame
    
    def capture_picture(self):
        set_config_value('actions', 'viewfinder', 0)
        test = self.camera.capture(gp.GP_CAPTURE_IMAGE)
        time.sleep(0.3)  # Necessary to let the time for the camera to save the image
        print(test)


    def capture_stream(self):  
        camFile =  self.camera.capture_preview()
        frame = Image.open(io.BytesIO(camFile.get_data_and_size()))
        return frame
