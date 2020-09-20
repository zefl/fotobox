import time
import threading
import RPi.GPIO as GPIO  
import requests

class Buttons():
    stateButtonNext = 1
    stateButtonEnter = 0
    threadGPIO = None
    url = 'http://127.0.0.1:5000/button'
    statusObj = {'status': '0'}
    def __init__(self):
        print('Init Buttons')
        GPIO.setmode(GPIO.BCM)     # set up BCM GPIO numbering  
        GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)    # set GPIO25 as input (button)  
    
    def initialize(self):
        if self.threadGPIO is None:
            pass
            #self.threadGPIO = threading.Thread(target=self._threadGPIO)
            #self.threadGPIO.start()
            
    def getStateButtonNext(self):
        return self.stateButtonNext
        
    def getStateButtonEnter(self):
        returnState = self.stateButtonEnter 
        if self.stateButtonEnter == 1:
            self.stateButtonEnter = 0
        return returnState  
        
    def _threadGPIO(self):
        print("Thread Start") 
        newButtonStateNext = 0
        oldButtonStateNext = 0
        debounceTimer = 0
        flagDetected = 0
        while True:            # this will carry on until you hit CTRL+C  
            newButtonStateNext = GPIO.input(26)
            if newButtonStateNext !=  oldButtonStateNext and not(flagDetected):
                debounceTimer = 0
                flagDetected = 1
            elif newButtonStateNext !=  oldButtonStateNext and flagDetected:
                self.stateButtonEnter = 1
                print("Enter")
                debounceTimer = 0
                flagDetected = 0 #reset flag detection becaus it is processed           
            #wait for 1 sec if in this time another input is detected it is enter signal
            if debounceTimer > 2 and flagDetected: 
                print("Next")
                debounceTimer = 0
                flagDetected = 0 #reset flag detection becaus it is processed           
                self.stateButtonNext = self.stateButtonNext + 1
                if self.stateButtonNext > 4:
                    self.stateButtonNext = 1
            oldButtonStateNext = newButtonStateNext
            #button state is published by getter function
            #self.statusObj['status'] = self.stateButtonNext   
            #x = requests.post(self.url , data = self.statusObj)            
            time.sleep(0.2)         # wait 0.2 seconds  
            debounceTimer = debounceTimer + 1