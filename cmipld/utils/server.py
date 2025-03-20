import http.server
import socketserver
import ssl
import threading
import tempfile
import os
import subprocess


class LocalServer:
    def __init__(self, base_path, port=8000):
        self.base_path = base_path
        self.port = port
        self.certfile, self.keyfile = self.create_ssl_certificates()
        self.server = None
        self.thread = None

    def create_ssl_certificates(self):
        """Create self-signed SSL certificates and return the file paths."""
        # Create a temporary directory to store certificates
        # temp_dir = tempfile.mkdtemp()
        certfile = os.path.join(self.base_path, 'temp_cert.pem')
        keyfile = os.path.join(self.base_path, 'temp_key.pem')

        # Use OpenSSL to generate a self-signed certificate
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-keyout', keyfile,
            '-out', certfile, '-days', '365', '-nodes', '-subj', '/CN=localhost'
        ], check=True)

        print(f"Created SSL certificates in: {self.base_path}")
        return certfile, keyfile

    def start_server(self):
        """Start the HTTPS server without changing the working directory."""
        self.stop_server()  # Ensure any existing server is stopped

        # Define a custom handler that serves files from the specified base_path
        handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
            *args, directory=self.base_path, **kwargs
        )

        self.server = socketserver.TCPServer(("", self.port), handler)

        # # Wrap the server with SSL

        # Create an SSL context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
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
            print(f"Serving {self.base_path} at https://localhost:{self.port}")
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
            print("Server stopped.")
