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
    encode_command = "/usr/bin/oggenc --quiet --raw -b 64 --raw-bits 16 --raw-chan 2 --raw-rate 44100 -"

    rval = subprocess.Popen(encode_command.split(),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                           )
    attrb = fcntl.fcntl(rval.stdout.fileno() , fcntl.F_GETFL, os.O_NONBLOCK)
    fcntl.fcntl(rval.stdout.fileno() , fcntl.F_SETFL, attrb & (~os.O_NONBLOCK))

    attrb = fcntl.fcntl(rval.stdin.fileno() , fcntl.F_GETFL, os.O_NONBLOCK)
    fcntl.fcntl(rval.stdin.fileno() , fcntl.F_SETFL, attrb & (~os.O_NONBLOCK))
    #fcntl.fcntl(rval.stdin.fileno() , fcntl.F_SETFL, os.O_NONBLOCK)
    return rval

class ProcessIO(object):
    def __init__(self, process):
        self.process = process
        #fcntl.fcntl(self.process.stdout.fileno() , fcntl.F_SETFL, os.O_NONBLOCK)

    def write(self, data):
        try:
            self.process.stdin.write(data)
        except:
            print 'except writing in ProcessIO'

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
            time.sleep(.8) # TODO - efficiency?

    def input_work_unit(self):
        if self.input is not None:
            in_buf = self.input.read(IN_BUF_SIZE)
        else:
            in_buf = '\x00' * IN_BUF_SIZE
        self.output.write(in_buf)

    def output_proc(self):
        """ free wheeling as long as there is output """
        while self.threads_should_run:
            self.listeners.acquire()
            while len(self.listeners):
                self.output_work_unit()
            self.listeners.release()

    def output_work_unit(self):
        try:
            packet = OggPacketReader(self.output)
        except:
            print 'error reading packet'
            import traceback
            traceback.print_exc()
            import sys
            sys.exit(1)
            return
        if packet.is_header():
            self.headers.append(packet)
        for listener in self.listeners:
            try:
                listener.write(packet.data)
            except:
                pass
                #print 'removing dead listener'
                #self.listeners.remove(listener)

    def add_listener(self, listener):
        print 'adding listener', listener
        for packet in self.headers:
            listener.write(packet.data)
        self.listeners.append(listener)

def main():
    r = RadioStation()

    decode_command = "/usr/bin/oggdec -Q -o - 2.ogg"

    rval = subprocess.Popen(decode_command, stdout=subprocess.PIPE, shell=True)

    attr = fcntl.fcntl(rval.stdout.fileno() , fcntl.F_GETFL)
    fcntl.fcntl(rval.stdout.fileno() , fcntl.F_SETFL, attr & (~os.O_NONBLOCK))

    #fcntl.fcntl(rval.stdout.fileno() , fcntl.F_SETFL, os.O_NONBLOCK)

    r.input = rval.stdout
    #r.input = open('2.raw', 'rb')

    listen_proc = subprocess.Popen("ogg123 --quiet -", stdin=subprocess.PIPE, shell=True)

    attr = fcntl.fcntl(listen_proc.stdin.fileno() , fcntl.F_GETFL)
    fcntl.fcntl(listen_proc.stdin.fileno() , fcntl.F_SETFL, attr & (~os.O_NONBLOCK))

    r.add_listener(listen_proc.stdin)
    time.sleep(400)


    #out = open('output.ogg', 'wb')
    #out2 = open('output2.ogg', 'wb')
    #r.add_listener(out)
    #time.sleep(6)
    #print 'adding out2'
    #r.add_listener(out2)
    #time.sleep(1)
    #r.stop_threads()
    #time.sleep(1)
    #out.close()
    #out2.close()


if __name__ == "__main__":
    main()
