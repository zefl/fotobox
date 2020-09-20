#this process the frame depending on the modus
import cv2
import copy
import time
from enum import Enum
from datetime import datetime

from cameras.cameraRecorder import CameraRecorder
#########################
#Select which camera driver to use
#########################
#from cameras.webcamRecoder import Camera
#from cameras.dslrCameras import Camera
from cameras.piCamera import Camera




class processImage():
    class enModus(Enum):
        enNormalKamera = 1
        enCollageKamera = 2
        enVideoKamera = 3
        
    class enStatus(Enum):
        enInit = 1
        enCountDownSec = 2
        enOverwritePicture = 3
        enProcessPicture = 4
        enVideoCountdown = 5
        enProcessVideo = 6
        enIdle = 7
        
    modus =  enModus.enNormalKamera.value 
    status = enStatus.enInit.value
    counterTimer = 0
    counterTimer1sec = 0
    pics = []
    picShow = None
    countDownTime = 4
    countDown = countDownTime
    recordTimeSec = 10
    recorder = None
    frame = []
  
    def __init__(self, ticks):
        ######################
        # init cameras
        ######################
        self.streamingCamera = Camera()
        #self.captureCamera = dslrCamera()
        self.recorder = CameraRecorder(self.streamingCamera)
        self.counterTimer1sec = ticks
        
    def reset(self):
        print("reset status")
        self.status = self.enStatus.enInit.value
        self.counterTimer = 0
        self.countDown = self.countDownTime
        self.pics = []
        self.recorder.start_capturing()
        
    def getTicks1Sec(self):
        return self.counterTimer1sec
        
    def setModus(self, modus):
        self.modus = modus
        
    def writeText(self, frame,text, position, size):
        fontScale = 5
        lineType = 1
        
        if size == "large":
            fontScale = 10
            lineType = 20
        elif size == "middle":
            fontScale = 5
            lineType = 10
        elif size == "small":
            fontScale = 1
            lineType = 5    

        font = cv2.FONT_HERSHEY_SIMPLEX
        textsize = cv2.getTextSize(text, font, fontScale, lineType)[0]
        
        textX = 0
        textY = 0
        if position == "center":
            # get coords based on boundary from bottom left corner
            textX = (frame.shape[1] - textsize[0]) / 2
            textY = (frame.shape[0] + textsize[1]) / 2
        
        cv2.putText(frame, 
            text, 
            (int(textX), int(textY)),
            font, 
            fontScale,
            (255, 255, 255),
            lineType)

    #debugStart = time.time()
    #debugEnd = time.time()
    #print("Debug Time: " + str(debugEnd - debugStart))

    def processFrame(self):
        text = None
        #get current frame
        newFrame = self.recorder.get_last_capture()
        
        #wait for first frame
        while len(newFrame) == 0:
             newFrame = self.recorder.get_last_capture()
        
        if len(newFrame) > 0:
            self.frame =  copy.copy(newFrame)
        
        #this is needed to build webpage onyl return current pic
        if self.status == self.enStatus.enInit.value:
            self.status = self.enStatus.enCountDownSec.value
            return self.frame
        #first check if modus is supported
        if self.modus == 1 or self.modus == 2 or self.modus == 3:
            #----------
            #status 0 --> counter
            #----------
            if self.status == self.enStatus.enCountDownSec.value:
                self.writeText(self.frame, str(self.countDown), 'center','large')
                if self.modus == self.enModus.enVideoKamera.value:
                    self.recorder.start_recording()
                if self.counterTimer > self.counterTimer1sec:
                    self.counterTimer = 0
                    self.countDown = self.countDown - 1
                    
                if self.countDown == 0:
                    self.status = self.enStatus.enOverwritePicture.value
            #----------
            #status 1 if picture handle picture if video handle video
            #----------        
            elif self.status == self.enStatus.enOverwritePicture.value:
                if self.modus == self.enModus.enNormalKamera.value or self.modus == self.enModus.enCollageKamera.value:
                    self.writeText(self.frame, "Cheese", 'center','middle')
                    if self.counterTimer > self.counterTimer1sec:
                        self.status = self.enStatus.enProcessPicture.value
                        self.counterTimer = 0 
                elif self.modus == self.enModus.enVideoKamera.value:
                    self.writeText(self.frame, "Und los gehts", 'center','small')
                    if self.counterTimer > self.counterTimer1sec:
                        self.status = self.enStatus.enVideoCountdown.value
                        self.counterTimer = 0 
            
            #----------
            #status 2 handle picture
            #----------  
            elif self.status == self.enStatus.enProcessPicture.value:
                #save current frame
                now = datetime.now()
                self.name = str(now.year) + "_" + str(now.month) + "_" + str(now.day) + "_" + str(now.hour) + "_" + str(now.minute) + "_" + str(now.second)
                if self.modus == self.enModus.enNormalKamera.value:
                    cv2.imwrite("pictures/"+ self.name +".jpg", self.frame)
                    self.picShow = copy.copy(self.frame) 
                    self.status = self.enStatus.enIdle.value
                    self.counterTimer = 0 
                elif self.modus == self.enModus.enCollageKamera.value:
                    cv2.imwrite("pictures/"+ self.name +".jpg", self.frame)
                    self.pics.append(copy.copy(self.frame))
                    if len(self.pics) < 4:
                        self.status = self.enStatus.enCountDownSec.value
                        #reset countdown for next image
                        self.countDown = 4
                        self.counterTimer = 0 
                    else: 
                        self.picShow = copy.copy(self.frame)
                        x = int(self.frame.shape[1] / 2)
                        y = int(self.frame.shape[0] / 2)
                        dsize = (x, y)
                        # resize image
                        self.picShow[0:y, 0:x] = cv2.resize(self.pics[0], dsize)
                        self.picShow[y:y+y, 0:x] = cv2.resize(self.pics[1], dsize)
                        self.picShow[0:y, x:x+x] = cv2.resize(self.pics[2], dsize)
                        self.picShow[y:y+y, x:x+x] = cv2.resize(self.pics[3], dsize)
                        cv2.imwrite("pictures/"+ self.name +"_4Pics.jpg", self.picShow)
                        self.status = self.enStatus.enIdle.value
                        self.counterTimer = 0
                        
            #----------
            #status 3 handle video countdown
            #----------        
            elif self.status == self.enStatus.enVideoCountdown.value:
                if self.counterTimer > self.counterTimer1sec * self.recordTimeSec:
                    text = "Verarbeitung"
                    self.writeText(self.frame, text, 'center','small')
                    self.status = self.enStatus.enProcessVideo.value
                    self.counterTimer = 0
                else:
                    text = "0:" + str(self.recordTimeSec - int(self.counterTimer / self.counterTimer1sec))
                    self.writeText(self.frame, text, 'center','middle')
            
            #----------
            #status 3 handle video
            #----------        
            elif self.status == self.enStatus.enProcessVideo.value:
                self.recorder.stop_recording()
                self.recorder.save_recording('videos')
                text = "Bezaubernd"
                self.picShow = copy.copy(self.frame)
                self.writeText(self.frame, text, 'center','small')    
                self.status = self.enStatus.enIdle.value
                
            #----------
            #status 128 last status return self.picShow
            #----------        
            elif self.status == self.enStatus.enIdle.value:
                #self.recorder.stop_capturing();
                return self.picShow 
                
        self.counterTimer = self.counterTimer + 1
        return self.frame;

