from os import error
import queue


class Error:
    def __init__(self):
        self._error_queue = queue.Queue(20)
        self._uuid = 1

    def put(self, error: dict(status=None)):
        if error["status"] != "Okay":
            if not ("description" in error):
                error["description"] = "Ungültiger Fehler"
            self.add(error["description"], error["status"])

    def add(self, description, status):
        new_error = {}
        self._uuid = +1
        new_error["uuid"] = self._uuid
        if status == "Info":
            new_error["status"] = status
        else:
            new_error["status"] = "Error"
        new_error["description"] = description
        self._error_queue.put(new_error)

    def get(self):
        if not (self._error_queue.empty()):
            return self._error_queue.get()
        else:
            return None
