#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  camera_pi.py

import copy
import cv2
from datetime import datetime
import threading
import multiprocessing as mp
import time
import os

from cameras.IFotocamera import IFotocamera


class CameraBase(IFotocamera):
    def __init__(self):
        """Variables for handling camera"""
        self._camera = None
        self._connected = False
        """Variables for static picture
        """
        self._frame = []
        self._frameAvalible = False
        """Variables for handling streaming
        """
        self._process = None
        self._thread = None
        self._mp_StopEvent = mp.Value("i", lock=False)
        """Two queues one for preview and one if during preview picture is taken"""
        self._mp_FrameQueues = [mp.Queue(2), mp.Queue(2)]
        self._frame = []
        self._frameRate = 30

    """Interface functions
    """

    def picture_take(self):
        """If subporcess is active use frame form this one to take picture"""
        if self._process:
            if self._process.is_alive():
                self._frame = self._mp_FrameQueues[1].get()
                self._frameAvalible = True
        elif self._thread:
            if self._thread.is_alive():
                # self._frame = self._mp_FrameQueues[1].get()
                self._frameAvalible = True
        else:
            """Check if camera is still connect"""
            if self._camera == None:
                self.connect(self._frameRate)
            self._take_picture()

    def picture_show(self):
        if self._frameAvalible:
            self._frameAvalible = False
            return self._frame
        else:
            return []

    def picture_save(self, folder="", file=""):
        now = datetime.now()
        picFrame = copy.copy(self._frame)
        if file == "":
            """create new filename if no filename was given"""
            file = now.strftime("%Y_%m_%d_%H_%M_%S")
        picName = os.path.join(folder, file + ".jpg")
        if self._frameAvalible:
            cv2.imwrite(picName, picFrame)
        else:
            self._save_picture(picName)

    def thread_start(self):
        if self._process:
            print("Stream process already up in running")
        else:
            if self._thread == None:
                self._thread = threading.Thread(name="CameraStreamThread", target=self._thread_run)
                self._mp_StopEvent.value = False
                self._thread.start()

    def thread_stop(self):
        self._mp_StopEvent.value = True

    def stream_start(self):
        self.thread_start()
        return
        """check if thread is active"""
        if self._process == None:
            self.disconnect()
            """create process will be implemented by child on virtual in this context"""
            self._process = self._create_process()
            self._mp_StopEvent.value = False
            self._process.start()

    def stream_stop(self):
        self.thread_stop()
        while self._thread != None:
            # Wait for thread to end
            pass
        return
        # Stop stream, thread will be stoped
        self._mp_StopEvent.value = True
        self._process.join()
        self._process = None
        self.connect()

    def stream_show(self):
        if not (self._mp_FrameQueues[0].empty()):
            return self._mp_FrameQueues[0].get()
        elif self._thread:
            if self._thread.is_alive():
                return self._frame
            else:
                return []
        else:
            return []

    """Specific Functions
    """

    def connect(self, fps: int = 0):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def frameSize(self):
        raise NotImplementedError

    def _take_picture(self):
        raise NotImplementedError

    def _save_picture(self, pic_targert):
        raise NotImplementedError

    def _capture_stream(self):
        raise NotImplementedError

    def _create_process(self):
        raise NotImplementedError

    def _thread_run(self):
        desiredCyleTime = 1 / self._frameRate  # run this thread only as fast as nessecarry
        nextFrameTime = 0
        while True:
            if (nextFrameTime > 0)  and (time.time() < nextFrameTime):
                time.sleep(nextFrameTime - time.time())
            nextFrameTime = time.time() + desiredCyleTime
            # call camera to take picutre
            if self._connected:
                try:
                    self._frame = self._capture_stream()
                except:
                    print("[picInABox] Error in camera reading")
                    self.disconnect()
                    self.connect(self._frameRate)
            if self._mp_StopEvent.value:
                break
        self._mp_StopEvent.value = False
        self._thread = None  # stop thread


"""Global Function which is called by subprocess

:param queue: queue of parent class which holds frame data
:param stopEvent : Eventflag which causes the process to stop
:param frameRate : static framerate on which the camera should work
:param streamCamera : specific instansiation of child class
"""


def stream_run(streamCamera: CameraBase, queues, stopEvent: mp.Value, frameRate: int):
    streamCamera.connect(frameRate)
    desiredCyleTime = 1 / frameRate  # run this thread only as fast as nessecarry
    nextFrameTime = 0
    while True:
        currentTime = time.time()
        if currentTime > nextFrameTime:
            nextFrameTime = currentTime + desiredCyleTime
            # call camera to take picutre
            for queue in queues:
                if not (queue.full()):
                    frame = streamCamera._capture_stream()
                    queue.put(frame)
        if stopEvent.value:
            break
    stopEvent.value = False
    queue.close()  # check if i need to
    streamCamera.disconnect()
