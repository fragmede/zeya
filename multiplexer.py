import fcntl
import os
import signal
import socket
import StringIO
import struct
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
header_packets = []

bitrate = 64

HEADER_LEN = 1
OGG_MAGIC = 'OggS\x00'
#GRANULE_POS_OFFSET = 6
GRANULE_POS_LEN = 8
SERIAL_NUM_LEN = 4
PAGE_SEQ_LEN = 4
CHECKSUM_LEN = 4
PAGE_SEGMENTS_LEN = 1

class OggPacketizer(object):
    def __init__(self, input_stream):
        self.header = ''
        self.read_ogg_packet(input_stream)

    def is_header(self):
        return all([x == '\x00' for x in self.granule_pos])

    def read_ogg_packet(self, data):
        magic = data.read(len(OGG_MAGIC))
        assert(magic == OGG_MAGIC)

        # TODO - make map creating locals
        self.header_type = data.read(HEADER_LEN)
        self.granule_pos = data.read(GRANULE_POS_LEN)
        self.serial_num = data.read(SERIAL_NUM_LEN)
        self.page_seq_num = data.read(PAGE_SEQ_LEN)
        self.checksum = data.read(CHECKSUM_LEN)
        self.page_segments = ord(data.read(PAGE_SEGMENTS_LEN))

        #print 'header_type  ',  repr(self.header_type)
        #print 'granule_pos  ',  repr(self.granule_pos)
        #print 'serial_num   ',  repr(self.serial_num)
        #print 'page_seq_num ',  repr(self.page_seq_num)
        #print 'checksum     ',  repr(self.checksum)
        #print 'page_segments',  repr(self.page_segments)

        #print '  page_segs', self.page_segments

        #if self.page_segments == 0:
        #    foo = data.read(1)
        #    #print 's', ord(foo)
        #    data.read(ord(foo)+16)
        #    #print 'endp', hex(f.tell())
        #    return

        segment_table = data.read(self.page_segments)
        #segment_table = data.read(0)
        segments = []
        #print 'st', segment_table
        for segment in segment_table:
            #print 'segment n', hex(ord(segment))
            segments.append(data.read(ord(segment)))

        #data.read(1)

class OggPageSync(object):
    def __init__(self, output):
        self.output_sock = output
        self.syncd = False

    def write(self, data):
        if self.syncd:
            self.output_sock.send(data)
            return
        page_start = data.find(OGG_MAGIC)
        if page_start == -1:
            return
        self.output_sock.send(data[page_start:])
        self.syncd = True

def reader():
    global output_list
    print 'reader thread started'
    input_fifo = 'ogg_fifo'
    global header_packets
    f = open(input_fifo, 'r')
    while True:
        time.sleep(.2)
        while len(output_list) == 0:
            time.sleep(.2)
        packet = ogg_packet(f)
        if packet.is_header():
            header_packets.append(packet)
        #buff = f.read(4096)
        for output in output_list:
            output.write(buff)

def server(num):
    global output_list
    global header_packets
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
    for packet in header_packets:
        conn.send(packet)

    output_list.append(OggPageSync(conn))

if __name__ == "__main__":
    #test ogg packets at:
    #  0x0
    #  0x3a
    #  0xf8b
    #  0x1fc9
    #  0x30d1
    #  0x4111

#    f = open('test.ogg', 'r')
#    d = f.read(0x5000)
#    offset = -1
#    pack_begins = []
#    while True:
#        idx = d.find('OggS')
#        if idx == -1:
#            break
#        d = d[idx+1:]
#        offset += idx + 1
#        print hex(offset)
#        pack_begins.append(offset)
#
#    print 'packs'
#    for offset in pack_begins:
#        f.seek(offset, 0)
#        print hex(offset), f.read(6).find('O')
        #print offset, repr(f.read(6))
    #import sys
    #sys.exit()
    f = open('test.ogg', 'r')
    for i in range(8):
        p = OggPacketizer(f)
        print 'packet', i, 'at', hex(f.tell()), p.is_header()

    #thread.start_new_thread(reader, ())
    #thread.start_new_thread(server, (0,))
    #thread.start_new_thread(server, (1,))

    #reader()
    #while True:
    #    time.sleep(.2)
