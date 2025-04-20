from upload.IUpload import IUpload
# from mega import Mega
import json


class MegaNz(IUpload):
    def __init__(self):
        self._file_server = None
        self._last_upload_file_link = ""
        self._connected = False

    def Connect(self):
        if not (self._connected):
            with open("upload/login.json") as f:
                logins = json.load(f)
                if "MEGA" in logins:
                    login = logins["MEGA"]
                    mega = Mega()
                    self._file_server = mega.login(login["user"], login["password"])
                    self._connected = True
        return self._connected

    def UploadPicture(self, picture):
        try:
            file = self._file_server.upload(picture)
            self._last_upload_file_link = self._file_server.get_upload_link(file)
            # name = picture.split("/")[-1]
            # self._last_upload_file_link = self._file_server.export(name)
            return True
        except Exception as e:
            print(e)
            return False

    def GetLastUploadLink(self):
        return self._last_upload_file_link
