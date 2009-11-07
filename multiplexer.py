import fcntl
import os
import signal
import socket
import StringIO
import subprocess
import thread
import time

try:
    subprocess.Popen.terminate
except AttributeError:
    def sub_popen_terminate(self):
        # This will only work on Unix-like systems, but it's better than
        # nothing.
        os.kill(self.pid, signal.SIGTERM)
    subprocess.Popen.terminate = sub_popen_terminate


output_list = []
bitrate = 64

class SockAdaptor(object):
    def __init__(self, sock):
        self.sock = sock

    def write(self, data):
        return self.sock.send(data)

    def read(self, data_len):
        return self.sock.recv(data_len)

class Encoder(object):
    def __init__(self, output):
        #encode_command = ["/usr/bin/oggenc", "-r", "-b", str(bitrate), "-"]
        encode_command = "/usr/bin/oggenc -r -Q -b 64 -"
        self.p2 = p2 = subprocess.Popen(encode_command,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        shell=True)
        #self.write = p2.stdin.write
        self.output_sock = output
        #p2.stdout.setblocking(0)
        fcntl.fcntl(p2.stdout.fileno() , fcntl.F_SETFL, os.O_NONBLOCK)

    def write(self, data):
        self.p2.stdin.write(data)
        return
        comms = self.p2.communicate(data)
        print 'comm', len(comms[0])
        self.output_sock.send(comms[0])

    def output(self):
        #data = self.p2.communicate()[0]
        try:
            data = self.p2.stdout.read(4096)
        except IOError:
            return
        self.output_sock.send(data)
        #self.p2.poll()

def reader():
    global output_list
    print 'reader thread started'
    input_name = 'ogg_fifo'
    f = open(input_name, 'r')
    while True:
        time.sleep(.2)
        while len(output_list) == 0:
            time.sleep(.2)
        buff = f.read(81920)
        for output in output_list:
            output.write(buff)
            output.output()

def server(num):
    global output_list
    print 'server thread', num, 'started'

    pipename = 'output%s' % (num, )
    try:
        os.remove(pipename)
    except:
        pass

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.setblocking(1)
    s.bind(pipename)
    s.listen(1)

    conn, addr = s.accept()
    print 'client connected', conn, addr
    #output_list.append(Encoder(SockAdaptor(conn)))
    output_list.append(Encoder(conn))
    #while True:
    #    time.sleep(.2)

if __name__ == "__main__":
    #thread.start_new_thread(reader, ())
    thread.start_new_thread(server, (0,))
    thread.start_new_thread(server, (1,))

    reader()
    while True:
        time.sleep(.2)
