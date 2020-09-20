#start captureing
#gphoto2 --capture-movie --stdout> fifo.mjpg &

import cv2
from os import path
from pathlib import Path
import time

while not(path.exists("fifo.mjpg")):
    pass
    
while Path('fifo.mjpg').stat().st_size == 0:
    pass

cap = cv2.VideoCapture('fifo.mjpg')

while True:
  ret, frame = cap.read()
  if ret:
    cv2.imshow('Video', frame)

  if cv2.waitKey(1) == ord('q'):
    exit(0)