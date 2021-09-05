# -*- coding: utf-8 -*-

import cups
import tempfile
import os.path as osp

from PIL import Image

PAPER_FORMATS = {
    '2x6': (2, 6),      # 2x6 pouces - 5x15 cm - 51x152 mm
    '3,5x5': (3.5, 5),  # 3,5x5 pouces - 9x13 cm - 89x127 mm
    '4x6': (4, 6),      # 4x6 pouces - 10x15 cm - 101x152 mm
    '5x7': (5, 7),      # 5x7 pouces - 13x18 cm - 127x178 mm
    '6x8': (6, 8),      # 6x8 pouces - 15x20 cm - 152x203 mm
    '6x9': (6, 9),      # 6x9 pouces - 15x23 cm - 152x229 mm
}

"""
use cups to install the printer via http://localhost:631/
Bug Fixes see
https://www.voss.earth/2018/08/31/kurztipp-canon-selphy-wlan-drucker-cp910-oder-cp1300-unter-linux-cups-verwenden/
https://askubuntu.com/questions/1180926/connect-canon-selphy-cp1200-via-usb-ubuntu-19-04
"""
class Printer(Logger):
    def __init__(self, name='default', max_pages=-1, counters=None):
        super().__init__()
        self._conn = cups.Connection()
        self.name = None
        self.max_pages = max_pages
        self.count = counters

        if not name or name.lower() == 'default':
            self.name = self._conn.getDefault()
            if not self.name and self._conn.getPrinters():
                for printer in self._conn.getPrinters():
                    if "SELPHY" in printer:
                        self.name = printer  # Take first one
        elif name in self._conn.getPrinters():
            self.name = name

        if not self.name:
            if name.lower() == 'default':
                print("No printer configured in CUPS (see http://localhost:631)")
            else:
                print("No printer named '%s' in CUPS (see http://localhost:631)", name)
        else:
            print("Connected to printer '%s'", self.name)

    def print_picture(self, picture, copies=1):
        """Send a file to the CUPS server to the default printer.
        """
        if not self.name:
            raise EnvironmentError("No printer found (check config file or CUPS config)")
        if not osp.isfile(picture):
            raise IOError("No such file or directory: {}".format(picture))

        if copies > 1:
            with tempfile.NamedTemporaryFile(suffix=osp.basename(picture)) as fp:
                picture = Image.open(picture)
                # Don't call setup factory hook here, as the selected parameters
                # are the one necessary to render several pictures on same page.
                self._conn.printFile(self.name, fp.name, osp.basename(picture), {})
        else:
            self._conn.printFile(self.name, picture, osp.basename(picture), {})
        super().print_picture(picture)
        print("File '%s' sent to the printer", picture)