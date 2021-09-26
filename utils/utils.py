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