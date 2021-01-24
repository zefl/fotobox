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

from cameras.IVideocamera import IVideocamera
from cameras.IFotocamera import IFotocamera


class CameraRecorder(IVideocamera):
    
    def __init__(self, _camera: IFotocamera, _audioRec=None):
        self.camera = _camera
        self.thread = None
        self.threadActive = False
        #################
        # Varibales for recording
        #################
        self.startRecording = False
        self.stopRecording = False
        self.recordingActive = False
        self.recordFrames = []
        self.startTimeRec = None
        self.finishTimeRec = None
        #################
        #Save fps_recorded
        #################
        self.fps = 30 #in current setup we have two threads with leads to ~15 less framrate
        self.fpsRecorded = 0
        #################
        # Optinal audio Recorder
        #################
        self.audioRecorder = _audioRec
        
    def recording_start(self):
        #if no capturing is active start is
        if self.threadActive == False:
            # start background frame thread
            self.thread = threading.Thread(target=self._thread_recording)
            #self.thread = threading.Timer(1/self.fps, self._thread_timer_recording)
            self.thread.start()
        self.startRecording = True
        
    def recording_stop(self):
        self.stopRecording = True
            
    def recording_save(self, _folder="", _file=""):
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
            frame = self.recordFrames[0]                                             
            videoWriter = cv2.VideoWriter(video_file, fourcc, self.fpsRecorded, (frame.shape[1],frame.shape[0])) 
            for frame in self.recordFrames:
                videoWriter.write(frame)
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

    def _thread_recording(self):
        _desiredCyleTime = 1 / self.fps #run this thread only as fast as nessecarry
        self.camera.connect()
        self.camera.stream_start()
        self.threadActive = True
        self.recordFrames = []
        _lastWakeUp = time.time()
        while(self.threadActive):
            _currentTime = time.time()
            if(_currentTime - _lastWakeUp > _desiredCyleTime):
                _lastWakeUp = time.time()
                if self.startRecording and not(self.recordingActive):
                    self.startTimeRec = _lastWakeUp
                    self.startRecording = False
                    self.recordingActive = True
                    if self.audioRecorder:
                        self.audioRecorder.start()
                        
                if self.recordingActive:
                    #call camera to take picutre
                    frame = self.camera.stream_capture()      
                    self.recordFrames.append(copy.copy(frame))
                    
                if self.stopRecording and self.recordingActive:
                    self.finishTimeRec = _lastWakeUp
                    countFrames = len(self.recordFrames)
                    self.fpsRecorded = countFrames / (self.finishTimeRec-self.startTimeRec)
                    print('Recorded %d images in %d seconds at %.2ffps' % (countFrames, self.finishTimeRec-self.startTimeRec, self.fpsRecorded))   
                    self.stopRecording = False
                    self.recordingActive = False
                    self.startRecording = False #reset if someone wanted to start stream while running
                    if self.audioRecorder:
                        self.audioRecorder.stop()
                    self.threadActive = False #Stop thread
        self.thread = None