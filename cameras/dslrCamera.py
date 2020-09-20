#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  dslrCamera.py
#  
#  
#  

import gphoto2 as gp
import io
from PIL import Image, ImageFilter
import copy
import numpy as np
import psutil
from fnmatch import fnmatchcase

class dslrCamera(ICamera):
    def __init__(self):
        self.cancleGphotoPrcess()
        self.camera = gp.check_result(gp.gp_camera_new())
        gp.check_result(gp.gp_camera_init(self.camera))
        text = gp.check_result(gp.gp_camera_get_summary(self.camera))
        print(text)
        
    def __del__(self):
        print("close DLSR camera")
        self.camera.exit()
    
    #from pipooth utils
    def cancleGphotoPrcess(self):
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

    def initialize(self):

    def convert_to_cv2(self, _frame):
        open_cv_image = np.array(_frame)
        frame = open_cv_image[:, :, ::-1].copy()
        return frame
    
    def capture(self):
        set_config_value('actions', 'viewfinder', 0)
        test = self.camera.capture(gp.GP_CAPTURE_IMAGE)
        time.sleep(0.3)  # Necessary to let the time for the camera to save the image
        print(test)


    def capture_stream(self):  
        camFile =  self.camera.capture_preview()
        frame = Image.open(io.BytesIO(camFile.get_data_and_size()))
        return frame
