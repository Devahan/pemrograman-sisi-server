from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/hello":
            data = {"message": "Hello from backend"}
            self.send_response(200)
        else:
            data = {"error": "Not found"}
            self.send_response(404)
            
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
        
server = HTTPServer(("localhost", 8000),Handler)
print("server running ini localhost://8000")
server.serve_forever()