#


#arch:
#   fifo with raw bytes -> here
#   here -> oggenc -> stream out

# see also:
#    http://www.xiph.org/vorbis/doc/oggstream.html
#    http://www.xiph.org/vorbis/doc/framing.html


import fcntl
import os
import signal
import socket
import StringIO
import struct
import subprocess
import thread
import time

output_list = []
header_packets = []

bitrate = 64

#packet_header_map = [   ( 'header_type', HEADER_LEN),
#                        ( 'granule_pos', GRANULE_POS_LEN),

class OggPacketReader(object):
    def __init__(self, input_stream):
        self.data = ''
        self.read_ogg_packet(input_stream)

    def is_header(self):
        return all([x == '\x00' for x in self.granule_pos])

    def read_ogg_packet(self, data):
        # wrap this behavior elsewhere
        # so OggPacketReader has no concept
        magic = data.read(len(OGG_MAGIC))
        #while True:
        #    magic = data.read(len(OGG_MAGIC))
        #    if len(magic) == len(OGG_MAGIC):
        #        break
        #    elif len(magic) != 0:
        #        raise Exception('partial read')
                #print 'partial read! ', len(magic)

        assert(magic == OGG_MAGIC)
        self.data += magic

        # TODO - make map creating locals
        self.header_type = data.read(HEADER_LEN)
        self.granule_pos = data.read(GRANULE_POS_LEN)
        self.serial_num = data.read(SERIAL_NUM_LEN)
        self.page_seq_num = data.read(PAGE_SEQ_LEN)
        self.checksum = data.read(CHECKSUM_LEN)
        self.page_segments = data.read(PAGE_SEGMENTS_LEN)

        self.data += self.header_type
        self.data += self.granule_pos
        self.data += self.serial_num
        self.data += self.page_seq_num
        self.data += self.checksum
        self.data += self.page_segments

        segment_table = data.read(ord(self.page_segments))
        self.data += segment_table
        segments = []
        for segment in segment_table:
            #print 'segment n', hex(ord(segment))
            segments.append(data.read(ord(segment)))
            self.data += segments[-1]

    def write_page(self, output):
        output.write(self.serial_num)

def oggenc():
    print 'oggenc thread started'
    #encode_command = ["/usr/bin/oggenc", "-r", "-b", str(bitrate), "-"]
    input = open('mux_input_fifo', 'rb')
    output = open('mux_output_fifo', 'wb')
    encode_command = "/usr/bin/oggenc -r -Q -b 64 - -M 70"
    p1 = subprocess.Popen(encode_command.split(),
                          stdin=input,
                          #stdout=subprocess.PIPE,
                          stdout=output,
                          #shell=True,
                         )
    #p2 = subprocess.Popen("cstream -t 80k", stdin=p1.stdout,
    #                      stdout=output, shell=True)

    p1.wait()
    print 'doom!, oggenc thread ended'

class SockObjRedir:
    def __init__(self, conn):
        self.conn = conn

    def write(self, data):
        self.conn.send(data)

    def read(self, data_len=0):
        return self.conn.recv(data_len)

def err_catch(input):
    try:
        return True, OggPacketReader(input)
    finally:
        return False, None

def reader():
    global output_list
    print 'reader thread started'
    input_fifo = 'mux_output_fifo'
    global header_packets
    f = open(input_fifo, 'r')
    while True:
        while len(output_list) == 0:
            time.sleep(.2)
        #while True:
        #    cont, packet = err_catch(f)
        #    if cont:
        #        break
        try:
            packet = OggPacketReader(f)
        except:
            continue
        if packet.is_header():
            header_packets.append(packet)
        #buff = f.read(4096)
        for output in output_list:
            try:
                output.write(packet.data)
            except:
                output_list.remove(output)

def server(num):
    global output_list
    global header_packets
    print 'server thread', num, 'started'

    pipename = 'mux_output'
    try:
        os.remove(pipename)
    except:
        pass

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.setblocking(1)
    s.bind(pipename)
    s.listen(1)

    while True:
        conn, addr = s.accept()
        connIO = SockObjRedir(conn)
        print 'client connected', addr
        for packet in header_packets:
            connIO.write(packet.data)

        output_list.append(connIO)

if __name__ == "__main__":
    #thread.start_new_thread(reader, ())
    def loop(call):
        while True:
            call()
    thread.start_new_thread(lambda :loop(lambda :server(0)), ())
    thread.start_new_thread(lambda :loop(oggenc), ())

    reader()
    #while True:
    #    time.sleep(.2)
