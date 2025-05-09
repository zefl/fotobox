from abc import ABC, abstractmethod


class IFotocamera(ABC):
    @abstractmethod
    def connect(self, _fps: int = 0):
        raise NotImplementedError

    @abstractmethod
    def disconnect(self):
        raise NotImplementedError

    @abstractmethod
    def picture_show(self):
        raise NotImplementedError

    @abstractmethod
    def picture_take(self):
        raise NotImplementedError

    @abstractmethod
    def picture_save(self, _folder="", _file=""):
        raise NotImplementedError

    @abstractmethod
    def stream_show(self):
        raise NotImplementedError

    @abstractmethod
    def stream_start(self):
        raise NotImplementedError

    @abstractmethod
    def stream_stop(self):
        raise NotImplementedError
