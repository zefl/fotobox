#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  cameraRecorder.py
#  
#  
# 

##############
#Notes:
#- could be an timer to close thread if not needed after certain time
# self.last_access = time.time() #reset timeout so at least 30 sec of capturing
#
############## 

import time
import threading
import cv2
import copy
import os
import ffmpeg
from datetime import datetime
#from audioRecorder import audio
from cameras.ICamera import ICamera


class CameraRecorder(object):
    
    def __init__(self, _camera: ICamera, _audioRec=None):
        self.camera = _camera
        #################
        #Variables for handling streaming
        #################
        self.frame = []  # current frame is stored here
        self.captureStreamActive = False
        self.captureStreamStop = False
        self.thread = None
        #################
        # Varibales for recording
        #################
        self.startRecording = False
        self.stopRecording = False
        self.recordingActive = False
        self.recordFrames = []
        #################
        #Save fps_recorded
        #################
        self.fps = 30
        self.fpsRecorded = 0
        #################
        # Optinal audio Recorder
        #################
        self.audioRecorder = _audioRec
        
        self.frameAvalible = False
    
    def start_capturing(self):
        #check if thread is active 
        if not(self.captureStreamActive):
            # start background frame thread
            self.thread = threading.Thread(target=self._thread_capturing)
            self.thread.start()

    def stop_capturing(self):
        self.captureStreamStop = True
        
    def start_recording(self):
        #reset frame buffer
        self.recordFrames = []
        #if no capturing is active start is
        if not(self.captureStreamActive):
            self.start_capturing()
        self.startRecording = True
        
    def stop_recording(self):
        self.stopRecording = True
            
    def save_recording(self, _folder="", _file=""):
        if self.recordFrames:
            #wait for recording to finish
            while self.recordingActive:
                time.sleep(0.1)  
                #To Do Timeout and rais error
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            now = datetime.now()
            #handle video data
            timestamp = now.strftime('%Y_%m_%d_%H_%M_%S') 
            video_file = os.path.join(_folder, "vid_" + timestamp +'.avi' )  
            frame = self.camera.convert_to_cv2(self.recordFrames[0])                                             
            videoWriter = cv2.VideoWriter(video_file, fourcc, self.fpsRecorded, (frame.shape[1],frame.shape[0])) 
            for frame in self.recordFrames:
                videoWriter.write(self.camera.convert_to_cv2(frame))
            videoWriter.release()
            #handle audio data
            if self.audioRecorder:
                volume_file = os.path.join(_folder, "vol_" + timestamp + ".wav")
                self.audioRecorder.save(volume_file)
                
                #merge video and audio data
                input_video = ffmpeg.input(video_file)
                input_audio  = ffmpeg.input(volume_file)
                movie_file = "mov_" + timestamp + ".mp4"
                (
                    ffmpeg
                    .concat(input_video, input_audio, v=1, a=1)
                    .output(os.path.join(_folder,movie_file))
                    .run(overwrite_output=True)
                )
            else:
                movie_file = "mov_" + timestamp + ".mp4"
                (
                    ffmpeg
                    .input(video_file)
                    .output(os.path.join(_folder,movie_file))
                    .run()
                )
            os.remove(video_file) 
            self.recordFrames = []

    def get_last_capture(self):
        if self.frameAvalible:
            return self.camera.convert_to_cv2(self.frame)
        else:
            return []
    

    def take_picture(self, _folder="", _file=""):
        #if streaming is active take current picture
        if self.captureStreamActive:
            now = datetime.now()
            picFrame = copy.copy(self.get_last_capture());
            if(_file == ""):
                _file = now.strftime('%Y_%m_%d_%H_%M_%S') 
            picName = os.path.join(_folder, _file + ".jpg")
            cv2.imwrite(picName, picFrame)
       #return error if not init
                      
    def _thread_take_picture(self):
        self.camera.initialize(self.fps)
        self.camera.capture_picture()
            
    def _thread_capturing(self):
        self.captureStreamActive = True
        self.camera.initialize('capture_stream', self.fps)
        _desiredCyleTime = 1 / self.fps #run this thread only as fast as nessecarry
        while(True):
                _startTimeCature = time.time()
                #call camera to take picutre
                self.frame = self.camera.capture_stream()
                self.frameAvalible = True                    
                if self.startRecording and not(self.recordingActive):
                    countFrames = 0
                    startTimeRec = time.time()
                    self.startRecording = False
                    self.recordingActive = True
                    if self.audioRecorder:
                        self.audioRecorder.start()
                        
                if self.recordingActive:
                    countFrames += 1
                    self.recordFrames.append(copy.copy(self.frame))
                    
                if self.stopRecording and self.recordingActive:
                    finishTimeRec = time.time()
                    self.fpsRecorded = countFrames / (finishTimeRec-startTimeRec)
                    print('Recorded %d images in %d seconds at %.2ffps' % (countFrames, finishTimeRec-startTimeRec, self.fpsRecorded))   
                    self.stopRecording = False
                    self.recordingActive = False
                    self.startRecording = False #reset if someone wanted to start stream while running
                    if self.audioRecorder:
                        self.audioRecorder.stop()
                        
                if self.captureStreamStop:
                    break #stop thread
                    
                #check cycle time with respect to given cycel time
                _endTimeCature = time.time()
                _cyleTime = _endTimeCature - _startTimeCature
                _waitTime = _desiredCyleTime - _cyleTime
                if _waitTime > 0:
                    time.sleep(_waitTime)
                else:
                    print("Warning: Camera cannot take picture with given fps")                   
         
        self.frame=[] #delete picture
        self.thread = None
        self.captureStreamActive = False
        self.captureStreamStop = False
        self.frameAvalible = False