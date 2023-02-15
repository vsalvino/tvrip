from pathlib import Path
from subprocess import DEVNULL, PIPE, Popen
from typing import Dict, IO, List, Tuple, Union
import datetime
import re
import time


DVBTEE = Path("/usr/bin/dvbtee")
WORKDIR = Path("/mnt/WD2TB/worker")
# Channel config obtained from channel scan `dvbtee -s -a0`
# (channel, program number, virtual channel)
CHANNEL = (17, 5, "55.3")


class Program:
    def __init__(self, channel, station, start, end, title):
        self.channel = channel
        self.station = station
        self.start = start
        self.end = end
        self.title = title

    def __eq__(self, obj):
        # Two programs are equal if their attributes match.
        return (
            self.channel == obj.channel
            and self.start == obj.start
            and self.end == obj.end
            and self.title == obj.title
        )

    def __str__(self):
        return f"{self.start} - {self.end} | {self.channel} {self.station} | {self.title}"


def atsc_get_guide():
    # Get the programming guide.
    with Popen(
        [DVBTEE, f"-c{CHANNEL[0]}", f"-I{CHANNEL[1]}", "-E"],
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True,
    ) as proc:
        # Run process and capture output.
        stdout, stderr = proc.communicate()

    # dvbtee provides the programming guide JSON as log output in stderr:
    # dump_epg_event: id:3 - 55.3: Movies!    2023-01-26 07:35-09:15 Danger Signal
    schedule: List[Program] = []
    for line in stderr.splitlines():
        line = line.strip(" \r\n\t")
        if not line.startswith("dump_epg_event:"):
            continue
        m = re.match(
            (
                r"dump_epg_event: id:\d+\s+\-\s+"
                r"(?P<channel>\d+\.\d+):\s+"
                r"(?P<station>[^\t]+)\t"
                r"(?P<year>\d{4})\-"
                r"(?P<month>\d{2})\-"
                r"(?P<day>\d{2})\s"
                r"(?P<s_hour>\d{2}):"
                r"(?P<s_minute>\d{2})\-"
                r"(?P<e_hour>\d{2}):"
                r"(?P<e_minute>\d{2})\s+"
                r"(?P<title>.+$)"
            ),
            line,
        )
        # Only look at the correct virtual channel / program ID.
        if m.group("channel") != CHANNEL[2]:
            continue
        start = datetime.datetime(
            int(m.group("year")),
            int(m.group("month")),
            int(m.group("day")),
            int(m.group("s_hour")),
            int(m.group("s_minute")),
        )
        end = datetime.datetime(
            int(m.group("year")),
            int(m.group("month")),
            int(m.group("day")),
            int(m.group("e_hour")),
            int(m.group("e_minute")),
        )
        # Account for midnight / date rollover.
        if end < start:
            end = end + datetime.timedelta(days=1)
        p = Program(
            channel=m.group('channel'),
            station=m.group("station"),
            start=start,
            end=end,
            title=m.group("title"),
        )
        if p not in schedule:
            schedule.append(p)

    return schedule


# Record continually, naming and terminating each recording based on the guide.
recorder: Popen = None
processor: Popen = None
processor_queue: List[Path] = []
while True:

    # If recorder is blank, scan the guide and start a new recording job.
    if recorder is None:

        # Get current program.
        print("Getting program guide...")
        schedule = atsc_get_guide()
        now = datetime.datetime.now()
        program = None
        for p in schedule:
            if p.start <= now <= p.end:
                program = p
                break
        print(program)

        # Make a Windows-safe filename from the date, channel, and title.
        filename = now.strftime("%Y%m%d_%H%M")
        if program:
            filename = f"{program.station}_{filename}_{program.title}"
            filename = re.sub(r"[\<\>\:\"\/\\\|\?\*]", "", filename)

        # Record.
        rfile = WORKDIR / f"{filename}.ts"
        print("Recording to: ", rfile)
        recorder = Popen(
            [DVBTEE, f"-c{CHANNEL[0]}", f"-I{CHANNEL[1]}", f"-ofile://{rfile}", "-q"],
            stdout=DEVNULL,
            stderr=DEVNULL,
        )

    # TODO: start a processing job for completed recordings in the queue.

    # Sleep until program has ended, or indefinitely.
    if recorder and program:
        print("Sleeping until", program.end)
        slumber = program.end - datetime.datetime.now()
        time.sleep(slumber.total_seconds())
        recorder.terminate()
        recorder = None
        # Queue the recording to be processed.
        processor_queue.append(rfile)
    elif recorder:
        recorder.wait()

