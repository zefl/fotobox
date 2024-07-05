from appPicInABox import *

before_first_request_func()

if __name__ == "__main__":
    print("[picInABox] Start PicInABox Application")
    app.run(host = '0.0.0.0', threaded = True, port = 80)