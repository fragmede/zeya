#

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

HEADER_LEN = 1
OGG_MAGIC = 'OggS\x00'
GRANULE_POS_LEN = 8
SERIAL_NUM_LEN = 4
PAGE_SEQ_LEN = 4
CHECKSUM_LEN = 4
PAGE_SEGMENTS_LEN = 1

#packet_header_map = [   ( 'header_type', HEADER_LEN),
#                        ( 'granule_pos', GRANULE_POS_LEN),

class OggPacketReader(object):
    def __init__(self, input_stream):
        self.data = ''
        self.read_ogg_packet(input_stream)

    def is_header(self):
        return all([x == '\x00' for x in self.granule_pos])

    def read_ogg_packet(self, data):
        magic = data.read(len(OGG_MAGIC))
        if len(magic) == 0:
            raise EOFError
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

        #print 'header_type  ',  repr(self.header_type)
        #print 'granule_pos  ',  repr(self.granule_pos)
        #print 'serial_num   ',  repr(self.serial_num)
        #print 'page_seq_num ',  repr(self.page_seq_num)
        #print 'checksum     ',  repr(self.checksum)
        #print 'page_segments',  repr(self.page_segments)

        #print '  page_segs', self.page_segments

        segment_table = data.read(ord(self.page_segments))
        self.data += segment_table
        segments = []
        for segment in segment_table:
            #print 'segment n', hex(ord(segment))
            segments.append(data.read(ord(segment)))
            self.data += segments[-1]

    def write_page(self, output):
        output.write(self.serial_num)

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

    def file_in_paths(name, paths):
        for path in search_paths:
            if os.path.exists(os.path.join(path, 'oggdec')):
                return True
        return False

#
    import os
    MY_PATH = os.getenv('PATH', 'Error')
    search_paths = [x for x in MY_PATH.split(':') if x]
    print file_in_paths('oggdec', search_paths)




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
    import sys
    sys.exit()
    f = open('test.ogg', 'r')
    out = open('2.ogg', 'wb')
    #for i in range(8):
    i = 1
    while True:
        p = OggPacketReader(f)
        print 'packet', i, 'at', hex(f.tell()), p.is_header()
        i += 1
        #p.write_page(out)
        out.write(p.data)

    #thread.start_new_thread(reader, ())
    #thread.start_new_thread(server, (0,))
    #thread.start_new_thread(server, (1,))

    #reader()
    #while True:
    #    time.sleep(.2)
