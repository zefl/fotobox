#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  ICamera.py
#  
#  
# 
from abc import ABC, abstractmethod

class ICamera(ABC):
     
    @abstractmethod    
    def initialize(self, _modus: str, _fps: int = 0):
        raise NotImplementedError
    
    @abstractmethod    
    def capture_stream(self):
        raise NotImplementedError
        
    @abstractmethod
    def convert_to_cv2(self, _frame):
        raise NotImplementedError
        
    @abstractmethod
    def capture_picture(self):
        raise NotImplementedError