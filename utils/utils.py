import cv2
import os
import requests
import re
import socket

from PIL import Image
from sys import platform


def openImage(layoutSrc):
    try:
        img = Image.open(layoutSrc)
    except:
        img = cv2.imread(layoutSrc, cv2.IMREAD_UNCHANGED)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        img = Image.fromarray(img)
    return img


def findInserts(layoutSrc):
    img = openImage(layoutSrc)
    width, height = img.size
    img = img.convert("RGBA")
    imgData = list(img.getdata())
    imageLines = []
    oldTransprancy = 255
    for index, item in enumerate(imgData):
        # check for edge in transprancy from filled (255) to none filled (0)
        if item[3] < 10 and item[3] != oldTransprancy:
            ancor = {"x": 0, "y": 0, "width": 0, "height": 0}
            ancor["y"] = int(index / width)
            ancor["x"] = index % width
            loopIndex = index
            # search for end of x
            while imgData[loopIndex][3] == item[3]:
                loopIndex += 1
                if loopIndex >= len(imgData):
                    break
            # search for end of y
            ancor["width"] = loopIndex - index
            loopIndex = index
            while imgData[loopIndex][3] == item[3]:
                loopIndex += width
                if loopIndex >= len(imgData):
                    break

            ancor["height"] = int(loopIndex / width) - ancor["y"]
            imageLines.append(ancor)
        oldTransprancy = item[3]

    def takeX(elem):
        return elem["x"]

    # sort by x values to get the lines via the same x value
    imageLines.sort(key=takeX)
    if len(imageLines) == 0:
        raise ImportError("Fehler in den leer Feldern für die Bilder")
    lastAncor = imageLines[0]

    imageAncors = []
    # check first item
    if imageLines[0]["height"] > 10:
        imageAncors.append(imageLines[0])
    for index, item in enumerate(imageLines):
        # check if last ancor was last ancor of insert
        if lastAncor["height"] == 1:
            # only if there is a big enough space
            if item["height"] > 10:
                imageAncors.append(item)
        lastAncor = item
    return imageAncors


def resetUsbViaName(name):
    # see https://wiki.ubuntuusers.de/usbreset/
    import subprocess
    import re

    # see https://stackoverflow.com/questions/8110310/simple-way-to-query-connected-usb-devices-info-in-python
    dev_tree = subprocess.check_output("lsusb")
    device_re = re.compile(
        b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$",
        re.I,
    )
    for i in dev_tree.split(b"\n"):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                dinfo["device"] = "/dev/bus/usb/%s/%s" % (
                    dinfo.pop("bus").decode("ascii"),
                    dinfo.pop("device").decode("ascii"),
                )
                if name in dinfo["tag"].decode("ascii"):
                    result = subprocess.run(["usbreset", dinfo["device"]])
                    if result.returncode == 0:
                        return True
                    else:
                        return False
    return False


def getWifiList():
    cmd = os.popen("sudo iw dev wlan0 scan | grep SSID")
    wifi = cmd.read()
    wifi = re.findall(r"SSID: (.+)\n", wifi)
    wifi = list(set(wifi))
    return wifi


def get_operating_system():
    if platform == "win32":
        return "Windows"
    elif platform.startswith("linux"):
        return "Linux"
    else:
        return "Other"


def getActivWifi():
    if platform != "win32":
        cmd = os.popen("iwgetid")
        wifi = cmd.read()
        wifi = re.findall(r'ESSID:"(.+)"', wifi)
        if wifi:
            return wifi
        else:
            return False
    return False


def checkInternetConnection(timeout=5):
    url = "http://www.google.com"
    try:
        request = requests.get(url, timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout) as exception:
        return False


def connectToWifi(essid, password):
    # see https://programmerall.com/article/8884208824/
    # use wpa_cli to add network
    cmd = os.popen("sudo wpa_cli -i wlan0 list_network")
    networks = cmd.read()
    # Build list of current networks
    # network id / ssid / bssid / flags\
    networks = networks.split("\n")  # split into rows
    networks = networks[1:-1]  # remove first and last row
    for network in networks:
        network_info = network.split("\t")
        # check if network is in list
        if network_info[1] == essid:
            if network_info[3] != "[CURRENT]":
                # Remove network from list if it is not active
                cmd = os.popen(f"sudo wpa_cli -i wlan0 remove_network {network_info[0]}")
                if cmd.read() != "OK\n":
                    return {
                        "status": "Error",
                        "description": "Netzwerk nicht gefunden",
                        "status_code": 409,
                    }
            else:
                return {
                    "status": "Error",
                    "description": "Netzwerk ist schon aktiv",
                    "status_code": 409,
                }

    cmd = os.popen("sudo wpa_cli -i wlan0 add_network")
    network_id = int(cmd.read())
    while True:
        detail_error = ""
        cmd = os.popen(f"sudo wpa_cli -i wlan0 set_network {network_id} ssid '\"{essid}\"'")
        if cmd.read() != "OK\n":
            detail_error = " - Netzwerk setzen Problem"
            break
        cmd = os.popen(f"sudo wpa_cli -i wlan0 set_network {network_id} psk '\"{password}\"'")
        if cmd.read() != "OK\n":
            detail_error = " - Flasches Passwort"
            break
        cmd = os.popen(f"sudo wpa_cli -i wlan0 set_network {network_id} scan_ssid 1")
        if cmd.read() != "OK\n":
            detail_error = " - Neues Netzwerk suchen Problem"
            break
        cmd = os.popen(f"sudo wpa_cli -i wlan0 set_network {network_id} priority 1")
        if cmd.read() != "OK\n":
            detail_error = " - Problem setzen Prio"
            break
        cmd = os.popen("sudo wpa_cli -i wlan0 save_config")
        if cmd.read() != "OK\n":
            detail_error = " - Problem Speichern Einstellungen"
            break
        cmd = os.popen(f"sudo wpa_cli -i wlan0 select_network {network_id}")
        if cmd.read() != "OK\n":
            detail_error = " - Problem Netzwerk Aktivieren"
            break
        return {
            "status": "Okay",
            "status_code": 200,
        }
    return {
        "status": "Error",
        "status_code": 409,
        "description": "Fehler in Netzwerkeinstellungen" + detail_error,
    }


def get_ip_address(interface):
    try:
        # Extract the IP address using the 'ip' command
        if get_operating_system() == "Linux":
            ip_address = (
                os.popen(f'ip -4 addr show {interface} | grep -oP "(?<=inet\\s)\d+(\\.\\d+){{3}}"').read().strip()
            )
            return f"{ip_address}"
        else:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            return f"{ip_address}"
    except Exception as e:
        return f"No Ip address found"


def start_browser():
    import subprocess

    process = subprocess.Popen(
        ["cmd", "/c", "start msedge 127.0.0.1:5001 --start-maximized --start-fullscreen"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate()


def kill_browser():
    import subprocess

    process = subprocess.Popen(
        ["cmd", "/c", "taskkill /im msedge.exe /f"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate()
