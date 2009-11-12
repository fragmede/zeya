# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Phil Sung, Samson Yeung, Romain Francoise
#
# This file is part of Zeya.
#
# Zeya is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Zeya is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Zeya. If not, see <http://www.gnu.org/licenses/>.

import fcntl
import os
import signal
import socket
import subprocess
import time

# For Python2.5 compatibility, we create an equivalent to
# subprocess.Popen.terminate (new in Python2.6) and patch it in.
try:
    subprocess.Popen.terminate
except AttributeError:
    def sub_popen_terminate(self):
        # This will only work on Unix-like systems, but it's better than
        # nothing.
        os.kill(self.pid, signal.SIGTERM)
    subprocess.Popen.terminate = sub_popen_terminate

import decoders

# Serve data to the client at a rate of no higher than RATE_MULTIPLIER * (the
# bitrate of the encoded data).
RATE_MULTIPLIER = 2.0

# Attempt to write STREAM_CHUNK_SIZE bytes up to (but possibly less than)
# STREAM_WRITE_FREQUENCY times per second. The maximum possible write rate with
# these parameters is 8192 bytes * 128 Hz = 1MB/sec.
STREAM_CHUNK_SIZE = 8192 #bytes
STREAM_WRITE_FREQUENCY = 128.0 #Hz

class StreamGenerationError(Exception):
    """
    Indicates an error generating a stream for the requested file.
    """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

def filename_to_stream(filename, out_stream, bitrate, buffered=False):
    print "Handling request for %s" % (filename,)
    try:
        decode_command = decoders.get_decoder(filename)
    except KeyError:
        raise StreamGenerationError(
            "Couldn't play specified format: %r" % (filename,))
    # Pipe the decode command into the encode command.
    return subprocess.Popen(decode_command, stdout=open('mux_input_fifo', 'w'))

# This interface is implemented by all library backends.

class LibraryBackend():
    """
    Object that controls access to a collection of music files.
    """
    def get_library_contents(self):
        """
        Return a list of the available files.

        The return value should be of the form

          [ {'key': ..., 'title': ..., 'artist': ..., 'album': ...},
            ... ]

        where each entry represents one file. The values coresponding to
        'title', 'artist', and 'album' are strings or unicode strings giving
        the song attributes. The value corresponding to 'key' may be passed to
        self.write_content in order to obtain the data for a particular file.

        The items will be displayed to the user in the order that they appear
        here.
        """
        raise NotImplementedError()

    def get_content(self, key, out_stream, bitrate, buffered=False):
        """
        Retrieve the file data associated with the specified key and write an
        audio/ogg encoded version to out_stream.
        """
        # This is a convenience implementation of this method.
        try:
            filename = self.get_filename_from_key(key)
        except KeyError:
            print "Received invalid request for key %r" % (key,)
        try:
            return filename_to_stream(filename, out_stream, bitrate, buffered)
        except StreamGenerationError, e:
            print "ERROR. %s" % (e,)

    def get_filename_from_key(self, key):
        # Retrieve the filename that 'key' is backed by. This is not part of
        # the public API, but is used in the default implementation of
        # get_content.
        #
        # Raise KeyError if the key is not valid.
        raise NotImplementedError()
