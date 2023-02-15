tvrip
=====

TV ripper that automatically records individual programs based on channel and EPG program guide.


Depedencies
-----------

* Any modern version of Python 3

* Compile a working build of [libdvbtee](https://github.com/mkrufky/libdvbtee)


Installation
------------

* Clone the repository.

* Scan for channels with:
  ```
  dvbtee -s -a0 > channels.txt
  ```

* Edit the globals at the top of `tvrip.py` to specify the path to `dvbtee`, the working directory where files will be saved, and the channel you would like to record (channel info can be found in `channels.txt` from previous step).

* Optional - an example systemd service (`tvrip.service`) is provided. Edit this file with the correct paths and enable it:
  ```
  sudo cp tvrip.service /etc/systemd/system/
  ```


Usage
-----

Start a recording:
```
python3 tvrip.py
```

Or run the systemd service:
```
sudo systemctl start tvrip
```

This will read the EPG program guide, and automatically start/stop recordings based on the schedule of the selected channel. It will continue to create recordings indefinitely until stopped. If the EPG cannot be read, then it will record a continuous stream indefinitely until stopped.

The outputted `.ts` files are MPEG Transport Streams which contain a single program, plus captions, etc. To play them, use `mplayer` or `ffplay`.

Note: in order to update the EPG, it is re-scanned between recordings. This may result in a 5-30 second gap between recordings. Usually this timeslot is filled with commercials anyways.


Future ideas
------------

* Config file to control program options.

* Support multiple DVB adapters to record simultaneously.

Post-processing:

* Remove commercials using black frame detection (ffmpeg)

* Extract captions to subtitles file.

* Convert finished recordings to mp4.

* Continuously read EPG while recording, to avoid having to re-scan it between recordings.
