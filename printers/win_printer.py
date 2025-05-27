from PIL import Image, ImageWin

import time
import win32print
import win32ui

from printers.logger import Logger

# Refere to https://www.programmersought.com/article/76882776470/
#
# Constants for GetDeviceCaps
#
#
# HORZRES / VERTRES = printable area
#
HORZRES = 8
VERTRES = 10
#
# LOGPIXELS = dots per inch
#
LOGPIXELSX = 88
LOGPIXELSY = 90
#
# PHYSICALWIDTH/HEIGHT = total area
#
PHYSICALWIDTH = 110
PHYSICALHEIGHT = 111
#
# PHYSICALOFFSETX/Y = left / top margin
#
PHYSICALOFFSETX = 112
PHYSICALOFFSETY = 113


class Printer(Logger):
    def __init__(self):
        super().__init__()

        print(f"[picInABox] Start connect to printer...")
        self.busy = False
        self.name = win32print.GetDefaultPrinter()
        self.printer_context = win32ui.CreateDC()
        self.printer_context.CreatePrinterDC(self.name)
        self.printable_area = self.printer_context.GetDeviceCaps(HORZRES), self.printer_context.GetDeviceCaps(VERTRES)
        self.printer_size = self.printer_context.GetDeviceCaps(PHYSICALWIDTH), self.printer_context.GetDeviceCaps(
            PHYSICALHEIGHT
        )
        self.printer_margins = self.printer_context.GetDeviceCaps(PHYSICALOFFSETX), self.printer_context.GetDeviceCaps(
            PHYSICALOFFSETY
        )
        print(f"[picInABox] Connected Printer: {self.name}")

    def get_printer_names(self):
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
        printer_names = []
        for printer in printers:
            printer_names.append(printer[2])
            print(f"Printer: {printer[2]}")
        pass
        return printer_names

    def reset_jobs(self):
        pass

    def check_status(self, printer):
        printer_status = win32print.GetPrinter(printer, 2)["Status"]
        if printer_status == win32print.PRINTER_STATUS_OFFLINE:
            win32print.ClosePrinter(printer)
            raise RuntimeError("Drucker offline - bitte Drucker einschalten")
        elif printer_status == win32print.PRINTER_STATUS_NO_TONER:
            win32print.ClosePrinter(printer)
            raise RuntimeError("Toner leer - bitte Toner aufüllen")
        elif printer_status == win32print.PRINTER_STATUS_PAPER_JAM:
            win32print.ClosePrinter(printer)
            raise RuntimeError("Papierstau - bitte entfernen")

    def printing(self, picture):
        printer = win32print.OpenPrinter(self.name, None)
        self.check_status(printer)

        bmp = Image.open(picture)
        bmp = bmp.rotate(90, expand=True)
        bmp = bmp.resize(self.printable_area, Image.Resampling.LANCZOS)

        self.printer_context.StartDoc(picture)
        self.printer_context.StartPage()

        dib = ImageWin.Dib(bmp)
        x1 = 0
        y1 = 0
        x2 = bmp.size[0]
        y2 = bmp.size[1]
        dib.draw(self.printer_context.GetHandleOutput(), (x1, y1, x2, y2))

        self.printer_context.EndPage()
        self.printer_context.EndDoc()

        start = time.time()
        active = True
        printer = win32print.OpenPrinter(self.name, None)
        while active:
            active = False

            jobs = win32print.EnumJobs(printer, 0, -1, 2)
            for job in jobs:
                if picture in job["pDocument"]:
                    active = True
                    status = job["Status"]
                    if status == win32print.JOB_STATUS_ERROR:
                        win32print.ClosePrinter(printer)
                        raise RuntimeError("Problem beim Drucker")
                    elif status == win32print.JOB_STATUS_DELETED:
                        win32print.ClosePrinter(printer)
                        raise RuntimeError("Druckauftrag wurde gelöscht")
                    elif status == win32print.JOB_STATUS_COMPLETE:
                        break

            if start + 30 < time.time():
                win32print.ClosePrinter(printer)
                raise RuntimeError("Zeitüberschreitung - Drucker prüfen")

        self.check_status(printer)
        win32print.ClosePrinter(printer)

    def print_picture(self, picture):
        if self.busy:
            raise RuntimeError("Letzter Druck Job noch nicht abgeschlossen")
        self.busy = True
        try:
            self.printing(picture)
            self.busy = False
        except Exception as e:
            self.reset_jobs()
            self.busy = False
            raise e
