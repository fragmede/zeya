#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Phil Sung, Samson Yeung
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


# Zeya - a web music server.

# Work with python2.5
from __future__ import with_statement

import BaseHTTPServer

import getopt
import urllib
import os
import sys
import tempfile
import traceback
try:
    from urlparse import parse_qs
except: # (ImportError, AttributeError):
    from cgi import parse_qs

try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json

DEFAULT_PORT = 8080
DEFAULT_BACKEND = "rhythmbox"

# Store the state of the library.
library_contents = []
library_repr = ""

valid_backends = ['rhythmbox', 'dir']

class BadArgsError(Exception):
    """
    Error due to incorrect command-line invocation of this program.
    """
    def __init__(self, message):
        self.error_message = message
    def __str__(self):
        return "Error: %s" % (self.error_message,)

# TODO: support a multithreaded server.

def ZeyaHandler(resource_basedir):
    """
    Wrapper around the actual HTTP request handler implementation class. We
    need to create a closure so that the inner class can remember the base
    directory for resources.
    """

    class ZeyaHandlerImpl(BaseHTTPServer.BaseHTTPRequestHandler):
        """
        Web server request handler.
        """
        def do_GET(self):
            """
            Handle a GET request.
            """
            # http://host/ yields the library main page.
            if self.path == '/':
                self.serve_static_content('/library.html')
            # http://host/getlibrary returns a representation of the music
            # collection.
            elif self.path == '/getlibrary':
                self.serve_library()
            # http://host/getcontent?key=N yields an Ogg stream of the file
            # associated with the specified key.
            elif self.path.startswith('/getcontent?'):
                self.serve_content(urllib.unquote(self.path[12:]))
            # All other paths are assumed to be static content.
            # http://host/foo is mapped to resources/foo.
            else:
                self.serve_static_content(self.path)
        def get_content_type(self, path):
            """
            Return the MIME type associated with the given path.
            """
            path = path.lower()
            if path.endswith('.html'):
                return 'text/html'
            elif path.endswith('.png'):
                return 'image/png'
            elif path.endswith('.css'):
                return 'text/css'
            elif path.endswith('.ogg'):
                return 'audio/ogg'
            else:
                return 'application/octet-stream'
        def serve_content(self, query):
            """
            Serve an audio stream (audio/ogg).
            """
            # The query is of the form key=N or key=N&buffered=true.
            args = parse_qs(query)
            key = args['key'][0] if args.has_key('key') else ''
            # If buffering is activated, encode the entire file and serve the
            # Content-Length header. This increases song load latency because
            # we can't serve any of the file until we've finished encoding the
            # whole thing. However, Chrome needs the Content-Length header to
            # accompany audio data.
            buffered = args['buffered'][0] if args.has_key('buffered') else ''

            self.send_response(200)
            self.send_header('Content-type', 'audio/ogg')
            if buffered:
                # Complete the transcode and write to a temporary file.
                # Determine its length and serve the Content-Length header.
                output_file = tempfile.TemporaryFile()
                backend.get_content(key, output_file, buffered=True)
                output_file.seek(0)
                data = output_file.read()
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                # Don't determine the Content-Length. Just stream to the client
                # on the fly.
                self.end_headers()
                backend.get_content(key, self.wfile)
            self.wfile.close()
        def serve_library(self):
            """
            Serve a representation of the library.

            We take the output of backend.get_library_contents(), dump it as JSON,
            and give that to the client.
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(library_repr.encode('utf-8'))
            self.wfile.close()
        def serve_static_content(self, path):
            """
            Serve static content from the resources/ directory.
            """
            try:
                # path already has a leading '/' in front of it. Strip it.
                full_path = os.path.join(resource_basedir, path[1:])
                # Ensure that the basedir we use for security checks ends in '/'.
                effective_basedir = os.path.join(resource_basedir, '')
                # Prevent directory traversal attacks. Canonicalize the
                # filename we're going to open and verify that it's inside the
                # resource directory.
                if not os.path.abspath(full_path).startswith(effective_basedir):
                    self.send_error(404, 'File not found: %s' % (path,))
                    return
                with open(full_path) as f:
                    self.send_response(200)
                    self.send_header('Content-type', self.get_content_type(path))
                    data = f.read()
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
            except IOError:
                traceback.print_exc()
                self.send_error(404, 'File not found: %s' % (path,))

    return ZeyaHandlerImpl

def getOptions():
    """
    Parse the arguments and return a tuple (show_help, backend, port), or raise
    BadArgsError if the invocation was not valid.

    show_help: whether user requested help information
    backend: string containing backend to use (only supported value right now
             is "rhythmbox")
    port: port number to listen on
    """
    help_msg = False
    port = DEFAULT_PORT
    backend_type = DEFAULT_BACKEND
    path = None
    try:
        opts, file_list = getopt.getopt(sys.argv[1:], "hp:",
                                        ["help", "backend=", "port=", "path="])
    except getopt.GetoptError:
        raise BadArgsError("Unsupported options")
    for flag, value in opts:
        if flag in ("-h", "--help"):
            help_msg = True
        if flag in ("--backend",):
            backend_type = value
            if backend_type not in valid_backends:
                raise BadArgsError("Unsupported backend type")
        if flag in ("--path",):
            path = value
        if flag in ("-p", "--port"):
            try:
                port = int(value)
            except ValueError:
                raise BadArgsError("Invalid port setting %r" % (value,))
    if backend_type == 'dir' and path is None:
        raise BadArgsError("Directory (dir) backend needs a path (--path)")
    return (help_msg, backend_type, port, path)

def usage():
    print "Usage: zeya.py [-h|--help] [--backend=[rhythmbox|dir]] [--port] [--path=PATH]"

def main(port):
    global library_contents, library_repr
    # Read the library.
    print "Loading library..."
    library_contents = backend.get_library_contents()
    library_repr = json.dumps(library_contents, ensure_ascii=False)
    basedir = os.path.abspath(os.path.realdir(os.path.dirname(sys.argv[0])))
    server = BaseHTTPServer.HTTPServer(
        ('', port),
        ZeyaHandler(os.path.join(basedir, 'resources')))
    print "Listening on port %d" % (port,)
    # Start up a web server.
    print "Ready to serve!"
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    try:
        (show_help, backend_type, port, path) = getOptions()
    except BadArgsError, e:
        print e
        usage()
        sys.exit(1)
    if show_help:
        usage()
        sys.exit(0)
    print "Using %r backend" % (backend_type,)
    if backend_type == "rhythmbox":
        # Import the backend modules conditionally, so users don't have to
        # install dependencies unless they are actually used.
        from rhythmbox import RhythmboxBackend
        backend = RhythmboxBackend()
    elif backend_type == 'dir':
        from directory import DirectoryBackend
        backend = DirectoryBackend(path)
    main(port)
