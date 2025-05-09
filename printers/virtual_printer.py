from printers.logger import Logger


class VirtualPrinter(Logger):
    def __init__(self, name="default", max_pages=-1, counters=None):
        super().__init__()
        self.name = name
        self.max_pages = max_pages
        self.count = counters

    def print_picture(self, picture, copies=1):
        super().print_picture(picture)
        print(f"File '{picture}' sent to the printer")

    def log_error(self, error):
        super().log_error(error)
