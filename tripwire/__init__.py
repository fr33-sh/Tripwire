from flask import Flask, request, abort
from flask_socketio import SocketIO
from gpiozero import MotionSensor
from picamera2 import Picamera2
import PIL
from tripwire.ssim import ssim
from pywebpush.pywebpush import webpush, WebPushException
import secrets
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from hashlib import sha256
from threading import Thread
import time
from time import sleep
import yaml
import os
import sys
import subprocess
from datetime import datetime
import io
from base64 import b64encode
import random
import json


class SensorSecret:
    def __init__(self, secret_max = 1000000):
        self.secret = secrets.randbelow(secret_max)
        self._is_destroyed = False
        # TODO: Init a key pair?

    def destroy(self):
        """
        Overwrite the secret before setting to None.
        """
        self.secret = secrets.randbits(64)
        self.secret = None
        self._is_destroyed = True

    def is_destroyed(self):
        return self._is_destroyed

class Keys:
    def __init__(self):
        self.privkey = Ed25519PrivateKey.generate()
        self.pubkey = self.privkey.public_key()
        self.pubkey_pem = self.pubkey.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        # Not needed for now. Just saving as a reference.
        self.privkey_pem = self.privkey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )


def create_app():

    # Enforce that Gunicorn used its default config to start the app.
    gunicorn_cfg_hash = os.environ.get("TRIPWIRE_GUNICORN_CFG_SHA256")
    assert gunicorn_cfg_hash, \
        ("\nThe env var for Gunicorn config hash isn't set. Unless you are developing\n"
        "or testing Tripwire, it should be started using Gunicorn. If you really\n"
        "want to start it in a different way, you need to forge the env var\n"
        "or modify the code.")
    expected_hash = "45ce857206653052d04a60c1777eb45b781c1bfc2c357e8509099dc39539185e"
    assert gunicorn_cfg_hash == expected_hash, \
        ("\nThe env var of Gunicorn config hash doesn't match with the default.\n"
        "Unless you are developing or testing Tripwire, using a Gunicorn config\n"
        "different from the default is discouraged. This is mainly to ensure that\n"
        "Tripwire runs in a single process, and uses other recommended settings.\n"
        "If you really want to use a non-default Gunicorn config, you need to\n"
        "anually forge the env var or modify the code.")


    server_start_time = time.time()

    pir = MotionSensor(17)

    sensor_secrets = {
        "pir": SensorSecret(),
        "cam": SensorSecret()
    }

    # TODO: Should each sensor get its own key pair?
    keys = Keys()

    # Keep all image data sent through Socket.IO within the last ? minutes.
    all_img_data = {}

    # A dict is better than an array for the idempotence of PUT.
    push_subs = {}

    detection_time = None


    def probe_pir():
        while True:
            if pir.motion_detected:
                print("PIR motion is detected!")
                sensor_secrets["pir"].destroy()
                push_notify("Motion detected by PIR sensor!")

                nonlocal detection_time
                if detection_time == None:
                    detection_time = datetime.now()

                return

            sleep(0.5)


    def probe_cam():

        init_img_arr = picam.capture_array()  # 3D array

        # Continuously capture images and compare SSIMs.
        curr_img_arr = init_img_arr
        while True:
            nonlocal detection_time, keys

            iter_start_time = time.time()

            next_img_arr = picam.capture_array()

            # Only compare SSIMs if the cam secret isn't destroyed yet,
            # which means the camera hasn't detected anything.
            # Do this regardless of whether the PIR sensor detected anything.
            if not sensor_secrets["cam"].is_destroyed():
                ssim_vs_init = ssim(init_img_arr, next_img_arr)
                ssim_vs_next = ssim(curr_img_arr, next_img_arr)

                if ssim_vs_init < app.config["SERVER"]["MIN_SSIM_VS_INIT"]:
                    print("The SSIM between the initial and latest photos exceeds the threshold!")
                    sensor_secrets["cam"].destroy()
                    push_notify("Motion detected by camera!")
                    if detection_time == None:
                        detection_time = datetime.now()
                if ssim_vs_next < app.config["SERVER"]["MIN_SSIM_VS_NEXT"]:
                    print("The SSIM between the two latest photos exceeds the threshold!")
                    sensor_secrets["cam"].destroy()
                    push_notify("Motion detected by camera!")
                    if detection_time == None:
                        detection_time = datetime.now()

            curr_img_arr = next_img_arr

            # Convert the Numpy image array to JPEG, then to Base64.
            curr_img_buf = io.BytesIO()
            curr_img = PIL.Image.fromarray(curr_img_arr)
            curr_img.save(curr_img_buf, format="JPEG")
            # `getvalue` gets the entire content while
            # `read` would require a `seek(0)`.
            curr_img_bytes = curr_img_buf.getvalue()
            curr_img_b64 = b64encode(curr_img_bytes).decode("utf-8")

            # Get the time again because comparing SSIMs could take time.
            datetime_ = datetime.now()

            curr_img_data = {
                "timestamp": datetime_.timestamp(),
                "image_b64": curr_img_b64,
                "reget": False
            }

            # Sign and save.
            # Has detected something
            if detection_time != None:
                # Within the signing window after detection
                if (datetime_ - detection_time).seconds < \
                    app.config["SERVER"]["POST_DETECTION"]["SECS_DEL_KEYS"]:
                    sig = sign_photo_and_save(keys.privkey, datetime_, curr_img_bytes)
                    sig_b64 = b64encode(sig).decode("utf-8")
                    curr_img_data["sig_b64"] = sig_b64
                # Past the signing window after detection
                else:
                    # Try to erase the private key.
                    keys.privkey = random.randint(10000000, 99999999)
                    # Just save the photo.
                    datetime_str = datetime_.strftime("%Y-%m-%d %H:%M:%S")
                    with open("./instance/captures/" + datetime_str + ".jpg", "wb") as f:
                        f.write(curr_img_bytes)
            # No detection
            else:
                sign_photo_and_save(keys.privkey, datetime_, curr_img_bytes)

            # Broadcast the image Base64 to clients via Socket.IO
            emit_and_record_img_data(curr_img_data)

            # Maintain the iteration to be 1-second long if it's too fast.
            # Note: If the resolution is high, e.g. 1920x1080, it takes longer than
            #       a second to compute the SSIM of two images!
            secs_elapsed = time.time() - iter_start_time
            if secs_elapsed < 1:
                sleep(1 - secs_elapsed)
            elif secs_elapsed > 2:
                print(
                    f"An iteration of `probe_cam` took {secs_elapsed} "
                    "seconds which is too long."
                )


    def push_notify(msg):
        for endpoint, sub in push_subs.items():
            try:
                webpush(
                    sub,
                    msg,
                    vapid_private_key="/home/pi/tripwire/instance/vapid/private_key.pem",
                    vapid_claims={"sub": "mailto:test@test.test"}
                )
            except WebPushException as e:
                print(e)


    def sign_photo_and_save(privkey, datetime_, photo_bytes):
        # Sign the date time followed by the image's hash.
        datetime_str = datetime_.strftime("%Y-%m-%d %H:%M:%S")
        img_hash = sha256(photo_bytes).hexdigest()
        signed_str = datetime_str + "," + img_hash
        sig = privkey.sign(signed_str.encode("utf-8"))
        # Save the image and the sig.
        base_path = "./instance/captures/" + datetime_str
        img_path = base_path + ".jpg"
        sig_path = base_path + ".sig"
        with open(img_path, "wb") as f:
            f.write(photo_bytes)
        with open(sig_path, "wb") as f:
            f.write(sig)
        return sig


    def emit_and_record_img_data(img_data):
        socketio.emit("image broadcast", img_data)
        # Record.
        nonlocal all_img_data
        timestamp = round(img_data["timestamp"])
        all_img_data[timestamp] = img_data
        # Remove old photos from memory every 5 minutes.
        if len(all_img_data) > app.config["SERVER"]["KEEP_PHOTOS_IN_MEM_FOR"] + 300:
            timestamp_now = time.time()
            all_img_data = {
                k: v for k, v in all_img_data.items() \
                if timestamp_now - v["timestamp"] <= app.config["SERVER"]["KEEP_PHOTOS_IN_MEM_FOR"]
            }
        # TODO: Remove even older photos from disk too.


    app = Flask(__name__, instance_relative_config=True)
    app.config.from_file("config.yaml", load=yaml.safe_load)
    socketio = SocketIO(app)
    probe_pir_thread = Thread(target=probe_pir)
    probe_cam_thread = Thread(target=probe_cam)

    # Config the camera with the same config from camera tuning,
    # because the camera should be used the same as how it was tuned.
    with open("./cam_tuning.yaml") as f:
        cam_tuning_config = yaml.safe_load(f)
    picam = Picamera2()
    cam_pic_config = picam.create_still_configuration(
        main={
            "size": (
                cam_tuning_config["img_width"],
                cam_tuning_config["img_height"]
            )
        }
    )
    picam.configure(cam_pic_config)
    picam.start()


    def secrets_broadcast():
        while True:
            iter_start_time = time.time()

            # Include the hash of the public key.
            pubkey_path = './instance/pubkey.pem'
            if os.path.isfile(pubkey_path):
                pubkey_hash = subprocess.check_output(
                    ["shasum", "-a", "256", pubkey_path],
                    stderr=subprocess.STDOUT
                ).decode("utf-8")
            else:
                pubkey_hash = None

            secrets = {
                "pir": sensor_secrets["pir"].secret,
                "cam": sensor_secrets["cam"].secret,
                "pubkey_hash": pubkey_hash
            }

            # Having no client context assumes `broadcast=True`
            socketio.emit("secrets broadcast", secrets)

            # Maintain the iteration to be 1-second long if it's too fast.
            secs_elapsed = time.time() - iter_start_time
            if secs_elapsed < 1:
                sleep(1 - secs_elapsed)
            elif secs_elapsed > 2:
                print(
                    f"An iteration of `broadcast_secrets` took {secs_elapsed} "
                    "seconds which is too long."
                )

    @app.route("/bootstrap")
    def bootstrap():
        return {
            "pubkey_pem": keys.pubkey_pem.decode("utf-8"),
            "server_start_time": server_start_time,
            "client_config": app.config["CLIENT"]
        }

    isArmed = False
    @app.route("/arm")
    def arm():
        nonlocal isArmed
        if not isArmed:
            # TODO: With Flask, is it a good idea to probe sensors in a thread?
            #       And will it be better to use gpiozero callbacks?
            # Note: With a thread, pressing Ctrl-C doesn't seem to
            #       immediately stop the program. Why?
            probe_pir_thread.start()
            probe_cam_thread.start()
            socketio.start_background_task(secrets_broadcast)

            isArmed = True
            return "You armed the server.", 200
        else:
            return "The server is already armed!\r\n" \
                "If you see this, there may be a bug somewhere." , 409

    @app.route("/re-arm")
    def re_arm():
        nonlocal detection_time, keys, probe_pir_thread, probe_cam_thread

        # Re-generate the secrets and keys.
        sensor_secrets["pir"] = SensorSecret()
        sensor_secrets["cam"] = SensorSecret()
        keys = Keys()

        detection_time = None

        # Restart the PIR thread if it stopped.
        if not probe_pir_thread.is_alive():
            probe_pir_thread = Thread(target=probe_pir)
            probe_pir_thread.start()
            print("Restarted the PIR thread.")
        assert probe_cam_thread.is_alive(), "How has the cam thread stopped?"

        return {
            "pir": sensor_secrets["pir"].secret,
            "cam": sensor_secrets["cam"].secret,
            "pubkey_pem": keys.pubkey_pem.decode("utf-8")
        }

    @app.route("/preview")
    def preview():
        photo_buf = io.BytesIO()
        picam.capture_file(photo_buf, format="JPEG")
        photo_bytes = photo_buf.getvalue()
        photo_b64 = b64encode(photo_bytes).decode("utf-8")
        return photo_b64

    @app.route("/vapid-app-server-key")
    def get_vapid_app_server_key():
        key = os.environ.get("TRIPWIRE_VAPID_APP_SERVER_KEY")
        if not key:
            return "The server hasn't set up a VAPID app server key", 500
        return key

    # This handles both new subscriptions and re-subscriptions after expiration.
    @app.route("/register-push-subscription", methods = ["PUT"])
    def register_push_subscription():
        req_json = request.get_json()
        print(f"Received push subscription registration from a client: {req_json}")

        # Remove the expired sub, if any.
        old_sub = req_json["old_sub"]
        if old_sub:
            if push_subs.pop(old_sub["endpoint"], None):
                print(f"Removed an expired push subscription: {old_sub}")
            else:
                print(
                    "Client gave an expired subscription for removal but it doesn't "
                    "exist in `push_subs`!"
                )

        new_sub = req_json["new_sub"]

        # Use the endpoint as a unique identifier of each subscription.
        push_subs[new_sub["endpoint"]] = new_sub

        return "Received", 200

    @socketio.on("reget photos")
    def reget_photos(json_str):
        targetTimestamps = json.loads(json_str)["timestamps"]
        truly_miss_timestamps = []
        for t in targetTimestamps:
            if not t in all_img_data:
                truly_miss_timestamps.append(t)
                continue
            img_data = all_img_data[t]
            img_data["reget"] = True
            socketio.emit("image broadcast", img_data)
        # If this happen, it should be a bug.
        if len(truly_miss_timestamps) > 0:
            print(
                f"Client tries to reget photos but we don't have these timestamps: "
                f"{truly_miss_timestamps}"
            )

    return app
