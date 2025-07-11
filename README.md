# Tripwire: Anti Evil Maid Defense

## What are Evil Maid Attacks?
In an evil maid attack, the attacker gets physical access to the target device and compromise it. Their goal is to spy on the user's past **and future** activities on that device, without the user ever noticing. Because physical access gives the attacker so much control over the device, currently there is no software or firmware solution that can effectively defend against evil maid attacks. Even though there are Secure Boot and Trusted Platform Modules (TPM), it is still possible for the attacker to install something like a hardware keylogger to bypass those defenses.

## How can Tripwire help?
Start by thinking of Tripwire as a home monitoring system. However, traditional home monitoring products can only defend against burglars, who are not technically-sophisticated and only want to steal money. They can't help high-profile users (e.g. whistleblowers, journalists, developers/maintainers of critical software) defend against strong adversaries (e.g. professional spies and criminal hackers). A strong adversary will likely disable the network on the premise, and then compromise the target device and the monitoring system so that it will look like no intrusion was detected. Additionally, because mose of the home monitoring products are for-profit and closed-source, it's possible that they collude with the adversary as well.

Tripwire's solution is simple. Before the user deploys Tripwire, the server at home shares some random secrets with the client on user's mobile device. After Tripwire is deployed and user leaves home, if Tripwire detects any motion with its camera module or motion sensor, it will delete those secrets immediately. This way, even when the attacker gets physical access to both the target device and Tripwire's server and compromise both of them, they can't restore those secrets. And when the user sees a mismatch between the secrets on the client and the ones sent from the server, they know that there has been an intrusion. The server also has a separate cryptographic key pair that signs the first few seconds of photos after detection, before the key pair is deleted. This way the user can unmistakably see the brief moment after detection, possibly catching a glimpse of the intruder. If the user set up full-disk encryption (FDE) on Tripwire's server, it will make it difficult to tamper with the full photo log on the disk as well.

In summary, Tripwire is a robust monitoring system that is also tamper-evident by itself. It survives network outage by design, and can also survive power outage if plugged into an uninterrupted power supply (UPS). False positives and false negatives are also easier to identify by reasoning about Tripwire's logic and the artifacts. Those properties are discussed in later sections of this document.

## Prerequisite

In order to use Tripwire, you will need:
- Hardware:
  - A Raspberry Pi 5
    - Older models haven't been tested at all.
  - The official Camera Module 3 for Raspberry Pi.
  - A ribbon connector that works with RPi 5 and the camera module.
    - Some connectors look similar but don't fit!
  - (Strongly recommended) A camera holder that is compatible with the camera module so that the camera can be held up and not flop around.
  - A passive infrared (PIR) motion sensor.
  - A breadboard and jump wires to connect the RPi 5 with the motion sensor.
- A domain name.
  - So that Tripwire's web traffic will be encrypted. Otherwise, Tripwire is trivial to compromise.
  - You should probably get a domain from one of the listed providers in this repository: https://github.com/orgs/caddy-dns/repositories
    - This is to ensure that dynamic DNS will work later on.
- Port forwarding on your home router.
  - Since you will be self-hosting Tripwire at your home and accessing it when you are away from home, port forwarding needs to be set up so that traffic between your client device and the Tripwire server can go through.

TODO: Show/link references, add details.

## Installation

### Picamera2
Install Picamera2 from **APT**:
```
sudo apt install python3-picamera2 --no-install-recommends
```
Note: Installing picamera2 from pip probably won't work due to some compatibility issues. TODO: Link to the PiCam docs that talks about this.

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

Install pywebpush and Python VAPID tool. Run the following commands under `pywebpush/` as well as under `vapid/python/`.
```
pip install -r requirements.txt
pip install -e .
```

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
- The `MIN_SSIM_VS_INIT` and `MIN_SSIM_VS_NEXT` should be set when tuning the camera.
- `POST_DETECTION.SECS_DEL_KEYS` is the number of seconds before server deletes its private key after detecting motion.
  - Note: This parameter refers to the private key and not the secrets. The secrets are deleted immediately upon detection.
- `KEEPS_PHOTOS_IN_MEM_FOR`: The number of seconds server will keep a photo in memory before moving it to disk.
- `KEEPS_PHOTOS_IN_DISK_FOR`: The number of seconds server will keep a photo on disk before deleting it.

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

### TODO: Set up gunicorn.

### Running Tripwire
Now you should be able to run Tripwire. Spawn one terminal for Gunicorn:
```
source tripwire.flask.env.sh
source venv/bin/activate
gunicorn -c gunicorn_config.py 'tripwire:create_app()'
```

Spawn another terminal for Caddy:
```
caddy run --config Caddyfile
```

See if there are any errors from either terminal. If not, you can browse to your domain name on your phone, enter the credentials you've set up for Caddy's Basic Auth, and start using Tripwire!

TODO: Explain the different features on the UI.
