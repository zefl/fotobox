#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  ICamera.py
#
#
#
from abc import ABC, abstractmethod


class IVideocamera(ABC):
    @abstractmethod
    def recording_start(self):
        raise NotImplementedError

    @abstractmethod
    def recording_stop(self):
        raise NotImplementedError

    @abstractmethod
    def recording_save(self, _folder="", _file=""):
        raise NotImplementedError
