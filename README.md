# Tripwire: Anti Evil Maid Defense

## What are Evil Maid Attacks?
Evil maid attacks, first defined by Joanna Rutkowska ([source](https://blog.invisiblethings.org/2009/10/15/evil-maid-goes-after-truecrypt.html)), has been a difficult threat to people who care about their device security and personal privacy. In an evil maid attack, the attacker gets physical access to the target device when the user left it at home or in a hotel room. They secretly compromise the device in order to spy on the user's past **and future** activities, without the user ever noticing. Because physical access gives the attacker so much control, currently there is no software or firmware solution that effectively defends against evil maid attacks. Even though there are Secure Boot and Trusted Platform Modules (TPM), it is still possible for the attacker to install something like a hardware keylogger to bypass those defenses.

## How can Tripwire help?
Tripwire is a robust monitoring system **that defends against sophisticated adversaries**. In comparison, traditional home monitoring products can only defend against burglars, who are not technically-sophisticated and only want to steal money. For higher-profile users, such as:
- Developers of critical software (recall the xz backdoor)
- High-ranking officials in businesses/organizations
- Investigative journalists
- Attorneys with high-profile clients
- ...

Traditional monitoring systems can't help them defend against strong adversaries (e.g. professional spies and criminal hackers). A strong adversary will likely disable/jam the network on the premise, and then compromise the target device **and the monitoring system** so that it looks like no intrusion was detected. Additionally, because most of the home monitoring products are for-profit and closed-source, it's possible that they have undiscovered security vulnerabilities. In general, the companies that develop those monitoring products cannot be much trusted either, given past cases where employees in those companies spied on the users. See: https://www.justice.gov/usao-ndtx/pr/adt-technician-pleads-guilty-hacking-home-security-footage

Tripwire's solution is simple. Before the user deploys Tripwire, the server at home, which runs on a Raspberry Pi 5, shares some random secrets with the web client on user's mobile device. After Tripwire is deployed and the user leaves home, they can view a stream of photos which are captured by RPi's camera module and sent to the web client. If any motion is detected by RPi's camera module or motion sensor, the server will delete those secrets immediately, in addition to sending push notifications to the web client. This way, even when the attacker gets physical access to both the target device and the RPi and compromise both of them, they can't restore those secrets. And when the user sees a mismatch between the secrets on the web client and the ones sent from the server, they know that there has been a detection. Here is a demo video for this concept:

https://github.com/user-attachments/assets/2e8fbde4-8e36-4e81-9c1b-c86268d02e73

Other than the secrets, the server also has a separate cryptographic key pair, whose public key is shared with the web client, that signs the first few seconds of photos after detection before the key pair is deleted. This way the user can unmistakably see the brief moment after detection, which either catches a glimpse of the intruder, or shows a false positive, in which case the user can remotely re-arm Tripwire (generating new secrets and key pair). If the user sets up full-disk encryption (FDE) on the RPi, it will make it difficult to tamper with the photo log on the disk as well.

Because of Tripwire's sharing and deletion of the random secrets, the attacker can't cover their track left by the intrusion, even if they temporarily disable the network. It is slightly more challenging if the attacker persistently disables the network, which prevents the user from comparing secrets. But in this case the user can enter the deployment area, power off the RPi, and takes out the SD card. After plugging the SD card on another computer (e.g. a friend's laptop, a random computer at a library), if they see that the photo log has been signed up until the time when they come back and enter the deployment area, then it means Tripwire didn't detect any intrusion other than the user's return. If the signing of the photo log stopped a while before the user's return, then it must mean that Tripwire detected intrusion before the user returns.

In summary, Tripwire is a robust monitoring system that is also tamper-evident by itself. It survives network outage by design, and can also survive power outage if plugged into an uninterrupted power supply (UPS). False positives and false negatives are also easier to identify by reasoning about Tripwire's logic and the artifacts. Those properties will be discussed in more details later on.

## Prerequisites

In order to use Tripwire, you will need:
- Basic familiarity with technology.
  - If not, this document will still show you most of the steps for hardware and software. You may need to look up a few Linux commands or RPi docs though.
  - You can open an issue on this GitHub if you run into difficulty at a certain step.
- Hardware:
  - [A Raspberry Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/)
    - Older models haven't been tested at all.
  - [Raspberry Pi's official 27W USB-C power supply](https://www.raspberrypi.com/products/27w-power-supply/)
    - Lower-wattage power supplies have caused the RPi to randomly power off during tests.
    - You don't want to risk security with unsupported and non-official products.
  - A microSD card.
    - At least 128GB of storage for the hours or even days of photos.
  - [The official Camera Module 3 for Raspberry Pi](https://www.raspberrypi.com/products/camera-module-3/)
  - A ribbon connector that works with RPi 5 and the camera module.
    - Some connectors look similar but don't fit!
  - A passive infrared (PIR) motion sensor.
    - Note that it has to be a PIR motion sensor, which is very cheap (a few dollars), and not a prepackaged motion sensor product, which is more expensive (tens of dollars).
    - [This page](https://projects.raspberrypi.org/en/projects/parent-detector/1) has a good description of what a PIR motion sensor is, what it looks like, and how to connect it to the RPi (except that we are using GPIO pin #17 and not GPIO pin #4 on the RPi).
  - A breadboard to sit the PIR sensor straight, a batch of male-to-female jump wires to connect the RPi 5 with the PIR.
    - You may also need a batch of male-to-male jumpers if you are putting the PIR further on the breadboard.
  - (Strongly recommended) An uninterrupted power supply (UPS) for when there is a power outage or if the attacker cuts the power.
  - (Strongly recommended) A camera holder that is compatible with the camera module so that it can be held up and not flop around with the ribbon connector.
    - You can either buy it somewhere or 3D-print one using open-source designs.
- A domain name.
  - So that you can get TLS certificates for Tripwire's web traffic to be encrypted. Otherwise, Tripwire is trivial to compromise.
  - You should probably get a domain from one of the listed providers in this repository: https://github.com/orgs/caddy-dns/repositories
    - This is to ensure that dynamic DNS will work later on.
- Port forwarding on your home router.
  - Since you will be self-hosting Tripwire at your home and accessing it when you are away from home, port forwarding needs to be set up so that traffic between your client device and the Tripwire server can go through.
  - You can forward a non-standard port (any port between 1024-65535) from the router to port 443 on RPi, so that your log won't be filled with random script kiddies trying to attack common ports.

## Installation

### Choose your deployment area
This is where you place the device you want to protect along with the whole RPi. There can only be one entrance, so that the attacker can't enter and compromise the devices from behind. Very importantly, the room should have no window, so that the difference in ambient light can't trigger false positives with the camera module. There can't be any moving objects at all, so make sure your pets can't enter this area either. The place should also be well lit, probably with room lights, because camera-based motion detection is harder in the dark. If possible, a light source that can survive power outage is highly preferable. Finally, there shouldn't be heat sources in the area either to prevent false positives with the PIR sensor, which detects motion using infrared and heat change.

### Raspberry Pi 5
Set up your Raspberry Pi 5 *as a headless computer* following official docs: https://www.raspberrypi.com/documentation/computers/getting-started.html#installing-the-operating-system
- Make sure you go into "Raspberry Pi OS (other)" and choose "Raspberry Pi OS Lite (64-bit)".

Connect the PIR sensor and the camera module. [This tutorial](https://projects.raspberrypi.org/en/projects/parent-detector/0) has a pretty good walkthrough for both.
- Connect the OUT pin of the PIR sensor to GPIO pin #17 on the RPi instead of #4. Refer to RPi's [pin layout](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio) to see where it is.
- The orientation of the ribbon connector may be different. Double check which side should you plug it in. Generally speaking, the metal pins on the ribbon should touch the metal pins in the socket.
- <span style="color:red;">**NEVER PLUG/UNPLUG THE CAMERA MODULE, THE PIR SENSOR, OR WIRES WHEN THE RPi IS POWERED ON!!!**</span>

After you have set up the headless RPi with PIR sensor and camera module, power it on and SSH into it.

### Tripwire
Clone this repository and its submodules:
```
git clone --recurse-submodules git@github.com:fr33-sh/Tripwire.git
```
Enter the repo's directory:
```
cd Tripwire/
```

### Picamera2
Install Picamera2 from **APT**:
```
sudo apt install python3-picamera2 --no-install-recommends
```
Note: Installing picamera2 from pip probably won't work due to some compatibility issues. See section 2.2 of this [manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf).

### Python virtual environment and dependencies
Create and activate a Python virtual environment with system Python packages included, so that picamera2 will also be available in the virtual environment.
```
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

Install Tripwire's dependencies specified in `requirements.txt`:
```
pip install -r requirements.txt
```

Install pywebpush and Python VAPID tool. Run the following commands after `cd`ing into `pywebpush/`. Do the same for `vapid/python/`.
```
pip install -r requirements.txt
pip install -e .
```

### Checking and tuning the camera module
Tripwire's camera-based motion detection uses a metric called [Structural Similarity Index (SSIM)](https://scikit-image.org/docs/stable/api/skimage.metrics.html#skimage.metrics.structural_similarity), which compares a type of difference between photos. If the SSIM value falls below a pre-configured value, then it considers that motion is detected.

Check if the OS sees the camera:
```
libcamera-still --list-cameras
```
It should show the camera module.

Check that the camera module works by running:
```
libcamera-still --width 800 --height 800 -o test.jpg
```
It should capture a photo using the camera module and save to `test.jpg`. Make sure that `test.jpg` is a photo of reasonable quality.

Next, put the whole RPi at your planned deployment area, and point the camera module toward the only entrance. Set up the area to be similar to when Tripwire is deployed by turning the lights on, closing the door (if any), and so on. Run:
```
python3 cam_tuning.py
```
The script will capture a series of photos and compare the SSIM between the first photo and the latest photo, and the SSIM between each adjacent pair. It will report the minimal SSIMs from these two comparisons. These two minimal SSIMs should be pretty close to each other, and should be preferably above 0.8 and at the very least 0.7. Write down those two values because they will be used later when editing the config.

If the two SSIMs are low, then the area may not be well lit, the camera module may be too close to the door, or the camera module may be faulty. It's also possible that the image of the entrance is too simpmle (e.g. having a uniform color). Maybe putting a paper printed with something colorful and complicated on the door will help.

### Caddy
Install xcaddy following the instruction on its GitHub: https://github.com/caddyserver/xcaddy
Note: If you built it from source with `go install ...`, the built xcaddy binary will probably be located at `/home/pi/go/bin/xcaddy`, or `$GOBIN/xcaddy`. See `go help install`.

Using xcaddy, build Caddy with these two plugins:
1. The dynamic DNS plugin.
2. The specific DNS provider plugin for the domain registrar you are using.
```
xcaddy build --with github.com/mholt/caddy-dynamicdns --with github.com/caddy-dns/<YOUR DNS PROVIDER>
```
Replace <YOUR DNS PROVIDER> with the name of your DNS provider. If you don't know who your DNS provider is, then it is probably the same as your domain registrar (where you get the domain). All available DNS provider plugins can be found here: https://caddyserver.com/docs/modules/. Their names start with a prefix of "dns.providers". The description of each plugin shows the exact URL to be used for the second `--with` in the command. You can also find the GitHub repositories of these DNS provider plugins here: https://github.com/orgs/caddy-dns/repositories

So, if your DNS provider is Duck DNS, then you should run this command:
```
xcaddy build --with github.com/mholt/caddy-dynamicdns --with github.com/caddy-dns/duckdns
```

The built Caddy custom binary `caddy` will be located at whichever directory this command is run. For convenience, move it into a directory on `$PATH`. From here on, it is assumed to be put under `/home/pi/.local/bin/`.

For Caddy to be able to bind to the system ports (0-1023), it needs to have the corresponding capabilities. Otherwise, running Caddy will result in a permission error.
```
sudo setcap CAP_NET_BIND_SERVICE=+eip ~/.local/bin/caddy
```
Note: This is still necessary even if you are serving the web app on non-system ports, because Caddy by default tries to listen to port 80 for automatic HTTPS redirection.

### Setup the instance directory
Each instance of Tripwire deployment needs its own instance directory. You can use the provided example instance directory. You just need to rename it:
```
mv example_instance instance
```

### Configuration
The `instance/config.yaml` file contains both server and client configs.

Server parameters:
- The `MIN_SSIM_VS_INIT` and `MIN_SSIM_VS_NEXT` should be set at about 0.5 to 1 below the two minimal SSIMs acquired when tuning the camera previously.
- `POST_DETECTION.SECS_DEL_KEYS` is the number of seconds before server deletes its private key after detecting motion.
  - This parameter refers to the private key and not the secrets. The secrets are deleted immediately upon detection.
  - The value should be determined by the distance between where your protected device and Tripwire are, and where the attacker will enter the area. The keys should be deleted shortly before the attacker can run to the RPi and compromise it. Assume they can compromise it instantly after reaching the RPi.
    - For example, if you estimate the attacker to spend 0.5 seconds opening the door (which triggers detection), and 3 seconds to run to the RPi, then 2 seconds may be a safe value for this parameter.
- `KEEPS_PHOTOS_IN_MEM_FOR`: The number of seconds server will keep a photo in memory before moving it to disk.
  - This should be determined by how big the RAM is and how big each photo is.
- `KEEPS_PHOTOS_IN_DISK_FOR`: The number of seconds server will keep a photo on disk before deleting it.
  - This should be determined by how big the microSD card is and how big each photo is.

Client parameters:
- `MAX_NUM_PHOTOS_IN_MEM`: The maximal number of photos client will keep in memory before moving older ones into IndexedDB or deleting them.
- `SECS_PHOTOS_TO_MOVE_TO_FREE_MEM`: How many seconds worth of photos to move to IndexedDB or to delete when `MAX_NUM_PHOTOS_IN_MEM` is reached.

### Generate VAPID key pair
A VAPID key pair is needed for Tripwire's Flask server to send out web push notifications. Run this command under `instance/vapid/`.
```
vapid --gen
```
Note: Do not rename the generated keys.

### Environment Variables
Create a shell script named `tripwire.caddy.env.sh` that exports some environment variables upon execution. These variables will be automatically plugged into Caddy's config file `Caddyfile`. It is recommended to put this script outside of Tripwire's directory to avoid accidentally committing and leaking it to Git. The content of the shell script should be:
```
export TRIPWIRE_DOM_REG='...'
export TRIPWIRE_DOM_REG_TOK='...'
export TRIPWIRE_DOM='...'
export TRIPWIRE_USER='...'
export TRIPWIRE_PW='...'
```
Note: The single quotes around the ... are necessary, especially for `TRIPWIRE_PW`. The script will break without them.

Here is an explanation for these environment variables:
- `TRIPWIRE_DOM_REG` should be the name of your domain registrar or DNS provider.
- `TRIPWIRE_DOM_REG_TOK` should be the API token provided by your domain registrar or DNS provider.
  - Research online to see how you can get an API token with the domain registrar that you use.
- `TRIPWIRE_DOM` should be the domain name you got for Tripwire.
- `TRIPWIRE_USER` should be the username you want to use for Caddy's Basic Auth.
- `TRIPWIRE_PW` should be the **HASHED AND ENCODED** passphrase you want to use for Caddy's Basic Auth. To generate the hashed and encoded passphrase: 
  - First, generate a secure random passphrase using tools like KeePassXC. You probably want a "passphrase" made with several (at least 6) English words, rather than a "password" made with a long string of random character, so that you can actually type it when you are accessing Tripwire on a mobile device when you are away from home.
  - Second, run `caddy hash-password`. At the prompt, paste in your plaintext passphrase. It will return the hashed and encoded passphrase, which you can paste after `TRIPWIRE_PW`.

An example of `tripwire.caddy.env.sh`:
```
export TRIPWIRE_DOM_REG='duckdns'
export TRIPWIRE_DOM_REG_TOK='abcde'
export TRIPWIRE_DOM='my-tripwire.com'
export TRIPWIRE_USER='Alice'
export TRIPWIRE_PW='$2a$14$.lGj0kTww2Mi1Z0daBbd9eG/WxHzNjQ6Feo/it5IWPODFtYYFhg2e'
```

Create another shell script named `tripwire.flask.env.sh` with the content as:
```
export TRIPWIRE_VAPID_APP_SERVER_KEY='...'
```
The value here can be obtained by running `vapid --applicationServerKey` under `instance/vapid/`.

### Starting Tripwire
Now you should be able to start Tripwire. Spawn one terminal for Gunicorn and Flask:
```
source tripwire.flask.env.sh
source venv/bin/activate
gunicorn -c gunicorn_config.py 'tripwire:create_app()'
```

Spawn another terminal for Caddy:
```
caddy run --config Caddyfile
```

See if there are any errors from either terminal. If not, you can browse to https://<your-domain> on your phone, or https://<your-domain>:<port> if you forwarded a different port on your router, enter the credentials you've set up for Caddy's Basic Auth, and get to Tripwire's web client!

### Deploying Tripwire
The first thing you need to do is installing Tripwire as a Progressive Web App (PWA), especially on iPhones. This enables Tripwire to send you web push notifications, which is crucial when Tripwire detects intrusion. After installing and opening the PWA, you need to click "Enable Push Notification" to enable it, at least on iPhones. 

When you are about to deploy Tripwire, start by adjusting the angle of the camera module until it covers the entrance properly. You can click the "Preview" button under the "Live Photos" section to see where the camera module currently captures. Note that the preview is just a static photo so you will need to click "Preview" again after every adjustment. If the device you want to protect is the same one which you use to access Tripwire's server, make the adjustment before you shut down the device.

When you are happy with the camera angle, you can put your target device into the deployment area. Make sure it doesn't change too much of the camera's view, so that the pre-configured SSIM thresholds won't be affected. After you left the deployment area and closed the door, click the "Arm" button, and Tripwire will start detecting any intrusion. If you need to make further adjustment to the deployment area, or want to test the intrusion detection, you can do it and then click "Re-arm" to reactivate the deployment.

After Tripwire's deployment starts, you will see one secret for the PIR sensor and one secret for the camera module under the "Secrets" section. The "Stored" secret is what the server first shared with the web client, and the "Received" secret is what the server sends every second. Although the web client compares the stored and received secrets automatically, you still need to save the two secrets somewhere (e.g. on your phone) because sometimes the web client loses the stored secret after reloading itself. You also need to save the server's public key in PEM format below, if you need to manually verify the signatures on the microSD card in case of persistent network outage. Never let anyone else know what the secrets are.

As the photo stream comes in, each photo has a header bar showing its metadata, which includes:
- The time of when the camera module captures the photo
- Whether the photo is stored in the client's memory (MEM), retrieved from the client's IndexedDB (DB), or re-acquired from the server (REGET)
- Whether the PIR and camera secrets were good when this photo was captured
  - If the PIR secret was good at time of capture, it will show the text "PIR" with a green background. Otherwise, it will show the text "Bad PIR with a red background. Same with the camera secret.
- Whether the photo comes with no signature (NO SIG), with a signature but the browser doesn't support signature verification (CANT SIG), with a bad signature (BAD SIG), or with a good signature (GOOD SIG).

Most other features are self-explanatory. Click the "Re-acquire Missing Photos" button to re-request photos lost during past temporary network outages. Click "Freeze" button to freeze the photo grid so that you can examine certain photos. Pagination is set up conveniently so that if you want to see the photos from 5 minutes ago and "Photos Per Page" is set to 60, you can just go to page number 5, because photos are captured every second.

### Intrusion detection
When Tripwire detects intrusion, the server will send web push notifications to the client, if the network is available. The server will also immediately delete the secret of the sensor that made detection. The web client will initially show "null" as the received secrets, until the attacker compromises the server and sends back fake secrets. Any of these should mismatch with the ones you previously saved. Starting from this point, the header bar of each photo will show a red background with the text "BAD" for the sensor that detected intrusion.

Before the server deletes the key pair, it will send back photos with signatures. If the web client successfully verified the signatures, the header bar of these photos will show "GOOD SIG" in a blue background. You should use these photos to determine if the detection is a true or false positive. If it's a false positive, click the "Re-arm" button to remotely restart the deployment, and new secrets and new public key will be exchanged. If the browser doesn't support verifying the signature, which is using the ed25519 algorithm, then the header bar will show "CANT SIG" in orange. If the web client verified that these signatures are invalid, then the header bar will show "BAD SIG" in red. Theoretically it means that an attacker must be tampering with the server. But in practice, some browser may show "BAD SIG" when in fact its signature verification mechanism is faulty. Make sure you avoid using these browsers that doesn't support ed25519 signature verification, or has faulty ed25519 signature verification. So far this includes the Brave Browser on Linux Desktop.

It is strongly recommended that you test the intrusion detection with yourself a few times to get familiar with Tripwire's user interface.

### Network outage
If the network is temporarily disabled, then you can simply click "Re-acquire Missing Photos". Secrets comparison and signature verification will still work. If the network is persistently disabled, then you can't compare the secrets from the web client. In this case, you will need to enter the deployment area, power off the RPi, and take out the microSD card. Plug the microSD card into a computer other than the device you were protecting, because you can't trust that it wasn't compromised yet. You can use a friend's laptop or a random computer in a random public library.

Create a file named `pubkey.pem` and paste in the server public key PEM that you saved earlier. Then, download the script named `verify_sigs.sh` from Tripwire's GitHub repository, and run it against the directory that contains all the photos and their signature files. The command should look like this:
```
./verify_sigs.sh pubkey.pem instance/captures/
```
Replace `instance/captures/` with the full path to the `instance/captures/` directory on the microSD card. The script will verify all photos who have signatures. If any signature is verified to be invalid, then an attacker has probably tampered with the photos. If the photos stopped having signatures a while before the user returns to the deployment area, then an attacker has probably been detected.

*Note: verify_sigs.sh hasn't been implemented yet. You can still verify signature for one photo manually. Let pubkey.pem contain the public key in PEM format that you copied from the web client. Let str.txt be 'YYYY-mm-dd HH:MM:SS,<hash>' without trailing new line, where '<hash>' is the target photo's SHA256 hash. Let <sig> be the target photo's signature file. The command is:*
```
openssl pkeyutl -verify -pubin -inkey pubkey.pem -rawin -in str.txt -sigfile instance/captures/<sig>
```

## Limitation
Currently it is unclear how to securely delete a piece of data (in our case: the secrets) from the disk and the memory, so that it cannot be recovered. Suggestions are welcome.

## Inspiration
Tripwire is inspired by [Haven](https://github.com/guardianproject/haven), which is a previous anti evil maid system that also detects intrusion with sensors. In comparison, Tripwire is more robust and has more features, while Haven is easier to set up. Unfortunately, Haven has been broken due to difficulty with sending notifications to the user and other problems (See their latest issues [here](https://github.com/guardianproject/haven/issues)).
