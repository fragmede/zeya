# System Libs
import fcntl
import os
import subprocess

try:
    subprocess.Popen.terminate
except AttributeError:
    def sub_popen_terminate(self):
        # This will only work on Unix-like systems, but it's better than
        # nothing.
        import signal
        os.kill(self.pid, signal.SIGTERM)
    subprocess.Popen.terminate = sub_popen_terminate

import thread
import time

# Zeya Imports
from BlockingList import BlockingList
from OggReader import OggPacketReader
#import thread

"""
How many threads are needed?
3:

    1. read input, send to encoder
    2. the webserver, which also happens to stuff the dispatch list
    3. output must be free-wheeling as the beginning will have headers that
       shouldn't be time limited

"""

class GlobalRadioHandler(object):
    def __init__(self):
        self.streams = {}

    def stream_requested(self, name):
        if name not in self.streams:
            return 404
        return self.streams[name]

# Raw Bitrate is
#    44.1 kHz (samples / second) *
#    16 bits per sample *
#    2 channels /
#    8 bit / byte
IN_BUF_SIZE = 44100 * 16 * 2 / 8

def oggenc():
    encode_command = "/usr/bin/oggenc --quiet --raw -b 64 --managed -m 60 -m 70 --raw-bits 16 --raw-chan 2 --raw-rate 44100 -"

    return subprocess.Popen(encode_command.split(),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                           )

class ProcessIO(object):
    def __init__(self, process):
        self.process = process

    def write(self, data):
        self.process.stdin.write(data)

    def read(self, data_len):
        return self.process.stdout.read(data_len)

    def terminate(self):
        self.process.terminate()

class RadioStation(object):
    def __init__(self):
        self.headers = []

        self.input = None
        self.input_process = None

        self.output = ProcessIO(oggenc())
        self.listeners = BlockingList()

        self.threads_should_run = True
        self.start_threads()

    def start_threads(self):
        thread.start_new_thread(lambda :self.input_proc(), ())
        thread.start_new_thread(lambda :self.output_proc(), ())
        # 3rd thread is main thread that created this object
        # (there is also an exec'd oggenc process)

    def stop_threads(self):
        self.threads_should_run = False
        self.output.process.stdin.close()
        self.output.process.wait()

    def input_proc(self):
        """ time.sleep limited absolute bitrate
        does not need locking due to time limit?
        writes must (end up) blocking
        """
        while self.threads_should_run:
            self.input_work_unit()
            time.sleep(1) # TODO - efficiency?

    def input_work_unit(self):
        #if self.input is None:
        #    in_buf = '\x00' * IN_BUF_SIZE
        #else:
        #    in_buf = self.input.read(IN_BUF_SIZE)
        if self.input is None:
            return
        in_buf = self.input.read(IN_BUF_SIZE)
        print 'in unit', len(in_buf)
        self.output.write(in_buf)

    def output_proc(self):
        """ free wheeling as long as there is output """
        while True: #self.threads_should_run:
            self.listeners.acquire()
            while len(self.listeners):
                self.output_work_unit()
            self.listeners.release()

        for listener in self.listeners:
            listener.close()


    def output_work_unit(self):
        packet = OggPacketReader(self.output)
        if packet.is_header():
            self.headers.append(packet)
        for listener in self.listeners:
            listener.write(packet.data)
            listener.flush()

    def add_listener(self, listener):
        for packet in self.headers:
            listener.write(packet)
        self.listeners.append(listener)

def main():
    r = RadioStation()
    r.input = open('2.raw', 'rb')
    out = open('output.ogg', 'wb')
    r.add_listener(out)
    time.sleep(4)
    r.stop_threads()
    time.sleep(1)
    out.close()


if __name__ == "__main__":
    main()
