import os
import sys
import hashlib

def init(server):

    """
    Hash self and set an env var to indicate to the Flask app
    that Gunicorn is started with the default config (or not)
    mainly to ensure there is only 1 process.
    """

    env_var_name = "TRIPWIRE_GUNICORN_CFG_SHA256"
    if env_var_name in os.environ:
        print(
            f"The environment variable {env_var_name} is already set before Gunicorn runs.\n"
            "This shouldn't happen because this environment variable should normally be\n"
            "automatically unset when the app exits. Aborted!"
        )
        sys.exit(1)

    with open(__file__, "rb", buffering=0) as f:
        hash_ = hashlib.file_digest(f, "sha256").hexdigest()
        os.environ[env_var_name] = hash_
        print(f"Gunicorn cfg: My SHA256 hash is {hash_}")


# DO NOT HAVE MORE THAN 1 PROCESSES!
# THAT WILL INITIALIZE MULTIPLE RANDOM SECRETS, ONE PER PROCESS!
# THE FLASK APP WILL RETURN ONE OF THOSE RANDOMLY,
# CAUSING FALSE ALARMS!!!
workers = 1
# WE ARE FOLLOWING THE THIRD METHOD OF DEPLOYMENT IN Flask-SocketIO's DOCS.
# THE FIRST TWO ARE EVENTLET AND GEVENT, AND NEITHER SEEMS COMPATIBLE WITH GPIOZERO,
# AND CAUSES FREEZING ON START OR BLOCKING.
# AT LEAST 2 THREADS ARE NEEDED, SO THAT BOTH THE WEB SERVER
# AND GPIOZERO WILL WORK! THE NUMBER OF THREADS NEEDED IS PROBABLY
# THE NUMBER OF CLIENTS MINUS ONE.
threads = 30
on_starting = init
