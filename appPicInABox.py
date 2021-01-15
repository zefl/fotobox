#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  	picInABox.py
#  	author:zefl
import os
print('Current working directory: ' + (os.getcwd()))

from flask import Flask, render_template, Response, request, redirect, url_for, jsonify, send_from_directory, send_file, make_response, g

from flask import session
from flask_session import Session

import time
import cv2
import numpy as np

import glob
import json 
import copy
import qrcode
from datetime import datetime
from io import BytesIO
from PIL import Image

from cameras.cameraRecorder import CameraRecorder

#create Flask object with __name__ --> acutal python object
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = "sdbngiusdngdsgbiursbng"

#create session to store setting data
#from https://flask-session.readthedocs.io/en/latest/
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)

modus = None
anchorsMulti = []
anchorSingle = []
streamingCamera = []
recorder = None
#-------------------------------
# Webserver Functions
# from https://flask-session.readthedocs.io/en/latest/
# from https://pythonise.com/series/learning-flask/python-before-after-request
#-------------------------------
@app.before_first_request
def before_first_request_func():

    """ 
    This function will run once before the first request to this instance of the application.
    You may want to use this function to create any databases/tables required for your app.
    """    

    print("This function will run once ")
    
    checkCamera()

    global anchorsMulti
    global anchorSingle
    global modus
    
    modus = 1
    anchorsMulti = findInserts("static/pictures/LayoutMulti.png")
    anchorSingle = findInserts("static/pictures/LayoutSingle.png")
    with open('static/default.json') as json_file:
        data = json.load(json_file)
        session['settings'] = data
        
    if not(os.path.exists("./data/orginal_pictures")):
        os.makedirs("./data/orginal_pictures")
    if not(os.path.exists("./data/pictures")):
        os.makedirs("./data/pictures")
    if not(os.path.exists("./data/videos")):
        os.makedirs("./data/videos")

#from https://www.youtube.com/watch?v=8qDdbcWmzCg
#adds settings json to each page
@app.context_processor
def context_processor():
    return dict(settings=session.get('settings'))
#-------------------------------
# Web pages
#-------------------------------
@app.route('/')
def pageStart():
    global recorder
    #start stream of picture
    recorder.start_capturing()
    return render_template('startPage.html')

@app.route('/settings')
def pageSettings():
    return render_template('settingsPage.html')

@app.route('/options')
def pageOptions():
    return render_template('chooseOption.html')

@app.route('/picture')
def pagePicture():
    global recorder
    recorder.start_capturing()
    return render_template('picturePage.html') 

#from https://gist.github.com/arusahni/9434953
@app.route('/download')
def pageDownload():
    response = make_response(render_template('downloadPage.html'))
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, private, max-age=1')
    return response
 
@app.route('/gallery')
def pageGallery():
    images = os.listdir('./data/pictures')
    images.sort(reverse=True)
    return render_template("gallery.html", imageNames=images)

@app.route('/videoFeed')
def pageVideoFeed():
    #Video streaming route. Put this in the src attribute of an img tag
    #This gets called when the image inside the html is loaded
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame') 

@app.route('/upload/<filename>')
def pageImage(filename):
    return send_from_directory("data/pictures", filename)

#-------------------------------
# Rest API functions
#-------------------------------
@app.route('/api/setting', methods = ['POST', 'GET'])
def settings():
    if request.method == 'POST':
        jsonReq = json.loads(request.data)
        if  jsonReq['key'] in session['settings']:
            session['settings'][jsonReq['key']]['value'] = jsonReq['value'] 
        return jsonify( {'return': 'done'} )
    elif request.method == 'GET':
        if 'key' in request.args:
            return session[request.args['key']]

@app.route('/api/modus', methods = ['POST', 'GET'])
def setModus():
    global modus
    if request.method == 'POST':
        if 'option' in request.args:
            modus = int(request.args['option'])
            print('Set modus: ' + str(modus))
            #redirect the webpage to the picture Page
            return redirect(url_for('pagePicture'))
    elif request.method == 'GET':
        return jsonify( {'option': modus} )
      
@app.route('/api/controlCamera', methods = ['POST', 'GET'])
def action():
    global recorder
    print(request.data)
    jsonReq = json.loads(request.data)
    if request.method == 'POST':
        if 'takePciture' in jsonReq['option']:
            recorder.take_picture('data/orginal_pictures')
        elif 'startVideo' in jsonReq['option']:
            recorder.start_recording()     
        elif 'stopVideo' in jsonReq['option']:
            recorder.stop_recording()
    return jsonify( {'return': 'done'} )
    
@app.route('/api/getQRCode', methods = ['GET']) 
def get_qrCode():
    global modus
    if request.method == 'GET':
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )   
        if modus == 1 or modus == 2:
            list_of_files = glob.glob('data/pictures/*')
            list_of_files.sort(key=os.path.getctime)
            dataSrc = list_of_files[-1]
        elif modus == 3:
            list_of_files = glob.glob('data/videos/*')
            list_of_files.sort(key=os.path.getctime) 
            dataSrc = list_of_files[-1]
        qr.add_data(dataSrc)
        qr.make(fit=True)
        #from https://stackoverflow.com/questions/26417328/how-to-serve-a-generated-qr-image-using-pythons-qrcode-on-flask
        #from https://stackoverflow.com/questions/24920728/convert-pillow-image-into-stringio
        img_buf = BytesIO()
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(img_buf)
        img_buf.seek(0)
        return send_file(img_buf, mimetype='image/jpg') 
    
@app.route('/api/renderPicture', methods = ['GET']) 
def get_picture():   
    global modus
    global anchorsMulti
    global anchorSingle
    time.sleep(2)
    if request.method == 'GET':   
        list_of_files = glob.glob('data/orginal_pictures/*')
        list_of_files.sort(key=os.path.getctime)
        pics = []
        if modus == 1:
            #append last taken image
            pics.append(Image.open(list_of_files[-1]))
            layoutSrc = "static/pictures/LayoutSingle.png"
            anchors = anchorSingle

        elif modus == 2:
            pics = []
            for index in range(1,5): 
                id = index * -1
                print(list_of_files[id])
                pics.append(Image.open(list_of_files[id]))
            layoutSrc = "static/pictures/LayoutMulti.png"
            anchors = anchorsMulti
        
        compositeImg =  Image.new('RGBA', (Image.open(layoutSrc).size), (255, 0, 0, 0))
        #from https://www.tutorialspoint.com/python_pillow/Python_pillow_merging_images.htm
        for ancor in anchors:
            print(anchors.index(ancor))
            compositeImg.paste(pics[anchors.index(ancor)].resize((ancor['width'], ancor['height'])),(ancor['x'], ancor['y']),0)
        layoutImg = Image.open(layoutSrc) 
        #from https://pythontic.com/image-processing/pillow/alpha-composite
        finalImg = Image.alpha_composite(compositeImg, layoutImg) 
        imgSrc = "data/pictures/"+ datetime.now().strftime('%Y_%m_%d_%H_%M_%S') +"_4Pics.jpg"
        finalImg = finalImg.convert('RGB')
        finalImg.save(imgSrc, "JPEG") 
        return send_file(imgSrc, mimetype='image/jpg') 

@app.route('/api/renderVideo', methods = ['GET'])
def get_video():    
    global modus
    global recorder
    time.sleep(2)
    if request.method == 'GET':
        recorder.save_recording('data/videos')
        list_of_files = glob.glob('data/videos/*')
        list_of_files.sort(key=os.path.getctime) 
        vidSrc = list_of_files[-1]
        resp = make_response(send_file(vidSrc, 'video/avi'))
        resp.headers['Content-Disposition'] = 'inline'
        return resp
#-------------------------------
# Helper functions
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

def findInserts(layoutSrc):
    img = Image.open(layoutSrc) 
    width, height = img.size
    img = img.convert("RGBA")
    imgData = list(img.getdata())
    imageLines = []
    oldTransprancy = 255
    for index, item in enumerate(imgData):
        #check for edge in transprancy from filled (255) to none filled (0)
        if item[3] < 10 and item[3] != oldTransprancy:
            ancor = {'x':0, 'y':0, 'width':0, 'height':0}
            ancor['y'] = int(index / width)
            ancor['x'] = index % width
            loopIndex = index
            #search for end of x
            while imgData[loopIndex][3] == item[3]:
                loopIndex += 1
            #search for end of y
            ancor['width'] = loopIndex - index;
            loopIndex = index
            while imgData[loopIndex][3] == item[3]:
                loopIndex += width
            ancor['height'] = int(loopIndex / width) - ancor['y'];
            imageLines.append(ancor)
        oldTransprancy = item[3]
    
    def takeX(elem):  
        return elem['x']
    
    #sort by x values to get the lines via the same x value
    imageLines.sort(key=takeX)
    lastAncor = imageLines[0]
    
    imageAncors = []
    #check first item
    if(imageLines[0]['height'] > 10):
        imageAncors.append(imageLines[0])
    for index, item in enumerate(imageLines):
        #get last page
        if lastAncor['height'] == 1:
            #only if there is a big enough space
            if(item['height'] > 10):
                imageAncors.append(item)
        lastAncor = item
    return imageAncors

def checkCamera():
    from cameras.webcam import cv_camera_connected
    from cameras.dslrCamera import dsl_camera_connected
    from cameras.piCamera import pi_camera_connected
    
    global recorder  
    global streamingCamera
    #########################
    #Select which camera driver to use
    #########################
    if cv_camera_connected():
        print('Found DSLR camera')
        from cameras.dslrCamera import Camera
        streamingCamera.append(Camera())
    if pi_camera_connected():
        print('Found pi camera')
        from cameras.piCamera import Camera
        streamingCamera.append(Camera())
    if cv_camera_connected():
        print('Found webcam camera')
        from cameras.webcam import Camera
        streamingCamera.append(Camera())
    
    if streamingCamera == None:
        raise ValueError('No Camera found') 
    
    mainCamera = streamingCamera[0]
    mainCamera.initialize('capture_stream', 30)
    recorder = CameraRecorder(mainCamera)

if __name__ == '__main__':
    print('Start application')
    app.run(host='0.0.0.0', port =5000, debug=True, threaded=True)
