import http.server
import socketserver
import ssl
import threading
# import tempfile
import os,re
import subprocess
from ..io import shell
from rich import print
from rich.console import Console
from rich.text import Text
from ...locations import mapping
from .monkeypatch_requests import RequestRedirector
console = Console()

from ..logging.unique import UniqueLogger
log = UniqueLogger()

# class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
#     def end_headers(self):
#         self.send_header('Access-Control-Allow-Origin', '*')
#         self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
#         self.send_header('Access-Control-Allow-Headers', '*')
#         super().end_headers()

#     def do_OPTIONS(self):
#         self.send_response(200, "ok")
#         self.end_headers()

class LocalServer:
    def __init__(self, base_path, port=None, debug = False):
        self.base_path = base_path
        self.port = port
        self.certfile, self.keyfile = self.create_ssl_certificates()
        self.server = None
        self.thread = None
        self.debug = debug
        self.requests = None
        self.prefix_map = None
        self.redirect_rules = None
        
        if not port:
            with socketserver.TCPServer(("", 0), http.server.SimpleHTTPRequestHandler) as temp_server:
                self.port = temp_server.server_address[1]
                log.debug(f"Using port: {self.port}")

    def create_ssl_certificates(self):
        """Create self-signed SSL certificates and return the file paths."""
        # Create a temporary directory to store certificates
        # temp_dir = tempfile.mkdtemp()
        certfile = os.path.join(self.base_path, 'temp_cert.pem')
        keyfile = os.path.join(self.base_path, 'temp_key.pem')

        # Use OpenSSL to generate a self-signed certificate
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-keyout', keyfile,
            '-out', certfile, '-days', '365', '-nodes', '-subj', '/CN=localhost', '-quiet'
        ], check=True)
        

        # print(f"Created SSL certificates in: {self.base_path}")
        log.debug(f"Created SSL certificates in:[bold #FF7900] {self.base_path} [/bold #FF7900]")
        
        return certfile, keyfile

    def start_server(self):
        """Start the HTTPS server without changing the working directory."""
        self.stop_server()  # Ensure any existing server is stopped

        if not self.debug:
            http.server.SimpleHTTPRequestHandler.log_message = lambda *args: None
        else:
            http.server.SimpleHTTPRequestHandler.log_message = lambda *args: log.debug(
                f"[bold #FF7900] {str(args)} [/bold #FF7900] "
            )


        # Call the request redirector to handle the reques
        if not self.prefix_map:
            self.prefix_map = mapping #from cmipld.mapping

        self.requests = RequestRedirector(
            prefix_map=self.prefix_map,
            redirect_rules=self.redirect_rules or {}
        )



        
        self.requests.test_redirect('https://wcrp-cmip.github.io/WCRP-universe/bob')

        # Define a custom handler that serves files from the specified base_path
        handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
            *args, directory=self.base_path, **kwargs
        )
        # handler = lambda *args, **kwargs: CORSRequestHandler(
        #     *args, directory=self.base_path, **kwargs
        # )
        
        
        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("", self.port), handler)

        # # Wrap the server with SSL

        # Create an SSL context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # print('ssh here ssl here sssl here')
        context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)

        # Wrap the server socket with SSL
        self.server.socket = context.wrap_socket(
            self.server.socket, server_side=True)

        # code below was depreciated in py3.12
        # self.server.socket = ssl.wrap_socket(
        #     self.server.socket,
        #     keyfile=self.keyfile,
        #     certfile=self.certfile,
        #     server_side=True
        # )

        def run_server():
            # print(f"Serving {self.base_path} at https://localhost:{self.port}")
            log.debug(f"[bold orange]Serving[/bold orange] [italic #FF7900]{self.base_path}[/italic #FF7900] at [bold magenta]https://localhost:{self.port}[/bold magenta]")
            self.server.serve_forever()

        # Start the server in a separate thread
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        return f"https://localhost:{self.port}"

    def stop_server(self):
        """Stop the HTTPS server if it's running."""
        if self.server:
            print("Shutting down the server...")
            self.server.shutdown()
            self.thread.join()
            self.server = None
            self.thread = None
            # print("Server stopped.")
            self.requests.restore_defaults()
            log.info("[bold yellow]Server stopped.[/bold yellow]")
            

    def test(self, **args):
        return self.requests.test_redirect(**args)
    