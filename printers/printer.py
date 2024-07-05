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
                        self.name = printer  # Take first one
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
        if not self.name:
            raise EnvironmentError(
                "No printer found (check config file or CUPS config)"
            )
        if not osp.isfile(picture):
            raise IOError("No such file or directory: {}".format(picture))

        super().print_picture(picture)
        print("File '%s' sent to the printer", picture)

        job_id = self._conn.printFile(self.name, picture, osp.basename(picture), {})
        job_info = self._conn.getJobAttributes(job_id)
        start_print_time = time.time()
        start_waiting_time = None
        while job_info["job-state"] == 5:  # job_info['job-state-reasons']==job-printing
            time.sleep(1)
            job_info = self._conn.getJobAttributes(job_id)

            for reason in job_info["job-printer-state-reasons"]:
                match reason:
                    case "cups-missing-filter-warning":
                        # Do nothing here
                        pass

                    case "cups-waiting-for-job-completed":
                        if start_waiting_time == None:
                            start_waiting_time = time.time()
                        if time.time() - start_waiting_time > 30:
                            self.reset_jobs()
                            return "Drucker zu langsam - bitte nachschauen ob alles ok ist"
                    
                    case "marker-supply-empty-error":
                        self.reset_jobs()
                        return "Keine Druckerpatrone im Drucker bitte hinten einsetzten oder tauschen"
                
                    case "toner-empty":
                        self.reset_jobs()
                        return "Druckerpatrone bitte hinten tauschen" 

                    case "media-empty-error" | "media-needed":
                        self.reset_jobs()
                        return "Kein Papier mehr im Drucker. Bitte seitlich nachfüllen"
                    
                    case _:
                        super().log_error(reason)
                        self.reset_jobs()
                        return f"Problem beim Drucker - {reason} - "
                    

            # Long timeout nothing is working
            if time.time() - start_print_time > 60:
                error = self.check_status()
                if error:
                    return error
                return "Timeout Error - Error in Printer"

        job_info = self._conn.getJobAttributes(job_id)
        if job_info["job-state"] == 3 or job_info["job-state"] == 4:
            # job_info['job-state-reasons'] => printer-stopped
            error = self.check_status()
            if not (error):
                self.reset_jobs()
                error = job_info["job-printer-state-message"]
            return error

    def translate(self, status):
        if status == "Printer open failure (No matching printers found!)":
            return "Drucker ist abgeschaltet"
        elif status == "Printer error: No Paper (03)":
            return "Kein Papier - seitlichen Papiereinzug einsetzen"
        elif status == "Printer error: No Ink (07)":
            return "Keine Tinte - hinten weißen Einsatz einsetzen"
        elif status == "Printer error: Ink Cassette Empty (06)":
            return "Tinte leer - hinten weißen Einsatz tauschen"
        return status

    def print_picture(self, picture):
        """Send a file to the CUPS server to the default printer."""
        if self.busy:
            return "Letzter Druck Job noch nicht abgeschlossen"
        self.busy = True
        try:
            status = self.printing(picture)
            status = self.translate(status)
        except Exception as e:
            status = repr(e)
        self.busy = False
        return status
