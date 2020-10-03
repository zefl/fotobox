#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  	picInABox.py
#  	author:zefl

from flask import Flask, render_template, Response, request, redirect, url_for, jsonify, send_from_directory, send_file, make_response


import time
import cv2
import numpy as np
import os
import glob
import json 
import copy
from datetime import datetime

from cameras.cameraRecorder import CameraRecorder
#########################
#Select which camera driver to use
#########################
from cameras.webcam import Camera
#from cameras.dslrCameras import Camera
#from cameras.piCamera import Camera

#create Flask object with __name__ --> acutal python object
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
modus = 1

streamingCamera = Camera()
streamingCamera.initialize('capture_stream', 30)
recorder = CameraRecorder(streamingCamera)
#-------------------------------
# Web pages
#-------------------------------
@app.route('/')
def startPage():
    global recorder
    #start stream of picture
    recorder.start_capturing();
    return render_template('startPage.html')

@app.route('/options')
def optionsPage():
    return render_template('chooseOption.html')

@app.route('/picture')
def picturePage():
    global recorder
    recorder.start_capturing()
    return render_template('picturePage.html') 

@app.route('/download')
def downloadPage():
    return render_template('downloadPage.html') 
 
@app.route('/video_feed')
def video_feed():
    #Video streaming route. Put this in the src attribute of an img tag
    #This gets called when the image inside the html is loaded
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame') 
 
#-------------------------------
# Rest API functions
#-------------------------------
@app.route('/modus', methods = ['POST', 'GET'])
def modus():
    global modus
    if request.method == 'POST':
        if 'option' in request.args:
            modus = int(request.args['option'])
            print('Set modus: ' + str(modus))
            #redirect the webpage to the picture Page
            return redirect(url_for('picturePage'))
    elif request.method == 'GET':
        return jsonify( {'option': modus} )
  
@app.route('/upload/<filename>')
def send_image(filename):
    return send_from_directory("pictures", filename)

@app.route('/gallery')
def get_gallery():
    image_names = os.listdir('./pictures')
    image_names.sort(reverse=True)
    return render_template("gallery.html", image_names=image_names)
    
@app.route('/takePicture', methods = ['POST', 'GET'])
def action():
    global recorder
    print(request.data)
    jsonReq = json.loads(request.data)
    if request.method == 'POST':
        if 'takePciture' in jsonReq['option']:
            recorder.take_picture('pictures')
        elif 'startVideo' in jsonReq['option']:
            recorder.start_recording()     
        elif 'stopVideo' in jsonReq['option']:
            recorder.stop_recording()
            recorder.save_recording('videos')
    return jsonify( {'return': 'done'} )

@app.route('/getPicture', methods = ['GET']) 
def get_picture():   
    global modus
    time.sleep(2)
    if request.method == 'GET':   
        list_of_files = glob.glob('pictures/*')
        list_of_files.sort(key=os.path.getctime)
        if modus == 1:
            imgSrc = list_of_files[-1]
        elif modus == 2:
            pics = []
            for index in range(1,5): 
                id = (index + 1) * -1
                pics.append(cv2.imread(list_of_files[id]))
                print(len(pics))
            x = int(pics[0].shape[1] / 2)
            y = int(pics[0].shape[0] / 2)
            dsize = (x, y)
            # resize image
            picShow = copy.copy(pics[0])
            picShow[0:y, 0:x] = cv2.resize(pics[0], dsize)
            picShow[y:y+y, 0:x] = cv2.resize(pics[1], dsize)
            picShow[0:y, x:x+x] = cv2.resize(pics[2], dsize)
            picShow[y:y+y, x:x+x] = cv2.resize(pics[3], dsize)
            imgSrc = "pictures/"+ datetime.now().strftime('%Y_%m_%d_%H_%M_%S') +"_4Pics.jpg"
            cv2.imwrite(imgSrc, picShow)
                    
        return send_file(imgSrc, mimetype='image/jpg') 

@app.route('/getVideo', methods = ['GET'])
def get_video():    
    global modus
    time.sleep(2)
    if request.method == 'GET':   
        list_of_files = glob.glob('videos/*')
        list_of_files.sort(key=os.path.getctime) 
        vidSrc = list_of_files[-1]
        print(vidSrc)
        resp = make_response(send_file(vidSrc, 'video/avi'))
        resp.headers['Content-Disposition'] = 'inline'
        return resp
#-------------------------------
# Web functions
#-------------------------------
def gen():
    global recorder
    """Video streaming generator function."""
    while True:
        start = time.time()
        frame = recorder.get_last_capture()
            
        if len(frame) > 0:
            ret, frameJPG = cv2.imencode('.jpg', frame)
            frameShow  = frameJPG.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frameShow + b'\r\n')
        processTime = (time.time() - start)
        waitTime = 1 / 30 - processTime
        #print(waitTime)
        #print("Video Feed Process Time: " + str(processTime))
        if waitTime > 0:
            time.sleep(waitTime)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port =5000, debug=True, threaded=True)
