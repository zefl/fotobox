#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  cameraRecorder.py
#
#
#

##############
# Notes:
# - could be an timer to close thread if not needed after certain time
# self.last_access = time.time() #reset timeout so at least 30 sec of capturing
#
##############

import time
import threading
import multiprocessing as mp
import cv2
import copy
import csv
import os
import numpy as np
from datetime import datetime
from PIL import Image
import glob
import sys

# from audioRecorder import audio

from cameras.IFotocamera import IFotocamera


class CameraTimelapss:
    def __init__(self, camera: IFotocamera):
        self._camera = camera
        self._process = None
        self._mp_StopEvent = mp.Value("i", lock=False)
        self._mp_FrameQueue = mp.Queue(2)
        self._thread = None
        self._threadActive = False
        self._folder_data = "data/"
        self._picturePerMinute = 60
        self._save_percent = 0
        self._save_step = ""
        self._remaining_time = ""

    def recording_start(self):
        # if no capturing is active start is
        if self._process == None:
            """create process will be implemented by child on virtual in this context"""
            self._process = mp.Process(target=_stream_recording, args=(self._mp_StopEvent, self._mp_FrameQueue))
            self._mp_StopEvent.value = False
            self._process.start()
        if self._threadActive == False:
            # start background frame thread
            self._thread = threading.Thread(target=self._thread_recording)
            # self.thread = threading.Timer(1/self.fps, self._thread_timer_recording)
            self._thread.start()

    def recording_stop(self):
        if self._process:
            self._mp_StopEvent.value = True
            self._process.join()
            self._process = None
        self._threadActive = False

    def disconnect(self):
        self._camera.disconnect

    def image_gray(self, file):
        frame = cv2.imread(file)
        # https://pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
        image = cv2.resize(frame, (500, 500), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        return gray

    def detect_movement(self, image_1, image_2):
        # compute the absolute difference between the current frame and
        # first frame
        frameDelta = cv2.absdiff(image_1, image_2)
        thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]
        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, hierarchy = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )  # https://www.programcreek.com/python/example/86843/cv2.contourArea

        movement_detected = False
        # loop over the contours
        for c in contours:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < 50:
                continue
            else:
                movement_detected = True
                break
        return movement_detected

    def recording_save(self, folder="", file_name=""):
        if not (self._save_step == "" or self._save_step == "Rendern Fertig"):
            return

        self._save_step = "Bildgröße ermitteln"
        start_time = datetime.now()
        folder = "C:/Workspace/fotobox/fotos/timelaps_fasching/"
        # Handle Inputs
        if folder == "":
            picture_folder = os.path.join(self._folder_data, "timelaps/")
            video_folder = os.path.join(self._folder_data, "videos/")
        else:
            picture_folder = os.path.join(folder, "timelaps/")
            video_folder = os.path.join(folder, "videos/")

        # TODO check if videos exist

        if file_name == "":
            file_name = "timelaps_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        # Load files
        files = glob.glob(picture_folder + "*.jpg")
        minFrameSize = (0, 0)
        sorted(files)

        # Get min size of files
        for index, file in enumerate(files):
            try:
                self._save_percent = ((index + 1) / len(files)) * 100
                image = Image.open(file)
                minPixel = minFrameSize[0] * minFrameSize[1]
                currentPixel = image.size[0] * image.size[1]
                if minPixel == 0 or currentPixel < minPixel:
                    if currentPixel != 0:
                        minFrameSize = image.size
                elapsed_time = datetime.now() - start_time
                estimated_time = (elapsed_time / (index + 1)) * len(files)
                self._remaining_time = str(estimated_time - elapsed_time).split(".")[0]
            except:
                print(f"Unexpected error: {sys.exc_info()[0]} in {file}")

        self._save_step = "Erkennen Bewegung"
        start_time = datetime.now()

        # search for movement in picture
        movement_list = []
        for index, file in enumerate(files):
            try:
                self._save_percent = ((index + 1) / len(files)) * 100
                image = self.image_gray(file)
                image_next = self.image_gray(files[index + 1])
                motion_detected = self.detect_movement(image, image_next)
                if motion_detected:
                    movement_list.append(file)
                    movement_list.append(files[index + 1])
                elapsed_time = datetime.now() - start_time
                estimated_time = (elapsed_time / (index + 1)) * len(files)
                self._remaining_time = str(estimated_time - elapsed_time).split(".")[0]
            except:
                print(f"Unexpected error: {sys.exc_info()[0]} in {file}")

        self._save_step = "Rendern der Timelaps"
        start_time = datetime.now()

        # Prepare video format
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_file = os.path.join(video_folder, file_name + ".avi")
        fps = 20
        videoWriter = cv2.VideoWriter(video_file, fourcc, fps, minFrameSize)
        # only use movement list (removed duplicates)
        files = list(dict.fromkeys(movement_list))
        # Save list in csv
        with open(os.path.join(video_folder, file_name + ".csv"), "a+", newline="\n") as csv_file:
            wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
            wr.writerow(files)

        for index, file in enumerate(files):
            try:
                self._save_percent = ((index + 1) / len(files)) * 100
                frame = Image.open(file)
                frame = frame.resize(minFrameSize, Image.ANTIALIAS)
                image = np.array(frame)
                # Convert RGB to BGR
                image = image[:, :, ::-1].copy()
                videoWriter.write(image)
                elapsed_time = datetime.now() - start_time
                estimated_time = (elapsed_time / (index + 1)) * len(files)
                self._remaining_time = str(estimated_time - elapsed_time).split(".")[0]
            except:
                print("Error in Pricture skiped")
        videoWriter.release()
        self._save_percent = 0
        self._save_step = "Rendern Fertig"

    def status_save(self):
        return {
            "step": self._save_step,
            "percent": self._save_percent,
            "run_time": self._remaining_time,
        }

    def _thread_recording(self):
        self._camera.connect()
        self._camera.stream_start()
        self._threadActive = True
        while self._threadActive:
            time.sleep(self._picturePerMinute / 60)
            try:
                self._camera.picture_take()
            except:
                print("Error in timelaps picture take")
            self._mp_FrameQueue.put(self._camera.picture_show())
        self._thread = None


def _stream_recording(stopEvent: mp.Value, queue: mp.Queue):
    while True:
        # req = requests.get('http://127.0.0.1:5000/lastRawFrame')
        if not (queue.empty()):
            number_of_files = len(glob.glob("data/timelaps/*"))
            picName = os.path.join("data/timelaps", f"foto_{(number_of_files + 1):08}" + ".jpg")
            cv2.imwrite(picName, queue.get())
        if stopEvent.value:
            break
