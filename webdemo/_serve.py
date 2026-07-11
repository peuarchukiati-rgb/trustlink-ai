"""Minimal static server for the TrustLink console.

Serves this folder (webdemo/) with a correct UTF-8 charset. Run directly:
    python3 trustlink/webdemo/_serve.py
then open http://127.0.0.1:8099
"""
import functools
import http.server
import os
import socketserver

DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        if path.endswith(".html"):
            return "text/html; charset=utf-8"
        return super().guess_type(path)


if __name__ == "__main__":
    handler = functools.partial(Handler, directory=DIR)
    with socketserver.TCPServer(("127.0.0.1", 8099), handler) as httpd:
        print("TrustLink console on http://127.0.0.1:8099  (serving", DIR + ")")
        httpd.serve_forever()
