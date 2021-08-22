#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  	picInABox.py
#  	author:zefl
import os
import sys
print('Current working directory is: ' + (os.getcwd()))

from flask import Flask, render_template, Response, request, redirect, url_for, jsonify, send_from_directory, send_file, make_response, g

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

from cameras.IFotocamera import IFotocamera
from cameras.IVideocamera import IVideocamera

import faulthandler; faulthandler.enable()

#create Flask object with __name__ --> acutal python object
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = "sdbngiusdngdsgbiursbng"

#create session to store setting data
#from https://flask-session.readthedocs.io/en/latest/
#do not use session better to use global var
#SESSION_TYPE = 'filesystem'
#app.config.from_object(__name__)
#Session(app)

g_modus = None
g_anchorsMulti = []
g_anchorSingle = []
g_settings = None

class cameraContainer():
    def __init__(self):
        self.previewCamera = None
        self.fotoCamera = None
        self.videoCamera = None
        self.timelapsCamera = None
#holds active camera selection
g_activeCamera = cameraContainer()
#Holds list of available g_cameras
g_cameras = []

g_frame = []

g_init = False

#-------------------------------
# Webserver Functions
# from https://flask-session.readthedocs.io/en/latest/
# from https://pythonise.com/series/learning-flask/python-before-after-request
# -------------------------------
@app.before_first_request
def before_first_request_func():

    """ 
    This function will run once before the first request to this instance of the application.
    You may want to use this function to create any databases/tables required for your app.
    """    

    print("This function will run once ")
    
    checkCamera()

    global g_anchorsMulti
    global g_anchorSingle
    global g_modus
    global g_settings
    global g_init
    
    if g_init == False:
        g_init = True
        g_modus = 1
        g_anchorsMulti = findInserts("static/pictures/LayoutMulti.png")
        g_anchorSingle = findInserts("static/pictures/LayoutSingle.png")
        with open('static/default.json') as json_file:
            data = json.load(json_file)
            g_settings = data
            
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
    global g_settings
    return dict(settings=g_settings)
#-------------------------------
# Web pages
#-------------------------------
@app.route('/')
def pageStart():
    return render_template('startPage.html')

@app.route('/settings')
def pageSettings():
    return render_template('settingsPage.html')

@app.route('/options')
def pageOptions():
    return render_template('chooseOption.html')

@app.route('/picture')
def pagePicture():
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
    global g_activeCamera
    g_activeCamera.previewCamera.stream_start() #start preview stream
    #Video streaming route. Put this in the src attribute of an img tag
    #This gets called when the image inside the html is loaded
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame') 

@app.route('/upload/<filename>')
def pageImage(filename):
    return send_from_directory("data/pictures", filename)

@app.route('/timelaps')
def timelaps():
    return render_template("timelaps.html", directory="data/timelaps")

#-------------------------------
# Rest API functions
#-------------------------------
@app.route('/api/setting', methods = ['POST', 'GET'])
def settings():
    global g_activeCamera  
    global g_cameras
    global g_settings
    if request.method == 'POST':
        jsonReq = json.loads(request.data)
        if  jsonReq['key'] in g_settings:
            newValue = jsonReq['value'] 
            if g_settings[jsonReq['key']]['min'] <= int(newValue) and int(newValue) <= g_settings[jsonReq['key']]['max']:
                if(jsonReq['key'] == 'camera'):
                    newCamera = g_cameras[int(jsonReq['value'])]
                    if newCamera != None:
                        #stop old stream
                        g_activeCamera.timelapsCamera.recording_stop()
                        g_activeCamera.previewCamera.stream_stop()
                        #load new camera
                        g_activeCamera.previewCamera = newCamera.previewCamera
                        g_activeCamera.previewCamera.stream_start()
                    else:
                        #camera not active
                        return jsonify( {'return': 'error'} )
                elif(jsonReq['key'] == 'timelaps'):
                    if int(jsonReq['value']):
                        g_activeCamera.timelapsCamera.recording_start()
                    else:
                        g_activeCamera.timelapsCamera.recording_stop()    
                elif(jsonReq['key'] == 'timelapsCreate'):
                    if int(jsonReq['value']):
                        g_activeCamera.timelapsCamera.recording_save()
                        return jsonify( {'return': 'done'} ) #return okay if no error before
                g_settings[jsonReq['key']]['value'] = jsonReq['value']
                response = jsonify({'return': 'done'}, 200)
                return response #return okay if no error before
        return jsonify( {'return': 'error'} ) #default error
    elif request.method == 'GET':
        if 'key' in request.args:
            return jsonify({'value': g_settings[request.args['key']]['value']}) 
    

@app.route('/api/modus', methods = ['POST', 'GET'])
def setg_modus():
    global g_modus
    if request.method == 'POST':
        if 'option' in request.args:
            g_modus = int(request.args['option'])
            print('Set g_modus: ' + str(g_modus))
            #redirect the webpage to the picture Page
            return redirect(url_for('pagePicture'))
    elif request.method == 'GET':
        return jsonify( {'option': g_modus} )
      
@app.route('/api/controlCamera', methods = ['POST', 'GET'])
def action():
    global g_activeCamera
    print(request.data)
    jsonReq = json.loads(request.data)
    if request.method == 'POST':
        if 'takePciture' in jsonReq['option']:
            g_activeCamera.fotoCamera.picture_take()
            g_activeCamera.fotoCamera.picture_save('data/orginal_pictures')
        elif 'startVideo' in jsonReq['option']:
            g_activeCamera.videoCamera.recording_start()     
        elif 'stopVideo' in jsonReq['option']:
            g_activeCamera.videoCamera.recording_stop()
    return jsonify( {'return': 'done'} )
    
@app.route('/api/getQRCode', methods = ['GET']) 
def get_qrCode():
    global g_modus
    if request.method == 'GET':
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )   
        if g_modus == 1 or g_modus == 2:
            list_of_files = glob.glob('data/pictures/*')
            list_of_files.sort(key=os.path.getctime)
            dataSrc = list_of_files[-1]
        elif g_modus == 3:
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
    global g_modus
    global g_anchorsMulti
    global g_anchorSingle
    time.sleep(2)
    if request.method == 'GET':   
        list_of_files = glob.glob('data/orginal_pictures/*')
        list_of_files.sort(key=os.path.getctime)
        pics = []
        if g_modus == 1:
            #append last taken image
            pics.append(Image.open(list_of_files[-1]))
            layoutSrc = "static/pictures/LayoutSingle.png"
            anchors = g_anchorSingle

        elif g_modus == 2:
            pics = []
            for index in range(1,5): 
                id = index * -1
                print(list_of_files[id])
                pics.append(Image.open(list_of_files[id]))
            layoutSrc = "static/pictures/LayoutMulti.png"
            anchors = g_anchorsMulti
        
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
    global g_modus
    global g_activeCamera
    time.sleep(2)
    if request.method == 'GET':
        g_activeCamera.videoCamera.recording_save('data/videos')
        list_of_files = glob.glob('data/videos/*')
        list_of_files.sort(key=os.path.getctime) 
        vidSrc = list_of_files[-1]
        resp = make_response(send_file(vidSrc, 'video/avi'))
        resp.headers['Content-Disposition'] = 'inline'
        return resp

@app.route('/lastRawFrame', methods = ['GET'])
def lastRawFrame():
    #https://www.kite.com/python/answers/how-to-serialize-a-numpy-array-into-json-in-python
    #https://stackoverflow.com/questions/58433450/how-to-send-ndarray-response-from-flask-server-to-python-client 
    frameRaw = g_activeCamera.previewCamera.stream_show()
    if type(frameRaw) != 'NoneType' and len(frameRaw) > 0:
        return json.dumps(frameRaw.tolist())
    else:
        return None  

@app.route('/status',methods = ['GET'])
def status():
    if request.method == 'GET':
        if 'folder' in request.args:
            return json.dumps(len(os.listdir(request.args['folder'])))


@app.route('/print',methods = ['POST'])
def printing():
    jsonReq = ""
    if request.method == 'POST':
        #get contet of post
        if request.content_type == 'application/x-www-form-urlencoded':
            jsonReq = request.form.to_dict()
        else:
            jsonReq = json.loads(request.data)
        #check for picture tag
        if  jsonReq['key'] == 'picture':
                print(jsonReq['value'])
                response = jsonify({'return': 'done'}, 200)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response #return okay if no error before
        else:
            response = jsonify({'return': 'error'}, 400)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response #return okay if no error before 
#-------------------------------
# Helper functions
#-------------------------------
def gen():
    global g_activeCamera
    """Video streaming generator function."""
    _lastWakeUp = time.time()
    while True:
        time.sleep(1/25)
        frame = g_activeCamera.previewCamera.stream_show()
        if type(frame) != 'NoneType':
            if len(frame) != g_activeCamera.previewCamera.frameSize():
                ret, frameJPG = cv2.imencode('.jpg', frame)
                frameShow  = frameJPG.tobytes()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frameShow + b'\r\n')
            else:
                print("[picInABox] Corrupt Image in Video stream")
        else:
            raise RuntimeError("[picInABox] No Frametype given")

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
    from cameras.webcam import check_webcam
    from cameras.dslrCamera import check_dslrCamera
    from cameras.piCamera import check_piCamera
    from cameras.cameraRecorder import CameraRecorder
    from cameras.timeLaps import CameraTimelapss
    
    global g_cameras  
    global g_activeCamera
    #########################
    #Select which camera driver to use
    #########################
    if check_dslrCamera():
        print('Found DSLR camera')
        from cameras.dslrCamera import Camera
        dslrCameraContainer = cameraContainer()
        dslrCamera = Camera()
        dslrCamera.connect(30)
        dslrCameraContainer.fotoCamera = dslrCamera
        dslrCameraContainer.previewCamera = dslrCamera
        dslrCameraContainer.videoCamera = CameraRecorder(dslrCamera)
        dslrCameraContainer.timelapsCamera = CameraTimelapss(dslrCamera)
        g_cameras.append(dslrCameraContainer)
    else:
        g_cameras.append(None)
        
    if check_piCamera():
        print('Found pi camera')
        from cameras.piCamera import Camera
        piCameraContainer = cameraContainer()
        piCamera = Camera()
        piCamera.connect(30)
        piCameraContainer.fotoCamera = piCamera
        piCameraContainer.previewCamera = piCamera
        piCameraContainer.videoCamera = CameraRecorder(piCamera)
        piCameraContainer.timelapsCamera = CameraTimelapss(piCamera)
        g_cameras.append(piCameraContainer)
    else:
        g_cameras.append(None)
        
    if check_webcam():
        print('Found webcam camera')
        from cameras.webcam import Camera
        cvCameraContainer = cameraContainer()
        cvCamera = Camera()
        cvCamera.connect(30)
        cvCameraContainer.fotoCamera = cvCamera
        cvCameraContainer.previewCamera = cvCamera
        cvCameraContainer.videoCamera = CameraRecorder(cvCamera)
        cvCameraContainer.timelapsCamera = CameraTimelapss(cvCamera)
        g_cameras.append(cvCameraContainer)
    else:
        g_cameras.append(None)
    
    recorder = None
    
    for camera in g_cameras:
        if camera != None:
            g_activeCamera.videoCamera = camera.videoCamera
            g_activeCamera.fotoCamera = camera.fotoCamera
            g_activeCamera.previewCamera = camera.previewCamera
            g_activeCamera.timelapsCamera = camera.timelapsCamera
            #start preview camera right away
            g_activeCamera.previewCamera.stream_start()
            while(g_activeCamera.previewCamera.stream_show() == []):
                time.sleep(1)
            break

if __name__ == '__main__':
    print('Start application')
    app.run(host='0.0.0.0', port =5000, debug=True, threaded=True)
