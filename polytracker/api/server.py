"""Simple HTTP server for dashboard mode control."""

import asyncio
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from polytracker.api.mode_control import ModeController
from loguru import logger


class ModeControlHandler(BaseHTTPRequestHandler):
    """HTTP handler for mode control requests."""
    
    mode_controller = ModeController()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        
        if parsed.path == "/api/mode/info":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = self.mode_controller.get_info()
            self.wfile.write(json.dumps(data).encode())
        
        elif parsed.path == "/api/mode/current":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            mode = self.mode_controller.get_current_mode()
            self.wfile.write(json.dumps({"mode": mode}).encode())
        
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode())
        except:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return
        
        if parsed.path == "/api/mode/set":
            mode = data.get("mode")
            if not mode:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "mode required"}).encode())
                return
            
            result = self.mode_controller.set_mode(mode)
            
            self.send_response(200 if result.get("success") else 400)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        elif parsed.path == "/api/mode/set-confirmed":
            mode = data.get("mode")
            if not mode:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "mode required"}).encode())
                return
            
            result = self.mode_controller.set_mode_confirmed(mode)
            
            self.send_response(200 if result.get("success") else 400)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-type")
        self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


async def start_api_server(host: str = "127.0.0.1", port: int = 8000):
    """Start the API server.
    
    Args:
        host: Server host
        port: Server port
    """
    server = HTTPServer((host, port), ModeControlHandler)
    logger.info(f"📡 Mode control API server started on {host}:{port}")
    
    loop = asyncio.get_event_loop()
    
    def serve():
        server.handle_request()
        loop.call_soon(serve)
    
    loop.call_soon(serve)
    
    try:
        while True:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        server.server_close()
        logger.info("API server stopped")


if __name__ == "__main__":
    asyncio.run(start_api_server())
