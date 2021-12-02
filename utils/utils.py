from PIL import Image

def findInserts(layoutSrc):
    img = Image.open(layoutSrc) 
    width, height = img.size
    img = img.convert("RGBA")
    imgData = list(img.getdata())
    imageLines = []
    oldTransprancy = 255
    for index, item in enumerate(imgData):
        #check for edge in transprancy from filled (255) to none filled (0)
        if item[3] < 10 and item[3] != oldTransprancy:
            ancor = {'x':0, 'y':0, 'width':0, 'height':0}
            ancor['y'] = int(index / width)
            ancor['x'] = index % width
            loopIndex = index
            #search for end of x
            while imgData[loopIndex][3] == item[3]:
                loopIndex += 1
            #search for end of y
            ancor['width'] = loopIndex - index
            loopIndex = index
            while imgData[loopIndex][3] == item[3]:
                loopIndex += width

            ancor['height'] = int(loopIndex / width) - ancor['y']
            imageLines.append(ancor)
        oldTransprancy = item[3]
    
    def takeX(elem):  
        return elem['x']
    
    #sort by x values to get the lines via the same x value
    imageLines.sort(key=takeX)
    lastAncor = imageLines[0]
    
    imageAncors = []
    #check first item
    if(imageLines[0]['height'] > 10):
        imageAncors.append(imageLines[0])
    for index, item in enumerate(imageLines):
        #get last page
        if lastAncor['height'] == 1:
            #only if there is a big enough space
            if(item['height'] > 10):
                imageAncors.append(item)
        lastAncor = item
    return imageAncors

def resetUsbViaName(name):
    #see https://wiki.ubuntuusers.de/usbreset/
    import subprocess
    import re
    #see https://stackoverflow.com/questions/8110310/simple-way-to-query-connected-usb-devices-info-in-python
    dev_tree = subprocess.check_output("lsusb")
    device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
    for i in dev_tree.split(b'\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus').decode('ascii'), dinfo.pop('device').decode('ascii'))
                if name in dinfo['tag'].decode('ascii'):
                    result = subprocess.run(['usbreset', dinfo['device']])
                    if result.returncode == 0:
                        return True
                    else:
                        return False
    return False
    
def getWifiList():
    import os
    import re
    cmd = os.popen('sudo iw dev wlan0 scan | grep SSID')
    wifi = cmd.read()
    wifi = re.findall(r"SSID: (.+)\n" ,wifi)
    wifi = list(set(wifi))
    return wifi

def getActivWifi():
    import os
    import re
    cmd = os.popen('iwgetid')
    wifi = cmd.read()
    wifi = re.findall(r'ESSID:"(.+)"' ,wifi)
    if wifi: 
        return True
    else:
        return False

def checkInternetConnection():
    import requests
    url = "http://www.google.com"
    timeout = 5
    try:
	    request = requests.get(url, timeout=timeout)
	    return True
    except (requests.ConnectionError, requests.Timeout) as exception:
	    return False

def connectToWifi(essid, password):
    import os
    import re
    # see https://programmerall.com/article/8884208824/
    # use wpa_cli to add network
    cmd = os.popen("wpa_cli -i wlan0 list_network")
    networks = re.findall('(\d+)\s'+essid+'',cmd.read())
    if networks:
        # found existing network
        network = networks[0]
        cmd = os.popen("wpa_cli -i wlan0 remove_network {network}")

    cmd = os.popen("wpa_cli -i wlan0 add_network")
    network = int(cmd.read())
    while True:
        cmd = os.popen(f"wpa_cli -i wlan0 set_network {network} ssid '\"{essid}\"'")
        if cmd.read() != "OK\n":
            break
        cmd = os.popen(f"wpa_cli -i wlan0 set_network {network} psk '\"{password}\"'")
        if cmd.read() != "OK\n":
            break
        cmd = os.popen(f"wpa_cli -i wlan0 set_network {network} scan_ssid 1")
        if cmd.read() != "OK\n":
            break
        cmd = os.popen(f"wpa_cli -i wlan0 set_network {network} priority 1")
        if cmd.read() != "OK\n":
            break
        cmd = os.popen("wpa_cli -i wlan0 save_config")
        if cmd.read() != "OK\n":
            break
        cmd = os.popen(f"wpa_cli -i wlan0 select_network {network}")
        if cmd.read() != "OK\n":
            break
        return True
