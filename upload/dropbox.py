import dropbox
import os
import json
from upload.IUpload import IUpload

# Replace with your access token
ACCESS_TOKEN = "your_access_token_here"


class Dropbox(IUpload):
    def __init__(self):
        self._file_server = None
        self._last_upload_file_link = ""
        self._connected = False

    def Connect(self):
        if not (self._connected):
            with open("upload/login.json") as f:
                logins = json.load(f)
                if "Dropbox" in logins:
                    login = logins["Dropbox"]
                    self._file_server = dropbox.Dropbox(login["token"])
                    self._connected = True
        return self._connected

    def UploadPicture(self, picture):
        try:
            with open(picture, "rb") as f:
                name = f"/{os.path.basename(f.name)}"
                self._file_server.files_upload(f.read(), name)
                self._last_upload_file_link = self._file_server.sharing_create_shared_link_with_settings(name)
            return True
        except Exception as e:
            print(e)
            return False

    def GetLastUploadLink(self):
        return self._last_upload_file_link.url
