# -*- coding: utf-8 -*-

import cups
import tempfile
import os.path as osp
import time

from PIL import Image

from printers.logger import Logger

PAPER_FORMATS = {
    "2x6": (2, 6),  # 2x6 pouces - 5x15 cm - 51x152 mm
    "3,5x5": (3.5, 5),  # 3,5x5 pouces - 9x13 cm - 89x127 mm
    "4x6": (4, 6),  # 4x6 pouces - 10x15 cm - 101x152 mm
    "5x7": (5, 7),  # 5x7 pouces - 13x18 cm - 127x178 mm
    "6x8": (6, 8),  # 6x8 pouces - 15x20 cm - 152x203 mm
    "6x9": (6, 9),  # 6x9 pouces - 15x23 cm - 152x229 mm
}

"""
use cups to install the printer via http://localhost:631/
set options via printers -> maintenance->setDefaultOptions
Bug Fixes see
https://www.voss.earth/2018/08/31/kurztipp-canon-selphy-wlan-drucker-cp910-oder-cp1300-unter-linux-cups-verwenden/
https://askubuntu.com/questions/1180926/connect-canon-selphy-cp1200-via-usb-ubuntu-19-04
"""


class Printer(Logger):
    def __init__(self, name="default", max_pages=-1, counters=None):
        super().__init__()
        self._conn = cups.Connection()
        self.name = None
        self.max_pages = max_pages
        self.count = counters
        self.busy = False

        if not name or name.lower() == "default":
            self.name = self._conn.getDefault()
            if not self.name and self._conn.getPrinters():
                for printer in self._conn.getPrinters():
                    if "SELPHY" in printer and "fotobox" in printer:
                        self.name = printer
                        break
        elif name in self._conn.getPrinters():
            self.name = name

        if not self.name:
            if name.lower() == "default":
                print("No printer configured in CUPS (see http://localhost:631)")
            else:
                print("No printer named '%s' in CUPS (see http://localhost:631)", name)
        else:
            self._conn.cancelAllJobs(self.name)
            self._conn.enablePrinter(self.name)
            print("Connected to printer '%s'", self.name)

    def reset_jobs(self):
        self._conn.cancelAllJobs(self.name)  # reset all jobs
        self._conn.enablePrinter(self.name)  # reset printer -> resets error
    
    def check_status(self):
        status = self._conn.getPrinterAttributes(self.name)
        if status["printer-state-reasons"][0] != "none":
            self.reset_jobs()
            return status["printer-state-message"]

    def printing(self, picture):
        if self.name is None:
            raise EnvironmentError("Drucken nicht möglich. Fotobox neu starten")
        
        printer_state = self._conn.getPrinters()[self.name]
        match printer_state['printer-state-message']:
            case "Der Drucker existiert nicht oder ist zurzeit nicht verfügbar.":
                raise EnvironmentError("Drucker nicht verfügbar bitte starten.")

        if not osp.isfile(picture):
            raise IOError(f"Fehler beim im Foto: {picture}. Kann nicht gedruckt werden")

        super().print_picture(picture)
        job_id = self._conn.printFile(self.name, picture, osp.basename(picture), {})
        # sleep short to give cups time to receive task
        time.sleep(2)
        
        job_info = self._conn.getJobAttributes(job_id)
        start_print_time = time.time()
        start_waiting_time = None
        while job_info['job-state-reasons'] == "job-printing":
            time.sleep(2)
                                
            # Long timeout nothing is working
            if (time.time() - start_print_time) > 150:
                raise RuntimeError("Timeout Error - Error in Printer")

            # ------ Log section ----------- 
            # job_info = self._conn.getJobAttributes(job_id)
            # print(f"Overall job state {job_info['job-state-reasons']}")
            # number = len(job_info["job-printer-state-reasons"])
            # print(f"Number of current printer job states {number}")
            # for reason in job_info["job-printer-state-reasons"]:
            #     print(reason)
            # -------------------------

            job_info = self._conn.getJobAttributes(job_id)
            # Check finish condition 
            if job_info['job-state-reasons'] == "processing-to-stop-point":
                break
            if job_info["job-printer-state-reasons"] is None:
                break
            # Check for error
            for reason in job_info["job-printer-state-reasons"]:
                match reason:
                    case "cups-missing-filter-warning":
                        # Do nothing here
                        pass

                    case "cups-waiting-for-job-completed":
                        if start_waiting_time is None:
                            start_waiting_time = time.time()
                        else:
                            # Printing duration ~60 sec 
                            if (time.time() - start_waiting_time) > 120:
                                raise RuntimeError("Drucker zu langsam - bitte nachschauen ob alles ok ist")
                    
                    case "marker-supply-empty-error":
                        raise RuntimeError("Keine Druckerpatrone im Drucker bitte hinten einsetzten oder tauschen")
                
                    case "toner-empty":
                        raise RuntimeError("Druckerpatrone bitte hinten tauschen")

                    case "media-empty-error" | "media-needed":
                        raise RuntimeError("Kein Papier mehr im Drucker. Bitte seitlich nachfüllen")
                    
                    case "input-tray-missing":
                        raise RuntimeError("Kein Papierfach. Bitte Papierfach seitlich einstetzen")
                    
                    case _:
                        raise RuntimeError(f"Problem beim Drucker - {reason} - ")

    def print_picture(self, picture):
        """Send a file to the CUPS server to the default printer."""
        if self.busy:
            raise RuntimeError("Letzter Druck Job noch nicht abgeschlossen")
        self.busy = True
        try:
            self.printing(picture)
        except Exception as e:
            self.reset_jobs()
            self.busy = False
            raise e
