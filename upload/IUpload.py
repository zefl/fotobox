from abc import ABC, abstractmethod

class IUpload(ABC):
    @abstractmethod    
    def Connect(self):
        raise NotImplementedError

    @abstractmethod    
    def UploadPicture(self, picture):
        raise NotImplementedError

    @abstractmethod    
    def GetLastUploadLink(self):
        raise NotImplementedError