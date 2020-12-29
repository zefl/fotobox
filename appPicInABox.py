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
import qrcode
from datetime import datetime
from io import BytesIO
from PIL import Image

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
def pageStart():
    global recorder
    #start stream of picture
    recorder.start_capturing();
    return render_template('startPage.html')

@app.route('/options')
def pageOptions():
    return render_template('chooseOption.html')

@app.route('/picture')
def pagePicture():
    global recorder
    recorder.start_capturing()
    return render_template('picturePage.html') 

@app.route('/download')
def pageDownload():
    return render_template('downloadPage.html') 
 
@app.route('/videoFeed')
def pageVideoFeed():
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
            return redirect(url_for('pagePicture'))
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
    return jsonify( {'return': 'done'} )
    
@app.route('/getQRCode', methods = ['GET']) 
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
            list_of_files = glob.glob('pictures/*')
            list_of_files.sort(key=os.path.getctime)
            dataSrc = list_of_files[-1]
        elif modus == 3:
            list_of_files = glob.glob('videos/*')
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
                id = index * -1
                print(list_of_files[id])
                pics.append(Image.open(list_of_files[id]))
            layoutSrc = "static/pictures/Layout4.png"
            ancors = findInserts(layoutSrc)
            compositeImg =  Image.new('RGBA', (Image.open(layoutSrc).size), (255, 0, 0, 0))
            #from https://www.tutorialspoint.com/python_pillow/Python_pillow_merging_images.htm
            for ancor in ancors:
                print(ancors.index(ancor))
                compositeImg.paste(pics[ancors.index(ancor)].resize((ancor['width'], ancor['height'])),(ancor['x'], ancor['y']),0)
            layoutImg = Image.open(layoutSrc) 
            #from https://pythontic.com/image-processing/pillow/alpha-composite
            finalImg = Image.alpha_composite(compositeImg, layoutImg) 
            imgSrc = "pictures/"+ datetime.now().strftime('%Y_%m_%d_%H_%M_%S') +"_4Pics.jpg"
            finalImg = finalImg.convert('RGB')
            finalImg.save(imgSrc, "JPEG") 
        return send_file(imgSrc, mimetype='image/jpg') 

@app.route('/getVideo', methods = ['GET'])
def get_video():    
    global modus
    time.sleep(2)
    if request.method == 'GET':
        recorder.save_recording('videos')
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
    print(imageAncors)
    return imageAncors

if __name__ == '__main__':
    app.run(host='0.0.0.0', port =5000, debug=True, threaded=True)
