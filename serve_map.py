# serve_map.py
import http.server
import socketserver
import sys
import os

PORT = int(sys.argv[1])
HTML_FILE = sys.argv[2]

# Serve the directory containing the HTML file
directory = os.path.dirname(os.path.abspath(HTML_FILE))
filename = os.path.basename(HTML_FILE)

os.chdir(directory)

class Handler(http.server.SimpleHTTPRequestHandler):
    pass

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}/{filename}")
    httpd.serve_forever()
