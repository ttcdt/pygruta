#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   HTTP server

import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import time
import re
import hashlib, base64

import pygruta
import pygruta.activitypub as activitypub
import pygruta.webmention as webmention
import pygruta.calendar as calendar
import pygruta.xml as xml
import pygruta.html as html
import pygruta.text as text

class httpd_handler(BaseHTTPRequestHandler):

    def _finish(self, status=200, etag=None, ctype=None, body=None):
        if ctype is None:
            ctype = "text/html; charset=utf-8"

        self.send_response(status)

        self.send_header("Content-type", ctype)
        self.send_header("X-pygruta",    pygruta.__version__)
        self.send_header("X-Secret",     "-.-- --- ..- .-.. --- --- -.- -... --- .-. . -..")

        if etag:
            self.send_header("ETag", etag)

        if status == 303:
            # redirection
            self.send_header("Location", body)

        self.end_headers()

        if body is not None:
            if isinstance(body, str):
                body = body.encode("utf-8")

            self.wfile.write(body)


    def _init(self):
        # parse query string and vars
        qs = self.path.split('?')
        q_path = qs[0]

        # convert %XX to char
        q_path = urllib.parse.unquote(q_path)

        if len(qs) == 2:
            q_vars = urllib.parse.parse_qs(qs[1])
        else:
            q_vars = {}

        # basic authorization?
        auth = self.headers.get("Authorization")

        if auth is not None and auth[0:6] == "Basic ":
            # strip type
            auth = auth.replace("Basic ", "")

            # convert from base64 to string
            auth = base64.b64decode(auth).decode()

            auth = auth.split(":")

            # stored user name
            self.gruta.logged_user = auth[0]

        return self.gruta, q_path, q_vars


    def _invalid_token(self, gruta):
        ret = False

        # does this connection require a token?
        token = gruta.template("cfg_token")

        if token != "" and token != self.headers.get("X-Gruta-Token"):
            ret = True

        return ret


    def do_HEAD(self):
        gruta, q_path, q_vars = self._init()

        self._finish()

        gruta.clear_caches()


    def do_GET(self):
        gruta, q_path, q_vars = self._init()

        # get time and new and old tags
        time_n = time.time()
        etag_n = None
        etag_o = self.headers.get("If-None-Match") or ""

        # try the cache
        body, state, ctype = gruta.page_cache.get(q_path, etag_o)

        # not yet? build it
        if body is None:
            # HTTP status of 0 means 'didn't handled it'

            if self._invalid_token(gruta):
                status, body, ctype = 401, "<h1>401 Auth Required</h1>", "text/html"
            else:
                status, body, ctype = gruta.get_handler(q_path, q_vars)

            # if successful, put into cache and create new etag
            if status == 200:
                etag_n = "W/\"g-%x\"" % int(time_n)

                gruta.page_cache.put(q_path, body, tag=etag_n, context=ctype)

            # nobody handled this? notify error
            if status == 0:
                status = 404

            # if 404, force body and content/type
            if status == 404:
                status, body, ctype = 404, "<h1>404 Not Found</h1>", "text/html"

        else:
            if state == 1:
                # client already has it
                status, body = 304, None
            else:
                # serve client the cached state
                status = 200

        self._finish(status, etag_n, ctype, body)


    def do_POST(self):
        gruta, q_path, q_vars = self._init()

        gruta.log("DEBUG", "httpd: POST headers '%s'" % self.headers)

        content_length = int(self.headers['Content-Length'])
        p_data = self.rfile.read(content_length).decode('utf-8')

        status, body, ctype = 0, None, None

        if self._invalid_token(gruta):
            status, body, ctype = 401, "<h1>401 Auth Required</h1>", "text/html"

        elif re.search("^/activitypub/inbox/.+", q_path):
            status, body, ctype = activitypub.inbox_post_handler(gruta, q_path,
                q_vars, p_data)

        elif q_path == "/webmention/" or q_path == "/post_webmention/":
            status, body, ctype = webmention.post_handler(
                                    gruta, urllib.parse.parse_qs(p_data))

        else:
            status, body, ctype = html.post_handler(gruta, q_path, q_vars,
                urllib.parse.parse_qs(p_data))

        # nobody handled this? notify error
        if status == 0:
            status, body, ctype = 404, "<h1>404 Not Found</h1>", "text/html"

        self._finish(status, None, ctype, body)


    def log_message(self, format, *args):
        gruta, q_path, q_vars = self._init()
        gruta.log("INFO", "httpd: CONN %s %s" % (args[1], args[0]))



def httpd(gruta, address="localhost", port=8000):
    """ starts the httpd server """

    import signal, sys

    def sigterm_handler(sig, frame):
        gruta.log("INFO", "httpd: sigterm")
        # simulate Ctrl-C
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, sigterm_handler)

    server = HTTPServer((address, port), httpd_handler)
    gruta.log("INFO",
        "httpd: START %s:%s [pygruta %s]" % (address, port, pygruta.__version__))

    # copy the gruta object into the handler
    server.RequestHandlerClass.gruta = gruta

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.server_close()
    gruta.log("INFO", "httpd: STOP %s:%s" % (address, port))
