HEADER_LEN = 1
OGG_MAGIC = 'OggS\x00'
GRANULE_POS_LEN = 8
SERIAL_NUM_LEN = 4
PAGE_SEQ_LEN = 4
CHECKSUM_LEN = 4
PAGE_SEGMENTS_LEN = 1

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
