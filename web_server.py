# -*- coding: utf-8 -*-
"""
Web Server for RCSIM Deployment Tool.
Uruchamia interfejs webowy i udostępnia API dla logiki wdrożeniowej (bez zależności od wątków Tkintera).
"""

import os
import sys
import time
import json
import queue
import socket
import gettext
import threading
import subprocess
import webbrowser
from typing import Any, Dict
from flask import Flask, render_template, jsonify, request, Response

# Add core path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import deployment_logic

APP_NAME = "RCSIMDeploymentTool"
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "deployment_settings.json")
LOCALE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "locales"))
SUPPORTED_LANGUAGES = {"English": "en", "Polski": "pl"}

# Default settings
DEFAULT_SETTINGS = {
    "rpi_host": "",
    "rpi_user": "",
    "rpi_pass": "",
    "project_source": "",
    "pc_tailscale_ip": "",
    "use_rtk": True,
    "ntrip_user": "",
    "ntrip_pass": "",
    "ntrip_host": "",
    "ntrip_port": "",
    "ntrip_mount": "",
    "imu_driver": "native_mpu9250",
    "gps_enabled": True,
    "gps_port": "/dev/ttyAMA0",
    "gps_baudrate": "115200",
    "camera_port": "cam0",
    "camera_resolution": "1920x1080",
    "camera_fps": "30",
    "camera_bitrate": "5 Mbps",
    "camera_type": "AUTO",
    "lidar_enabled": False,
    "lidar_port": "/dev/ttyUSB0",
    "elrs_enabled": True,
    "elrs_port": "/dev/ttyAMA3",
    "language": "English",
    "rpi_use_key": False,
    "rpi_key_path": "",
    "rpi_key_passphrase": "",
    "pc_udp_port": "12347",
    "rpi_udp_port": "12346",
    "comm_mode": "AUTO",
    "comm_protocol": "NATIVE",
    "lidar_baudrate": "115200",
    "elrs_baudrate": "57600",
    "mavlink_system_id": "1",
    "mavlink_throttle_hz": "5",
    "fast_mode": True,
    "app_type": "RCSIM_DOCKER"
}

class WebConfigManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.settings = DEFAULT_SETTINGS.copy()
        self._translate = gettext.gettext
        self.load_settings()

    def translate(self, text: str) -> str:
        return self._translate(text)

    def switch_language(self, lang_code: str) -> None:
        try:
            lang = gettext.translation(
                APP_NAME,
                localedir=LOCALE_DIR,
                languages=[lang_code],
                fallback=True,
            )
            self._translate = lang.gettext
        except Exception:
            self._translate = gettext.gettext

    def load_settings(self) -> None:
        with self.lock:
            if os.path.exists(SETTINGS_FILE):
                try:
                    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        self.settings.update(loaded)
                except Exception as e:
                    print(f"Failed to load settings: {e}")
            
            # Apply loaded language
            lang_name = self.settings.get("language", "English")
            lang_code = SUPPORTED_LANGUAGES.get(lang_name, "en")
            self.switch_language(lang_code)

    def save_settings(self) -> None:
        with self.lock:
            try:
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.settings, f, indent=4)
            except Exception as e:
                print(f"Failed to save settings: {e}")

    def get_full_config_payload(self) -> Dict[str, Any]:
        gps_baud = 115200
        try:
            gps_baud = int(self.settings.get("gps_baudrate", "115200"))
        except Exception:
            pass

        camera_res = [1920, 1080]
        try:
            res_str = self.settings.get("camera_resolution", "1920x1080")
            if "x" in res_str:
                w, h = res_str.split("x")
                camera_res = [int(w), int(h)]
        except Exception:
            pass

        camera_fps = 30
        try:
            camera_fps = int(self.settings.get("camera_fps", "30"))
        except Exception:
            pass

        camera_bitrate_bps = 5_000_000
        try:
            bitrate_str = self.settings.get("camera_bitrate", "5 Mbps")
            camera_bitrate_bps = int(bitrate_str.split()[0]) * 1_000_000
        except Exception:
            pass

        return {
            "hardware": {
                "imu": {"driver": str(self.settings.get("imu_driver", "native_mpu9250")).strip()},
                "gps": {
                    "enabled": bool(self.settings.get("gps_enabled", True)),
                    "port": str(self.settings.get("gps_port", "/dev/ttyAMA0")).strip(),
                    "baudrate": gps_baud,
                },
                "lidar": {
                    "enabled": bool(self.settings.get("lidar_enabled", False)),
                    "port": str(self.settings.get("lidar_port", "/dev/ttyUSB0")).strip(),
                    "baudrate": int(self.settings.get("lidar_baudrate", "115200")),
                },
                "elrs": {
                    "enabled": bool(self.settings.get("elrs_enabled", True)),
                    "port": str(self.settings.get("elrs_port", "/dev/ttyAMA3")).strip(),
                    "baudrate": int(self.settings.get("elrs_baudrate", "57600")),
                },
            },
            "camera": {
                "resolution": camera_res,
                "fps": camera_fps,
                "port": str(self.settings.get("camera_port", "cam0")).strip(),
                "bitrate": camera_bitrate_bps,
                "type": self.settings.get("camera_type", "AUTO"),
                "dynamic_bitrate": True,
                "dynamic_resolution": True,
            },
            "video": {
                "resolution": camera_res,
                "fps": camera_fps,
                "dynamic_bitrate": True,
                "dynamic_resolution": True,
            },
            "network": {
                "pc_udp_port": int(self.settings.get("pc_udp_port", "12347")),
                "rpi_udp_port": int(self.settings.get("rpi_udp_port", "12346")),
                "adaptive_bitrate_enabled": True,
            },
            "comm_mode": self.settings.get("comm_mode", "AUTO"),
            "comm_protocol": self.settings.get("comm_protocol", "NATIVE"),
            "system_id": int(self.settings.get("mavlink_system_id", "1")),
            "mavlink_throttle_hz": int(self.settings.get("mavlink_throttle_hz", "5")),
            "mavlink_connection": f"{str(self.settings.get('elrs_port', '/dev/ttyAMA3')).strip()}:{self.settings.get('elrs_baudrate', '57600')}",
        }

    def get_deployment_config(self) -> Dict[str, Any]:
        key_p = self.settings.get("rpi_key_path", "")
        return {
            "rpi_host": self.settings.get("rpi_host", ""),
            "rpi_user": self.settings.get("rpi_user", ""),
            "rpi_pass": self.settings.get("rpi_pass", ""),
            "new_ssh_pass": self.settings.get("new_ssh_pass", ""),
            "project_source_dir": self.settings.get("project_source", ""),
            "pc_tailscale_ip": self.settings.get("pc_tailscale_ip", ""),
            "use_rtk": bool(self.settings.get("use_rtk", True)),
            "ntrip_user": self.settings.get("ntrip_user", ""),
            "ntrip_pass": self.settings.get("ntrip_pass", ""),
            "ntrip_host": self.settings.get("ntrip_host", ""),
            "ntrip_port": self.settings.get("ntrip_port", ""),
            "ntrip_mount": self.settings.get("ntrip_mount", ""),
            "rpi_key_path": key_p if self.settings.get("rpi_use_key", False) else None,
            "rpi_key_passphrase": (
                self.settings.get("rpi_key_passphrase", "")
                if self.settings.get("rpi_use_key", False)
                else None
            ),
            "app_type": self.settings.get("app_type", "RCSIM_DOCKER"),
            "full_config_payload": self.get_full_config_payload(),
        }

# Instantiate thread-safe manager
web_config = WebConfigManager()

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

# Log Queue for SSE stream
log_queue = queue.Queue()
progress_value = 0
active_action_thread = None
is_ui_locked = False

def push_log(message: str, level: str = "info"):
    """Dodaje log do kolejki wysyłanej do przeglądarki."""
    log_queue.put({
        "time": time.strftime("%H:%M:%S"),
        "message": message,
        "level": level
    })

def update_progress(val: int):
    global progress_value
    progress_value = val

def run_in_background(target, *args, **kwargs):
    """Pomocnik do uruchamiania akcji w osobnym wątku."""
    global active_action_thread, is_ui_locked
    if is_ui_locked:
        push_log("Another action is already running!", "error")
        return False
        
    is_ui_locked = True
    progress_value = 0
    
    def wrapped_target():
        global is_ui_locked
        try:
            target(*args, **kwargs)
        except Exception as e:
            push_log(f"Execution failed: {str(e)}", "error")
        finally:
            is_ui_locked = False
            progress_value = 100
            
    active_action_thread = threading.Thread(target=wrapped_target, daemon=True)
    active_action_thread.start()
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/languages', methods=['GET'])
def get_languages():
    return jsonify({
        "languages": list(SUPPORTED_LANGUAGES.keys()),
        "current": web_config.settings.get("language", "English")
    })

@app.route('/api/change_language', methods=['POST'])
def change_language():
    data = request.json or {}
    lang_name = data.get("language")
    if lang_name in SUPPORTED_LANGUAGES:
        web_config.settings["language"] = lang_name
        lang_code = SUPPORTED_LANGUAGES[lang_name]
        web_config.switch_language(lang_code)
        web_config.save_settings()
        push_log(f"Language changed to {lang_name}.", "verbose")
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Unsupported language"})

@app.route('/api/config', methods=['GET', 'POST'])
def get_set_config():
    if request.method == 'GET':
        web_config.load_settings()
        return jsonify(web_config.settings)
    else:
        # POST - Save settings
        data = request.json or {}
        for key in DEFAULT_SETTINGS.keys():
            if key in data:
                if isinstance(DEFAULT_SETTINGS[key], bool):
                    web_config.settings[key] = bool(data[key])
                else:
                    web_config.settings[key] = str(data[key])
                    
        web_config.save_settings()
        return jsonify({"success": True})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Zwraca status pingowania oraz usług na Raspberry Pi."""
    host = web_config.settings.get("rpi_host", "")
    
    # 1. Ping
    ping_ok = False
    if host:
        ping_ok = deployment_logic.ping_host(host)
        
    # 2. Services
    ind_ok = False
    vid_ok = False
    
    # We do a fast ssh check if ping is successful
    if ping_ok:
        creds = {
            "rpi_host": web_config.settings.get("rpi_host", ""),
            "rpi_user": web_config.settings.get("rpi_user", ""),
            "rpi_pass": web_config.settings.get("rpi_pass", ""),
            "rpi_key_path": web_config.settings.get("rpi_key_path", "") if web_config.settings.get("rpi_use_key", False) else None,
            "rpi_key_passphrase": web_config.settings.get("rpi_key_passphrase", "") if web_config.settings.get("rpi_use_key", False) else None,
        }
        try:
            ssh = deployment_logic.connect_ssh(
                lambda _msg, _lvl: None,
                web_config.translate,
                creds["rpi_host"],
                creds["rpi_user"],
                creds["rpi_pass"],
                creds["rpi_key_path"],
                creds["rpi_key_passphrase"],
                timeout=1.5
            )
            if ssh:
                app_type = web_config.settings.get("app_type", "RCSIM_DOCKER")
                if app_type == "RCSIM_MCS":
                    ind_ok = deployment_logic.check_remote_service_status(ssh, "usb_rc.service")
                    vid_ok = ind_ok
                else:
                    ind_ok = deployment_logic.check_remote_service_status(ssh, "rcsim_industrial")
                    vid_ok = deployment_logic.check_remote_service_status(ssh, "mediamtx.service")
                ssh.close()
        except Exception:
            pass

    return jsonify({
        "ping": ping_ok,
        "ui_locked": is_ui_locked,
        "progress": progress_value,
        "services": {
            "industrial": ind_ok,
            "video": vid_ok
        }
    })

@app.route('/api/fetch_pc_ip', methods=['POST'])
def fetch_pc_ip():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        try:
            ts_ip = subprocess.check_output(["tailscale", "ip", "-4"], timeout=2).decode().strip()
            if ts_ip:
                ip = ts_ip
        except Exception:
            pass
        web_config.settings["pc_tailscale_ip"] = ip
        web_config.save_settings()
        push_log(f"Fetched IP: {ip}", "info")
        return jsonify({"success": True, "ip": ip})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/browse_directory', methods=['POST'])
def browse_directory():
    """Otwiera natywny dialog systemu operacyjnego do wyboru folderu na komputerze PC."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Otwieramy tymczasowe okno Tkintera w bezpiecznym wątku
        result = []
        def picker():
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askdirectory(title="Select Project Source Directory")
            root.destroy()
            result.append(path)
            
        t = threading.Thread(target=picker)
        t.start()
        t.join()
        
        selected_path = result[0] if result else ""
        if selected_path:
            # Normalizujemy ukośniki pod Windows na forward-slashe
            selected_path = selected_path.replace("\\", "/")
            web_config.settings["project_source"] = selected_path
            web_config.save_settings()
            return jsonify({"success": True, "path": selected_path})
        return jsonify({"success": False, "error": "No directory selected"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/browse_file', methods=['POST'])
def browse_file():
    """Otwiera natywny dialog systemu operacyjnego do wyboru pliku (klucza SSH) na komputerze PC."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        result = []
        def picker():
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askopenfilename(title="Select SSH Private Key")
            root.destroy()
            result.append(path)
            
        t = threading.Thread(target=picker)
        t.start()
        t.join()
        
        selected_path = result[0] if result else ""
        if selected_path:
            selected_path = selected_path.replace("\\", "/")
            web_config.settings["rpi_key_path"] = selected_path
            web_config.save_settings()
            return jsonify({"success": True, "path": selected_path})
        return jsonify({"success": False, "error": "No file selected"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/action/<name>', methods=['POST'])
def run_action(name):
    web_config.load_settings()
    conf = web_config.get_deployment_config()
    
    def on_complete(success: bool, message: str):
        if success:
            push_log(message, "success")
        else:
            push_log(message, "error")
            
    if name == 'test_connection':
        run_in_background(deployment_logic.test_ssh, push_log, web_config.translate, conf, on_complete)
        
    elif name == 'detect_cameras':
        def wrapper():
            deployment_logic.detect_cameras(
                push_log,
                web_config.translate,
                conf,
                on_complete
            )
        run_in_background(wrapper)
        
    elif name == 'scan_hardware':
        def on_scan_complete(success, results):
            if success:
                push_log("Hardware scan completed successfully!", "success")
                i2c = results.get("i2c", [])
                uart = results.get("uart", {})
                cam = results.get("camera", "NONE")
                
                if "68" in i2c or "69" in i2c:
                    if "77" in i2c:
                        web_config.settings["imu_driver"] = "native_bmx160_bmp388"
                        push_log("Detected IMU: BMX160 + BMP388 (0x68, 0x77)", "info")
                    else:
                        web_config.settings["imu_driver"] = "native_mpu6050"
                        push_log("Detected IMU: MPU6050/9250 (0x68)", "info")
                        
                if "gps" in uart:
                    web_config.settings["gps_enabled"] = True
                    web_config.settings["gps_port"] = uart["gps"]
                    push_log(f"GPS auto-configured on {uart['gps']}", "info")
                    
                if "lidar" in uart:
                    web_config.settings["lidar_enabled"] = True
                    web_config.settings["lidar_port"] = uart["lidar"]
                    push_log(f"Lidar auto-configured on {uart['lidar']}", "info")
                    
                if cam != "NONE":
                    web_config.settings["camera_type"] = cam
                    push_log(f"Camera auto-detected: {cam}", "info")
                    
                web_config.save_settings()
            else:
                push_log("Hardware scan failed.", "error")
                
        run_in_background(deployment_logic.scan_hardware_rpi, push_log, web_config.translate, conf, on_scan_complete)
        
    elif name == 'deploy_full':
        fast_mode = bool(web_config.settings.get("fast_mode", True))
        run_in_background(
            deployment_logic.run_full_deployment,
            push_log,
            web_config.translate,
            update_progress,
            conf,
            on_complete,
            fast_mode=fast_mode
        )
        
    elif name == 'deploy_docker_update':
        run_in_background(
            deployment_logic.run_docker_update,
            push_log,
            web_config.translate,
            update_progress,
            conf,
            on_complete
        )
        
    elif name == 'deploy_hot':
        run_in_background(
            deployment_logic.run_hot_deploy,
            push_log,
            web_config.translate,
            update_progress,
            conf,
            on_complete
        )
        
    elif name == 'fast_camera_update':
        run_in_background(
            deployment_logic.run_camera_update,
            push_log,
            web_config.translate,
            update_progress,
            conf,
            on_complete
        )
        
    elif name == 'backup_docker':
        backup_path = os.path.expanduser("~/rcsim_docker_backup.tar.gz")
        run_in_background(
            deployment_logic.run_backup,
            push_log,
            web_config.translate,
            update_progress,
            conf,
            backup_path,
            lambda success, msg: on_complete(success, f"Backup saved to: {backup_path}" if success else msg)
        )
        
    elif name == 'restart_service':
        def restart_task():
            try:
                ssh = deployment_logic.connect_ssh(push_log, web_config.translate, 
                                                conf["rpi_host"], conf["rpi_user"], conf["rpi_pass"],
                                                conf["rpi_key_path"], conf["rpi_key_passphrase"])
                if ssh:
                    app_type = web_config.settings.get("app_type", "RCSIM_DOCKER")
                    if deployment_logic.restart_service(ssh, app_type=app_type):
                        push_log("Service restarted.", "success")
                    else:
                        push_log("Failed to restart service.", "error")
                    ssh.close()
            except Exception as e:
                push_log(f"Restart error: {e}", "error")
        run_in_background(restart_task)
        
    elif name == 'reboot_pi':
        def reboot_task():
            try:
                ssh = deployment_logic.connect_ssh(push_log, web_config.translate, 
                                                conf["rpi_host"], conf["rpi_user"], conf["rpi_pass"],
                                                conf["rpi_key_path"], conf["rpi_key_passphrase"])
                if ssh:
                    deployment_logic.reboot_pi(ssh)
                    push_log("Reboot command sent.", "success")
                    ssh.close()
            except Exception as e:
                push_log(f"Reboot error: {e}", "error")
        run_in_background(reboot_task)
        
    elif name == 'run_diagnostics':
        run_in_background(
            deployment_logic.run_diagnostics,
            push_log,
            web_config.translate,
            conf,
            on_complete
        )
        
    elif name in ('show_logs', 'show_build_logs'):
        def logs_task():
            try:
                ssh = deployment_logic.connect_ssh(push_log, web_config.translate, 
                                                conf["rpi_host"], conf["rpi_user"], conf["rpi_pass"],
                                                conf["rpi_key_path"], conf["rpi_key_passphrase"])
                if ssh:
                    app_type = web_config.settings.get("app_type", "RCSIM_DOCKER")
                    if name == 'show_logs':
                        logs = deployment_logic.fetch_logs(ssh, app_type=app_type)
                    else:
                        logs = deployment_logic.fetch_build_logs(ssh, app_type=app_type)
                    if logs:
                        clean = deployment_logic.strip_ansi_codes(logs)
                        for line in clean.splitlines():
                            push_log(line, "verbose")
                    else:
                        push_log("No logs retrieved.", "warning")
                    ssh.close()
            except Exception as e:
                push_log(f"Logs error: {e}", "error")
        run_in_background(logs_task)
        
    return jsonify({"success": True})

@app.route('/api/logs')
def stream_logs():
    """Server-Sent Events streaming of logs."""
    def generate():
        while True:
            try:
                log_item = log_queue.get(timeout=2.0)
                import json
                yield f"data: {json.dumps(log_item)}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    push_log("Server shutdown requested. Closing application...", "warning")
    def exit_process():
        time.sleep(1.0)
        os._exit(0)
    threading.Thread(target=exit_process, daemon=True).start()
    return jsonify({"success": True})

def start_server():
    port = 5000
    for p in range(5000, 5010):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('127.0.0.1', p))
            s.close()
            port = p
            break
        except Exception:
            continue
            
    print(f"Starting web server on http://localhost:{port}")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host='127.0.0.1', port=port, debug=False)

if __name__ == '__main__':
    start_server()
