## Testing
Tripwire is a new project. Right now it needs a lot of testing. You can follow the setup instructions on README and test if anything doesn't work on the default RPi 5 and Raspberry Pi OS Lite (64-bit). You can also test if Tripwire works on models other than RPi 5 or other OS.

Tripwire's server runs a few threads for Flask, the camera module, and the PIR sensor. It is possible for race conditions or duplicate threads to exist. If you are good at testing and debugging those kinds of problems, please help!

Tripwire's current caching of photos in IndexedDB on the client doesn't seem very robust. A closer look is appreciated.

Tripwire's client has only been tested on an iPhone. You can help by testing if Tripwire's client can run on different phones, different phone OS, different browsers, etc.

It will be helpful to test if Tripwire can run for a longer period of time, e.g. days, weeks, or even months, and still have everything work as expected.

If you find anything interesting in any of those tests (including successful cases such as Tripwire running on un-tested setup, or Tripwire being able to run for weeks), open an issue to report your finding.

## Limitations
If you have an idea for addressing any of the limitations described in the README, open an issue.

## Security
If you find a way to defeat Tripwire or if you find other security problems, open an issue.

## Confusion
If you **have tried your best to read the instructions and educate yourself about unfamiliar concepts** and are still confused by any of this, ask your questions in a new issue.

## Coding (not so fast)
Right now the only obstacle in implementing new features is the limitation of my time, rather than any technical challenge. So please don't jump into implementing a big feature yourself.

Small bug fixes are welcome. Typos not so much, unless if they significantly alter the meaning.
