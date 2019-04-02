#!/usr/bin/python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from os import path
from requests import get
from re import sub
from socket import gethostname
from socketserver import ThreadingMixIn

PORT_NUMBER = 80
HEALTHY = True

env = Environment(
    loader=FileSystemLoader(path.dirname(path.realpath(__file__)) + '/templates'),
    autoescape=select_autoescape('html')
)


class request_handler(BaseHTTPRequestHandler):
    def get_zone(self):
        r = get('http://metadata.google.internal/'
                'computeMetadata/v1/instance/zone',
                headers={'Metadata-Flavor': 'Google'})
        if r.status_code == 200:
            return sub(r'.+zones/(.+)', r'\1', r.text)
        else:
            return ''

    def get_template(self):
        r = get('http://metadata.google.internal/'
                'computeMetadata/v1/instance/attributes/instance-template',
                headers={'Metadata-Flavor': 'Google'})
        if r.status_code == 200:
            return sub(r'.+instanceTemplates/(.+)', r'\1', r.text)
        else:
            return ''

    def do_GET(self):
        global HEALTHY

        if self.path == '/makeHealthy':
            HEALTHY = True
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()

        elif self.path == '/makeUnhealthy':
            HEALTHY = False
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()

        elif self.path == '/health':
            if not HEALTHY:
                self.send_response(500)
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
            html = env.get_template('health.jinja2').render(healthy=HEALTHY)
            self.wfile.write(html.encode('UTF-8'))

        else:
            HOSTNAME = gethostname()
            ZONE = self.get_zone()
            TEMPLATE = self.get_template()

            self.send_response(200 if HEALTHY else 500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = env.get_template('index.jinja2').render(hostname=HOSTNAME,
                                                           zone=ZONE,
                                                           template=TEMPLATE,
                                                           healthy=HEALTHY)
            self.wfile.write(html.encode('UTF-8'))


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


try:
    server = ThreadedHTTPServer(('', PORT_NUMBER), request_handler)
    print('Started httpserver on port %s' % PORT_NUMBER)
    server.serve_forever()

except KeyboardInterrupt:
    print('^C received, shutting down the web server')
    server.socket.close()
