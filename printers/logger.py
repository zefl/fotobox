import os
from datetime import datetime
import csv

class Logger(object):
    def __init__(self):
        self._path = "./data"
        self._logFile = f"printerLogger_{datetime.now().strftime('%Y_%m_%d')}.csv"
        if not(os.path.exists(self._path)):
            os.makedirs(self._path)
        self._fieldnames = ['picutre_name', 'time']

    def __del__(self):
        self._csvFile.close()
    
    def print_picture(self, name):
        with  open(os.path.join(self._path, self._logFile), 'a+', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self._fieldnames, delimiter=';')
            writer.writerow({'picutre_name': name, 'time':datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}) 
