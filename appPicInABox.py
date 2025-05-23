import os
import shutil
import argparse
from enum import Enum

from flask import (
    Flask,
    render_template,
    Response,
    request,
    redirect,
    url_for,
    jsonify,
    send_from_directory,
    send_file,
    make_response,
)
from settings.settings import Settings
from error.error import Error
from upload.mega_io import MegaNz

import time
import cv2
import numpy as np
import git

import glob
import json
import qrcode
from datetime import datetime
from io import BytesIO
from PIL import Image
from utils.utils import (
    get_ip_address,
    get_operating_system,
    kill_browser,
    openImage,
    findInserts,
    getWifiList,
    getActivWifi,
    checkInternetConnection,
    connectToWifi,
    start_browser,
)


class enCamera(Enum):
    DSLR = 0
    PI = 1
    WEBCAM = 2
    IP = 3


class cameraContainer:
    def __init__(self):
        self.previewCamera = None
        self.fotoCamera = None
        self.videoCamera = None
        self.timelapsCamera = None


def exit():
    global g_cameras

    for camera in g_cameras:
        if camera:
            camera.fotoCamera.disconnect()
            camera.previewCamera.stream_stop()
            camera.previewCamera.disconnect()
            camera.timelapsCamera.recording_stop()
            camera.timelapsCamera.disconnect()
            # camera.videoCamera.disconnect()


# create Flask object with __name__ --> acutal python object
app = Flask(__name__)
# Cache files for one day -> enable if QR code is not cached
# app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24
# Do not cache anything because some pictures need to be reloaded like the rendered ones
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.secret_key = "sdbngiusdngdsgbiursbng"
app.config["UPLOAD_FOLDER"] = "static/pictures/custom_style"
app.config["MAX_CONTENT_PATH"] = 16 * 1000 * 1000
ALLOWED_EXTENSIONS = set(["png", "ico"])

# TODO if update in default json we need to merge user json
try:
    with open("static/user.json") as json_file:
        data = json.load(json_file)
except:
    with open("static/default.json") as json_file:
        data = json.load(json_file)

g_settings = Settings(**data)
g_files = []
g_modus = None
g_anchorsMulti = []
g_anchorSingle = []
g_error = Error()
g_url = ""
g_activeCamera = cameraContainer()
g_cameras = []
g_frame = []
g_init = False
g_remove_click_time = 0
g_remove_click_cnt = 0
g_printer = None
g_file_server = MegaNz()


# -------------------------------
# Settings Functions
# -------------------------------
@g_settings.Callback("previewCamera")
def set_preview_camera(value):
    global g_activeCamera
    camera = g_cameras[int(value)]
    if camera:
        # stop old stream
        if g_activeCamera.timelapsCamera:
            g_activeCamera.timelapsCamera.recording_stop()
        if g_activeCamera.previewCamera:
            g_activeCamera.previewCamera.stream_stop()
        # load new camera
        g_activeCamera.previewCamera = camera.previewCamera
        g_activeCamera.timelapsCamera = camera.timelapsCamera
        if int(value) == 3:
            g_activeCamera.previewCamera.disconnect()
            g_activeCamera.previewCamera.connect(30)
        else:
            # only start ip no ip camera is used
            g_activeCamera.previewCamera.stream_start()
        return {"status": "Okay"}
    # no camera found
    return {"status": "Error", "description": "Kamera nicht verfügbar"}


@g_settings.Callback("fotoCamera")
def set_foto_camera(value):
    global g_activeCamera
    camera = g_cameras[int(value)]
    if camera != None:
        # load new camera
        g_activeCamera.fotoCamera = camera.fotoCamera
        g_activeCamera.videoCamera = camera.videoCamera
        if int(value) == 3:
            g_activeCamera.fotoCamera.disconnect()
            g_activeCamera.fotoCamera.connect(30)
            # g_activeCamera.videoCamera.disconnect()
            # g_activeCamera.videoCamera.connect(30)
        return {"status": "Okay"}
    # no camera found
    return {"status": "Error", "description": "Kamera nicht verfügbar"}


@g_settings.Callback("timelaps")
def activate_timelaps(value):
    if int(value) and int(value) != 3:
        # dont start if ip camera
        g_activeCamera.timelapsCamera.recording_start()
    else:
        g_activeCamera.timelapsCamera.recording_stop()
    return {"status": "Okay"}


@g_settings.Callback("timelapsCreate")
def create_timelaps(value):
    if int(value) and int(value) != 3:
        # dont start if ip camera
        g_activeCamera.timelapsCamera.recording_save()
    return {"status": "Okay"}  # return okay if no error before


# -------------------------------
# Webserver Functions
# from https://flask-session.readthedocs.io/en/latest/
# from https://pythonise.com/series/learning-flask/python-before-after-request
# -------------------------------
def before_first_request_func(port):
    """
    This function will run once before the first request to this instance of the application.
    You may want to use this function to create any databases/tables required for your app.
    """

    initialize()

    global g_anchorsMulti
    global g_anchorSingle
    global g_modus
    global g_settings
    global g_init

    if g_init == False:
        g_init = True
        g_modus = 1
        try:
            g_anchorsMulti = findInserts(os.path.join(app.config["UPLOAD_FOLDER"], "LayoutMulti.png"))
            g_anchorSingle = findInserts(os.path.join(app.config["UPLOAD_FOLDER"], "LayoutSingle.png"))
        except Exception as e:
            error = {
                "status": "Error",
                "description": "Layouts können nicht geladen werden",
            }
            g_error.put(error)
            error = {"status": "Error", "description": repr(e)}
            g_error.put(error)

        for folder in ["orginal_pictures", "pictures", "videos", "timelaps"]:
            path = os.path.join("./data", folder)
            if not (os.path.exists(path)):
                os.makedirs(path)

    print("[picInABox] Browser will start now")
    if get_operating_system() == "Windows":
        start_browser(port)


# from https://www.youtube.com/watch?v=8qDdbcWmzCg
# adds settings json to each page
@app.context_processor
def context_processor():
    global g_settings
    return dict(settings=g_settings.get_json(), system=get_operating_system())


# -------------------------------
# Web pages
# -------------------------------
@app.route("/")
def pageStart():
    return render_template("startPage.html")


@app.route("/settings")
def pageSettings():
    global g_remove_click_cnt
    active = request.args.get("active")
    if active is not None:
        return render_template("settingsPage.html", directory="data", active=active)
    else:
        # Resetting delete count if page gets open without any active tab
        g_remove_click_cnt = 0
        return render_template("settingsPage.html", directory="data", active="Camera")


@app.route("/options")
def pageOptions():
    # [Single Foto, 4'er Session Foto, Video]
    return render_template(
        "chooseOption.html",
        numberOfPictures=len(g_anchorsMulti),
        enable=[
            g_settings.singlePicture,
            g_settings.multiPicture,
            g_settings.videoPicture,
        ],
    )


@app.route("/picture")
def pagePicture():
    global g_anchorsMulti
    return render_template("picturePage.html", numberOfPictures=len(g_anchorsMulti))


# from https://gist.github.com/arusahni/9434953
@app.route("/download")
def pageDownload():
    response = make_response(render_template("downloadPage.html"))
    response.headers.set("Cache-Control", "no-store, no-cache, must-revalidate, private, max-age=1")
    return response


@app.route("/gallery")
def pageGallery():
    images = os.listdir("./data/pictures")
    images.sort(reverse=True)
    return render_template("gallery.html", imageNames=images)


@app.route("/videoFeed")
def pageVideoFeed():
    global g_activeCamera
    g_activeCamera.previewCamera.stream_start()  # start preview stream
    # Video streaming route. Put this in the src attribute of an img tag
    # This gets called when the image inside the html is loaded
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/upload/<filename>")
def pageImage(filename):
    return send_from_directory("data/pictures", filename)


@app.route("/upload_orign/<filename>")
def pageImageOrgin(filename):
    return send_from_directory("data/orginal_pictures", filename)


# -------------------------------
# Rest API functions
# -------------------------------
@app.route("/api/setting", methods=["POST", "GET"])
def settings():
    global g_activeCamera
    global g_cameras
    global g_settings
    global g_error
    if request.method == "POST":
        jsonReq = json.loads(request.data)
        if "save" in jsonReq:
            with open("static/user.json", "w") as f:
                json.dump(g_settings.get_json(), f)
                response = jsonify({"status": "okay"}, 200)
                return response
        else:
            if jsonReq["key"] in g_settings:
                g_settings[jsonReq["key"]] = jsonReq["value"]
                ret = g_settings.SetItemOkay()
                g_error.put(ret)
                response = jsonify()
                response.status_code = 200
                return response  # return okay if no error before
            return jsonify({"return": "error"})  # default error
    elif request.method == "GET":
        if "key" in request.args:
            return jsonify({"value": g_settings[request.args["key"]]})


@app.route("/api/modus", methods=["POST", "GET"])
def set_modus():
    global g_modus
    if request.method == "POST":
        if "option" in request.args:
            g_modus = int(request.args["option"])
            # redirect the webpage to the picture Page
            return redirect(url_for("pagePicture"))
    elif request.method == "GET":
        return jsonify({"option": g_modus})


@app.route("/api/controlCamera", methods=["POST", "GET"])
def action():
    global g_activeCamera
    jsonReq = json.loads(request.data)
    if request.method == "POST":
        if "takePicture" in jsonReq["option"]:
            g_activeCamera.fotoCamera.picture_take()
            number_of_files = len(glob.glob("data/orginal_pictures/*"))
            fíle_name = g_activeCamera.fotoCamera.picture_save(
                "data/orginal_pictures", f"foto_{(number_of_files + 1):08}"
            )
            data = {"filename": fíle_name}
        elif "startVideo" in jsonReq["option"]:
            g_activeCamera.videoCamera.recording_start()
            data = {}
        elif "stopVideo" in jsonReq["option"]:
            g_activeCamera.videoCamera.recording_stop()
            data = {}
            # TODO save video here and return filename
    return jsonify(data)


@app.route("/api/getQRCode", methods=["GET"])
def get_qrCode():
    global g_modus
    global g_file_server
    if request.method == "GET":
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        img_buf = BytesIO()

        if g_settings["qrCode"] and checkInternetConnection(3):
            if g_modus == 1 or g_modus == 2:
                list_of_files = glob.glob("data/pictures/*")
                list_of_files.sort()
                dataSrc = list_of_files[-1]
            elif g_modus == 3:
                list_of_files = glob.glob("data/videos/*")
                list_of_files.sort()
                dataSrc = list_of_files[-1]
            if g_file_server.Connect():
                if g_file_server.UploadPicture(dataSrc):
                    download_link = g_file_server.GetLastUploadLink()
                    qr.add_data(download_link)
                    qr.make(fit=True)
                    # from https://stackoverflow.com/questions/26417328/how-to-serve-a-generated-qr-image-using-pythons-qrcode-on-flask
                    # from https://stackoverflow.com/questions/24920728/convert-pillow-image-into-stringio
                    img = qr.make_image(fill_color="black", back_color="white")
                    img.save(img_buf)
                    img_buf.seek(0)
                    return send_file(img_buf, mimetype="image/jpg")
        # default return transparent image
        data = np.zeros((512, 512, 4))
        img = Image.fromarray(data, "RGBA")
        img_buf = BytesIO()
        img.save(img_buf, "PNG")
        img_buf.seek(0)
        return send_file(img_buf, mimetype="image/png")


@app.route("/api/renderPicture", methods=["GET"])
def get_picture():
    global g_modus
    global g_anchorsMulti
    global g_anchorSingle
    time.sleep(2)
    if request.method == "GET":
        list_of_files = glob.glob("data/orginal_pictures/*")
        list_of_files.sort()
        pics = []
        if g_modus == 1:
            # append last taken image
            pics.append(openImage(list_of_files[-1]))
            layoutSrc = os.path.join(app.config["UPLOAD_FOLDER"], "LayoutSingle.png")
            anchors = g_anchorSingle

        elif g_modus == 2:
            pics = []
            for index in range(1, len(g_anchorsMulti) + 1):
                id = index * -1
                pics.append(openImage(list_of_files[id]))
            layoutSrc = os.path.join(app.config["UPLOAD_FOLDER"], "LayoutMulti.png")
            anchors = g_anchorsMulti

        compositeImg = Image.new("RGBA", (openImage(layoutSrc).size), (255, 0, 0, 0))
        # from https://www.tutorialspoint.com/python_pillow/Python_pillow_merging_images.htm
        for ancor in anchors:
            compositeImg.paste(
                pics[anchors.index(ancor)].resize((ancor["width"], ancor["height"]), Image.LANCZOS),
                (ancor["x"], ancor["y"]),
            )  # from https://www.geeksforgeeks.org/python-pil-image-resize-method/

        layoutImg = openImage(layoutSrc)
        # from https://pythontic.com/image-processing/pillow/alpha-composite
        finalImg = Image.alpha_composite(compositeImg, layoutImg)
        # imgSrc = "data/pictures/"+ datetime.now().strftime('%Y_%m_%d_%H_%M_%S') +"_4Pics.jpg"
        number_of_files = len(glob.glob("data/pictures/*"))
        imgSrc = os.path.join("data/pictures/", f"foto_{(number_of_files + 1):08}.jpg")
        finalImg = finalImg.convert("RGB")
        finalImg.save(
            imgSrc, quality=100, subsampling=0
        )  # from data https://jdhao.github.io/2019/07/20/pil_jpeg_image_quality/
        return send_file(imgSrc, mimetype="image/jpg")


@app.route("/api/renderVideo", methods=["GET"])
def get_video():
    global g_modus
    global g_activeCamera
    time.sleep(2)
    if request.method == "GET":
        g_activeCamera.videoCamera.recording_save("data/videos")
        list_of_files = glob.glob("data/videos/*")
        list_of_files.sort()
        vidSrc = list_of_files[-1]
        resp = make_response(send_file(vidSrc, "video/avi"))
        resp.headers["Content-Disposition"] = "inline"
        return resp


@app.route("/lastRawFrame", methods=["GET"])
def lastRawFrame():
    # https://www.kite.com/python/answers/how-to-serialize-a-numpy-array-into-json-in-python
    # https://stackoverflow.com/questions/58433450/how-to-send-ndarray-response-from-flask-server-to-python-client
    frameRaw = g_activeCamera.previewCamera.stream_show()
    if type(frameRaw) != "NoneType" and len(frameRaw) > 0:
        return json.dumps(frameRaw.tolist())
    else:
        return None


@app.route("/api/data", methods=["GET"])
def zipFile():
    global g_remove_click_cnt
    global g_remove_click_time
    if "zip" in request.query_string.decode("utf-8").split("=")[0]:
        # If there is already a zip file delete the old one, zip a zip file makes problems
        for file in os.listdir("data/"):
            file_path = os.path.join("data/", file)
            if os.path.isfile(file_path):
                file_extension = os.path.splitext(file_path)[1]
                if "zip" in file_extension:
                    os.remove(file_path)
        file_name = "data/all_picutres_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        shutil.make_archive(file_name, "zip", "data/")
        response = jsonify({"file": file_name + ".zip"})
        return response  # return okay if no error before
    elif "get" in request.query_string.decode("utf-8").split("=")[0]:
        file_name = request.query_string.decode("utf-8").split("=")[1]
        return send_file(
            file_name,
            mimetype="zip",
            as_attachment=True,
            download_name=file_name,
        )
    elif "remove" in request.query_string.decode("utf-8").split("=")[0]:
        g_remove_click_cnt += 1
        if (g_remove_click_cnt % 2) == 0 and (time.time() - g_remove_click_time) < 25:
            dirs = ["data", "data/pictures", "data/timelaps", "data/videos", "data/orginal_pictures"]
            for dir in dirs:
                for f in os.listdir(dir):
                    to_delete = os.path.join(dir, f)
                    if os.path.isfile(to_delete):
                        os.remove(to_delete)
            info = {"status": "Info", "description": "Alle Bilder/Videos wurden glöscht"}
            g_error.put(info)
        else:
            g_remove_click_time = time.time()
            info = {
                "status": "Info",
                "description": "Nochmal 'Löschen' drücken um alle Bilder/Videos zu löschen",
            }
            g_error.put(info)
        return redirect(url_for("pageSettings", active="Data"))


@app.route("/api/kill")
def kill():
    import os
    import signal

    if get_operating_system() == "Windows":
        kill_browser()

    pid = os.getpid()
    os.kill(pid, signal.SIGINT)
    return Response(status=200)


@app.route("/api/update", methods=["GET"])
def update():
    if "update" in request.query_string.decode("utf-8"):
        # https://stackoverflow.com/questions/15315573/how-can-i-call-git-pull-from-within-python
        g = git.cmd.Git(os.getcwd())
        try:
            g.pull()
        except Exception as e:
            error = {"status": "Error", "description": repr(e)}
            g_error.put(error)
            response = Response(status=500)
    elif "reboot" in request.query_string.decode("utf-8"):
        os.popen("sudo reboot")
        response = jsonify()
        response.status_code = 200
    else:
        response = jsonify()
        response.status_code = 400
    return redirect(url_for("pageStart"))


@app.route("/status", methods=["GET"])
def status():
    global g_error
    global g_activeCamera
    if request.method == "GET":
        if "folder" in request.args:
            response = jsonify(
                {
                    "timelaps": len(os.listdir(os.path.join(request.args["folder"], "timelaps"))),
                    "pictures": len(os.listdir(os.path.join(request.args["folder"], "orginal_pictures"))),
                }
            )
            response.status_code = 200
            return response
        elif "error" in request.args:
            error = g_error.get()
            if error:
                response = jsonify(error)
                response.status_code = 400
                return response
            else:
                response = jsonify({"type": "Okay", "description": "none"})
                response.status_code = 200
                return response
        elif "timelaps" in request.args:
            response = jsonify(g_activeCamera.timelapsCamera.status_save())
            response.status_code = 200
            return response
        elif "git" in request.args:
            repo = git.Repo(search_parent_directories=True)
            sha = repo.head.object.hexsha
            date = repo.head.object.committed_date
            summary = repo.head.object.summary
            date = str(datetime.fromtimestamp(date))
            tag = next(
                (tag for tag in repo.tags if tag.commit == repo.head.commit),
                "no tag found",
            )
            response = jsonify({"version": sha, "date": date, "tag": tag, "summary": summary})
            response.status_code = 200
            return response


@app.route("/print", methods=["POST"])
def printing():
    global g_printer
    jsonReq = ""
    if request.method == "POST":
        # get contet of post
        if request.content_type == "application/x-www-form-urlencoded":
            jsonReq = request.form.to_dict()
        else:
            jsonReq = json.loads(request.data)
        # check for picture tag
        if jsonReq["key"] == "picture":
            if jsonReq["value"] == "last":
                # If last is given use the last taken picture
                list_of_files = glob.glob("data/pictures/*")
                list_of_files.sort(key=os.path.getctime)
                file = list_of_files[-1]
            else:
                file = os.path.join("data/pictures/", jsonReq["value"])
            try:
                info = {
                    "status": "Info",
                    "description": "Bild wird gedruckt",
                }
                g_error.put(info)
                g_printer.print_picture(file)
                info = {
                    "status": "Info",
                    "description": "Bild fertig. Seitlich entnehmen.",
                }
                g_error.put(info)
            except Exception as e:
                error = {"status": "Error", "description": e.args}
                g_error.put(error)
            response = jsonify({"return": "done"})
            response.status_code = 200
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response  # return okay if no error before
        else:
            response = jsonify({"return": "error"})
            response.status_code = 400
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response  # return okay if no error before


@app.route("/wifi", methods=["POST", "GET"])
def wifi():
    global g_error
    global g_internet_active
    if request.method == "GET":
        if "all" in request.args:
            wifi = getWifiList()
            response = jsonify(wifi)
            response.status_code = 200
            return response
        elif "active" in request.args:
            wifi = getActivWifi()
            response = jsonify(wifi)
            response.status_code = 200
            return response
        elif "internet" in request.args:
            wifi = checkInternetConnection()
            response = jsonify(wifi)
            response.status_code = 200
            return response
        elif "ip" in request.args:
            ip = get_ip_address("wlan0")
            response = jsonify({"ip": ip})
            response.status_code = 200
            return response
    elif request.method == "POST":
        jsonReq = json.loads(request.data)
        if "wifi" in jsonReq and "psw" in jsonReq:
            try:
                ret = connectToWifi(jsonReq["wifi"], jsonReq["psw"])
                g_error.put(ret)
                response = Response(status=ret["status_code"])
            except Exception as e:
                error = {"status": "Error", "description": repr(e)}
                g_error.put(error)
                response = Response(status=500)
            return response
        else:
            error = {
                "status": "Error",
                "description": "No wifi passwort or wifi selected",
            }
            g_error.put(error)
            response = jsonify({"return": "error"})
            response.status_code = 400
            return response
    else:
        response = jsonify({"return": "error"})
        response.status_code = 400
        return response


# https://pythonbasics.org/flask-upload-file/
# https://stackoverflow.com/questions/44926465/upload-image-in-flask
@app.route("/upload", methods=["GET", "POST"])
def upload():
    global g_files
    global g_anchorsMulti
    global g_anchorSingle
    if request.method == "POST":
        for file_name in g_files:
            if file_name in request.files:
                file = request.files[file_name]
                if "Layout" in file_name:
                    tempFile = os.path.join(app.config["UPLOAD_FOLDER"], "temp.png")
                    file.save(tempFile)
                    try:
                        inserts = findInserts(tempFile)
                    except Exception as ex:
                        if ex.msg is not None:
                            error = {
                                "status": "Error",
                                "description": ex.msg,
                            }
                        else:
                            error = {
                                "status": "Error",
                                "description": "Fehler im hochgelanden Layout.",
                            }
                        g_error.put(error)
                        return redirect(url_for("pageSettings", active="Upload"))
                    if "Multi" in file_name:
                        if len(inserts) < 2:
                            os.remove(tempFile)
                            error = {
                                "status": "Error",
                                "description": "Nicht die Richtige Anzahl transparente Flächen im Layout",
                            }
                            g_error.put(error)
                            return redirect(url_for("pageSettings", active="Upload"))
                        else:
                            g_anchorsMulti = inserts
                    elif "Single" in file_name:
                        if len(inserts) != 1:
                            os.remove(tempFile)
                            error = {
                                "status": "Error",
                                "description": "Nicht die Richtige Anzahl transparente Flächen im Layout",
                            }
                            g_error.put(error)
                            return redirect(url_for("pageSettings", active="Upload"))
                        else:
                            g_anchorSingle = inserts
                    shutil.move(tempFile, os.path.join(app.config["UPLOAD_FOLDER"], file_name))
                    return redirect(url_for("pageSettings", active="Upload"))
                else:
                    file.save(os.path.join(app.config["UPLOAD_FOLDER"], file_name))
                    response = jsonify()
                    response.status_code = 400
                    return redirect(url_for("pageSettings", active="Upload"))


# -------------------------------
# Helper functions
# -------------------------------
def gen():
    global g_activeCamera
    """Video streaming generator function."""
    cnt = 0
    while True:
        time.sleep(1 / 20)
        frame = g_activeCamera.previewCamera.stream_show()
        if type(frame) != "NoneType":
            if len(frame) != 0:  # g_activeCamera.previewCamera.frameSize():
                ret, frameJPG = cv2.imencode(".jpg", frame)
                frameShow = frameJPG.tobytes()
                cnt = 0
                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frameShow + b"\r\n")
            else:
                cnt += 1
                print(
                    f"[picInABox] Corrupt Image in Video stream frame should be {g_activeCamera.previewCamera.frameSize()} but is {len(frame)}"
                )
                if cnt > 200:
                    raise RuntimeError("[picInABox] Too many Corrupt Images")
        else:
            raise RuntimeError("[picInABox] No Frametype given")


def initialize():
    from cameras.webcam import check_webcam
    from cameras.dslrCamera import check_dslrCamera
    from cameras.piCamera import check_piCamera
    from cameras.ipCamera import check_ipcam
    from cameras.cameraRecorder import CameraRecorder
    from cameras.timeLaps import CameraTimelapss

    #########################
    # Remove old zip files
    #########################
    dir_list = os.listdir()

    for item in dir_list:
        if item.endswith(".zip"):
            os.remove(item)

    #########################
    # Init pictures for webpage if none present use default
    #########################
    global g_files
    default_location = "static/pictures/default_style"
    if not os.path.isdir(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    for file in os.listdir(default_location):
        g_files.append(file)
        src_path_file_name = os.path.join(default_location, file)
        dest_path_file_name = os.path.join(app.config["UPLOAD_FOLDER"], file)
        if not os.path.exists(dest_path_file_name):
            shutil.copyfile(src_path_file_name, dest_path_file_name)

    #########################
    # Init printer
    #########################
    global g_printer
    try:
        if get_operating_system() == "Windows":
            from printers.win_printer import Printer

            g_printer = Printer()

        else:
            from printers.cup_printer import Printer

            g_printer = Printer()
    except:
        from printers.virtual_printer import VirtualPrinter

        g_printer = VirtualPrinter()

    #########################
    # Select which camera driver to use
    #########################
    global g_cameras
    global g_activeCamera
    global g_settings
    dsl_connected = check_dslrCamera()
    pi_camera_connected = check_piCamera()
    webcam_connected = check_webcam()
    ip_camera_conncetd = check_ipcam()

    if dsl_connected:
        try:
            print("[picInABox] Found DSLR camera")
            from cameras.dslrCamera import Camera

            dslrCameraContainer = cameraContainer()
            dslrCamera = Camera()
            dslrCamera.connect(30)
            dslrCameraContainer.fotoCamera = dslrCamera
            dslrCameraContainer.previewCamera = dslrCamera
            dslrCameraContainer.videoCamera = CameraRecorder(dslrCamera)
            dslrCameraContainer.timelapsCamera = CameraTimelapss(dslrCamera)
            g_cameras.append(dslrCameraContainer)
        except Exception as e:
            error = {"status": "Error", "description": "Kein Signal zur Spiegelreflex"}
            g_error.put(error)
            error = {"status": "Error", "description": repr(e)}
            g_error.put(error)
    else:
        g_cameras.append(None)

    if pi_camera_connected:
        try:
            print("[picInABox] Found pi camera")
            from cameras.piCamera import Camera

            piCameraContainer = cameraContainer()
            piCamera = Camera()
            piCamera.connect(30)
            piCameraContainer.fotoCamera = piCamera
            piCameraContainer.previewCamera = piCamera
            piCameraContainer.videoCamera = CameraRecorder(piCamera)
            piCameraContainer.timelapsCamera = CameraTimelapss(piCamera)
            g_cameras.append(piCameraContainer)
        except Exception as e:
            error = {
                "status": "Error",
                "description": "Kein Signal zur RaspberryPi Camera",
            }
            g_error.put(error)
            error = {"status": "Error", "description": repr(e)}
            g_error.put(error)
    else:
        g_cameras.append(None)

    if webcam_connected:
        try:
            print("[picInABox] Found webcam camera")
            from cameras.webcam import Camera

            cvCameraContainer = cameraContainer()
            cvCamera = Camera()
            cvCamera.connect(30)
            cvCameraContainer.fotoCamera = cvCamera
            cvCameraContainer.previewCamera = cvCamera
            cvCameraContainer.videoCamera = CameraRecorder(cvCamera)
            cvCameraContainer.timelapsCamera = CameraTimelapss(cvCamera)
            g_cameras.append(cvCameraContainer)
        except Exception as e:
            error = {"status": "Error", "description": "Kein Signal zur Webcam"}
            g_error.put(error)
            error = {"status": "Error", "description": repr(e)}
            g_error.put(error)
    else:
        g_cameras.append(None)

    if ip_camera_conncetd:
        try:
            print("[picInABox] Found ip camera")
            from cameras.ipCamera import Camera

            ipCameraContainer = cameraContainer()
            ipCamera = Camera()
            ipCamera.connect(30)
            ipCameraContainer.fotoCamera = ipCamera
            ipCameraContainer.previewCamera = ipCamera
            ipCameraContainer.videoCamera = CameraRecorder(ipCamera)
            ipCameraContainer.timelapsCamera = CameraTimelapss(ipCamera)
            g_cameras.append(ipCameraContainer)
        except Exception as e:
            error = {"status": "Error", "description": "Kein Signal zur IP Camera"}
            g_error.put(error)
            error = {"status": "Error", "description": repr(e)}
            g_error.put(error)
    else:
        g_cameras.append(None)

    if pi_camera_connected and dsl_connected:
        g_settings["fotoCamera"] = enCamera.DSLR.value
        g_activeCamera.videoCamera = g_cameras[enCamera.DSLR.value].videoCamera
        g_activeCamera.fotoCamera = g_cameras[enCamera.DSLR.value].fotoCamera
        g_settings["previewCamera"] = enCamera.PI.value
        g_activeCamera.previewCamera = g_cameras[enCamera.PI.value].previewCamera
        g_activeCamera.timelapsCamera = g_cameras[enCamera.PI.value].timelapsCamera
    else:
        for camera in g_cameras:
            if camera != None:
                g_settings["fotoCamera"] = g_cameras.index(camera)
                g_activeCamera.videoCamera = camera.videoCamera
                g_activeCamera.fotoCamera = camera.fotoCamera
                g_settings["previewCamera"] = g_cameras.index(camera)
                g_activeCamera.previewCamera = camera.previewCamera
                g_activeCamera.timelapsCamera = camera.timelapsCamera
                break

    if g_activeCamera.previewCamera != None:
        # start preview camera right away
        g_activeCamera.previewCamera.stream_start()
        frameRaw = g_activeCamera.previewCamera.stream_show()
        while type(frameRaw) != "NoneType" and len(frameRaw) > 0:
            print("[picInABox] Wait for first capture")
            time.sleep(1)
            frameRaw = g_activeCamera.previewCamera.stream_show()
        print("[picInABox] Cameras init done")
        if g_settings["timelaps"] == 1:
            g_activeCamera.timelapsCamera.recording_start()
    else:
        print("[picInABox] No Camera Found")


print("[picInABox] Starting ...")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a port number.")
    parser.add_argument("port", type=int, help="Port number to process")

    args = parser.parse_args()
    print(f"[picInABox] Start PicInABox Web Server on port {args.port}")
    # Other idea app.config["SERVER_PORT"] = 5000 with app.config.get('SERVER_PORT', 'Unknown')
    before_first_request_func(args.port)
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True, use_reloader=False)
