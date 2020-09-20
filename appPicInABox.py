#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  	picInABox.py
#  	author:zefl

from flask import Flask, render_template, Response, request, redirect, url_for, jsonify, send_from_directory


from imageHandler import processImage
import time
import cv2
import numpy as np
import os


#from gpioRecorder import Buttons #todo remove or try to make it optional

#create Flask object with __name__ --> acutal python object
app = Flask(__name__)
#buttons = Buttons()
#buttons.initialize()
procImage = processImage(15)
modus = 1
#-------------------------------
# Web pages
#-------------------------------
@app.route('/',methods = ['GET'])
def startPage():
    return render_template('startPage.html')

@app.route('/options')
def optionsPage():
    return render_template('chooseOption.html')

@app.route('/kameraOption/<int:option>', methods = ['POST'])
def kamera(option):
    print('KameraOption: ' + str(option))
    global modus
    if request.method == 'POST':
        if option == 1:
            modus = 1
            return redirect(url_for('picturePage')) #if this is done directly via button in form
        elif option == 2:
            modus = 2
            return redirect(url_for('picturePage'))
        elif option == 3:
            modus = 3
            return redirect(url_for('picturePage'))
    else:
        return redirect(url_for(''))

@app.route('/button', methods = ['POST', 'GET'])
def gpio():
    global modus
    if request.method == 'POST':
        if(request.values['status']):
            buttonState = request.values['status']
        return "Okay"
    elif request.method == 'GET':
        #modus = buttons.getStateButtonNext()
        modus = 0
        return jsonify( {'statusNext': modus, 'statusEnter': modus} )

@app.route('/picture')
def picturePage():
    procImage.reset()
    procImage.setModus(modus) #todo refactor to modus
    return render_template('picturePage.html')
    
@app.route('/video_feed')
def video_feed():
    #Video streaming route. Put this in the src attribute of an img tag
    #This gets called when the image inside the html is loaded
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/upload/<filename>')
def send_image(filename):
    return send_from_directory("pictures", filename)

@app.route('/gallery')
def get_gallery():
    image_names = os.listdir('./pictures')
    image_names.sort(reverse=True)
    return render_template("gallery.html", image_names=image_names)
#-------------------------------
# Web functions
#-------------------------------
def create_blank(width, height, rgb_color=(0, 0, 0)):
    """Create new image(numpy array) filled with certain color in RGB"""
    # Create black blank image
    image = np.zeros((height, width, 3), np.uint8)

    # Since OpenCV uses BGR, convert the color first
    color = tuple(reversed(rgb_color))
    # Fill image with color
    image[:] = color

    return image

def gen():
    """Video streaming generator function."""
    #ret, blankImage = cv2.imencode('.jpg',create_blank(200,400))
    #blankBytes = blankImage.tobytes()
    #yield (b'--frame\r\n'
    #        b'Content-Type: image/jpeg\r\n\r\n' + blankBytes + b'\r\n')
    while True:
        start = time.time()
        frame = procImage.processFrame()
            
        if len(frame) > 0:
            ret, frameJPG = cv2.imencode('.jpg', frame)
            frameShow  = frameJPG.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frameShow + b'\r\n')
        processTime = (time.time() - start)
        waitTime = 1 / procImage.getTicks1Sec() - processTime
        #print(waitTime)
        #print("Video Feed Process Time: " + str(processTime))
        if waitTime > 0:
            time.sleep(waitTime)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port =5000, debug=True, threaded=True)
