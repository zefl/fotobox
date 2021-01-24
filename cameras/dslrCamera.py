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
from datetime import datetime
import time
import os

from cameras.IFotocamera import IFotocamera

#from https://github.com/pibooth/pibooth/blob/master/pibooth/camera/gphoto.py
def check_dslrCamera():
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

class Camera(IFotocamera):
    ##################################      
    #Common functions
    ##################################            
    def picture_take(self):
        if not(self.streamActive):
            self.frame = self._take_picture()
            self.frameAvalible = True
        
    def picture_show(self):
        if self.frameAvalible:
            return _convert_to_cv2(self.frame)
        else:
            return []
            
    def picture_save(self, _folder="", _file=""):
        if self.frameAvalible:
            now = datetime.now()
            picFrame = copy.copy(self.frame);
            if(_file == ""):
                _file = now.strftime('%Y_%m_%d_%H_%M_%S') 
            picName = os.path.join(_folder, _file + ".jpg")
            cv2.imwrite(picName, picFrame)  
                
    def stream_start(self):
        #check if thread is active 
        if not(self.streamActive):
            # start background frame thread
            self.thread = threading.Thread(target=self._stream_thread)
            self.streamActive = True
            self.thread.start()
    
    def stream_stop(self):
        #Stop stream, thread will be stoped
        self.streamActive = False
    
    def stream_capture(self):
        if self.frameAvalible:
            return _convert_to_cv2(self.frame)
        else:
            return []
    
    ##################################      
    #Internal function
    ##################################
    def __init__(self):
        #################
        #Variables for handling camera
        #################
        self.camera = None
        self.stream = None
        #################
        #Variables for handling streaming
        #################
        self.frameAvalible = False
        self.frame = []  # current frame is stored here
        self.streamActive = False
        self.thread = None

    def connect(self, _fps: int = 0):
        if self.camera == None:
            self._cancleGphotoPrcess()
            self.camera = gp.Camera()
            self.framerate = _fps  
            
            # camera setup
            self.camera.init()
            text = self.camera.get_summary()
            print(text)
        
    def disconnect(self):
        print("close DLSR camera")
        self.camera.exit()
    
    def _cancleGphotoPrcess(self):
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

    def _convert_to_cv2(self, _frame):
        open_cv_image = np.array(_frame)
        frame = open_cv_image[:, :, ::-1].copy()
        return frame
    
    def _take_picture(self):
        set_config_value('actions', 'viewfinder', 0)
        test = self.camera.capture(gp.GP_CAPTURE_IMAGE)
        time.sleep(0.3)  # Necessary to let the time for the camera to save the image
        print(test)


    def _capture_stream(self):  
        camFile =  self.camera.capture_preview()
        frame = Image.open(io.BytesIO(camFile.get_data_and_size()))
        return frame
        
        
    def _stream_thread(self):
        _desiredCyleTime = 1 / self.framerate #run this thread only as fast as nessecarry
        while(self.streamActive):
                self.streamActive = True
                _startTimeCature = time.time()
                #call camera to take picutre
                self.frame = self._capture_stream()                                                                 
                #check cycle time with respect to given cycel time
                _endTimeCature = time.time()
                _cyleTime = _endTimeCature - _startTimeCature
                _waitTime = _desiredCyleTime - _cyleTime
                if _waitTime > 0:
                    time.sleep(_waitTime)
                else:
                    #print("Warning: Camera cannot take picture with given fps")       
                    pass 
        self.thread = None #stop thread
        self.frameAvalible = False
        self.frame=[] #delete picture
