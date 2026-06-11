// Translations mapping
const translations = {
    "English": {
        "app-title": "RCSIM Deployment Tool",
        "app-subtitle": "v8.0.0 Web UI • Premium Edition",
        "header-connection": "🔑 Connection Settings",
        "header-source": "📂 Source & Platform Configuration",
        "header-network": "🌐 Network & Communication",
        "header-hardware": "⚙️ Hardware & Sensors",
        "header-video": "📹 Video & Streaming",
        "header-rtk": "🛰️ RTK Differential GNSS",
        "header-control": "⚡ Deployment Control",
        "header-utility": "🛠️ Utility Actions",
        "header-console": "Deployment Live Console",
        
        "btn-test-connection": "Test Connection",
        "btn-scan-hardware": "Scan Hardware (I2C/UART)",
        "btn-fetch": "Fetch",
        "btn-detect": "Detect CSI Cameras",
        "btn-low-latency": "Low Latency Profile",
        "btn-deploy-full": "🚀 FULL DEPLOYMENT",
        "btn-deploy-docker-update": "🐳 Docker Rebuild & Update",
        "btn-deploy-hot": "🔥 Hot Deploy Code (~30s)",
        "btn-cam-update": "Cam Config Only",
        "btn-backup": "Backup Docker Vol",
        "btn-restart": "Restart Service",
        "btn-reboot": "Reboot Pi",
        "btn-diagnostics": "Diagnostics",
        "btn-logs": "App Logs",
        "btn-build-logs": "Build Logs",
        "btn-clear": "Clear Console",
        "btn-browse": "Browse...",
        "btn-shutdown": "Shutdown Server",
        
        "opt-docker": "Standard RCSIM (Docker & MediaMTX)",
        "opt-mcs": "RCSIM MCS (Direct Services)",
        
        "rpi-host": "RPi Host/IP",
        "rpi-user": "SSH Username",
        "rpi-use-key": "Use SSH Private Key",
        "rpi-pass": "SSH Password",
        "rpi-key-path": "Key Path",
        "rpi-key-passphrase": "Key Passphrase",
        "new-ssh-pass": "New SSH Password (Optional)",
        "project-source": "Project Source Path",
        "app-type": "Application Platform Type",
        "pc-tailscale-ip": "PC IP (Tailscale)",
        "pc-udp-port": "PC UDP Telemetry Port",
        "rpi-udp-port": "RPi UDP Telemetry Port",
        "comm-mode": "Comm Mode",
        "comm-protocol": "Comm Protocol",
        "imu-driver": "IMU Driver",
        "gps-enabled": "Enable GPS",
        "lidar-enabled": "Enable LiDAR",
        "elrs-enabled": "Enable ELRS / MAVLink Serial",
        "camera-port": "Camera CSI Port",
        "camera-type": "Camera Sensor Type",
        "camera-resolution": "Resolution",
        "camera-fps": "FPS",
        "camera-bitrate": "Video Bitrate",
        "use-rtk": "Enable NTRIP RTK Client",
        "ntrip-host": "NTRIP Host",
        "ntrip-port": "NTRIP Port",
        "ntrip-mount": "Mount Point",
        "ntrip-user": "NTRIP Username",
        "ntrip-pass": "NTRIP Password",
        "fast-mode": "Fast Deploy (Skip OS Config)",
        "status-ind": "Industrial: Off",
        "status-vid": "Video: Off",
        "status-core": "Core Service: Off",
        "status-web": "Web Service: Off"
    },
    "Polski": {
        "app-title": "Narzędzie wdrożeniowe RCSIM",
        "app-subtitle": "v8.0.0 Web UI • Edycja Premium",
        "header-connection": "🔑 Ustawienia połączenia",
        "header-source": "📂 Konfiguracja źródła i platformy",
        "header-network": "🌐 Sieć i komunikacja",
        "header-hardware": "⚙️ Sprzęt i czujniki",
        "header-video": "📹 Wideo i strumieniowanie",
        "header-rtk": "🛰️ RTK pozycjonowanie GNSS",
        "header-control": "⚡ Kontrola wdrożenia",
        "header-utility": "🛠️ Akcje pomocnicze",
        "header-console": "Konsola wdrożeniowa na żywo",
        
        "btn-test-connection": "Testuj połączenie",
        "btn-scan-hardware": "Skanuj sprzęt (I2C/UART)",
        "btn-fetch": "Pobierz",
        "btn-detect": "Wykryj kamery CSI",
        "btn-low-latency": "Profil niskiej latencji",
        "btn-deploy-full": "🚀 PEŁNE WDROŻENIE",
        "btn-deploy-docker-update": "🐳 Aktualizacja i przebudowa Dockera",
        "btn-deploy-hot": "🔥 Hot Deploy Kodu (~30s)",
        "btn-cam-update": "Tylko konfiguracja kamery",
        "btn-backup": "Kopia Docker Vol",
        "btn-restart": "Restart usługi",
        "btn-reboot": "Restart RPi",
        "btn-diagnostics": "Diagnostyka",
        "btn-logs": "Logi aplikacji",
        "btn-build-logs": "Logi budowania",
        "btn-clear": "Wyczyść konsolę",
        "btn-browse": "Wybierz...",
        "btn-shutdown": "Wyłącz Serwer",
        
        "opt-docker": "Standardowy RCSIM (Docker i MediaMTX)",
        "opt-mcs": "RCSIM MCS (Bezpośrednie usługi)",
        
        "rpi-host": "Host/IP RPi",
        "rpi-user": "Użytkownik SSH",
        "rpi-use-key": "Użyj klucza prywatnego SSH",
        "rpi-pass": "Hasło SSH",
        "rpi-key-path": "Ścieżka klucza",
        "rpi-key-passphrase": "Hasło klucza (Passphrase)",
        "new-ssh-pass": "Nowe hasło SSH (Opcjonalnie)",
        "project-source": "Ścieżka źródłowa projektu",
        "app-type": "Typ platformy aplikacji",
        "pc-tailscale-ip": "IP komputera (Tailscale)",
        "pc-udp-port": "Port UDP telemetryczny PC",
        "rpi-udp-port": "Port UDP telemetryczny RPi",
        "comm-mode": "Tryb komunikacji",
        "comm-protocol": "Protokół komunikacji",
        "imu-driver": "Sterownik IMU",
        "gps-enabled": "Włącz GPS",
        "lidar-enabled": "Włącz LiDAR",
        "elrs-enabled": "Włącz ELRS / MAVLink Serial",
        "camera-port": "Port CSI kamery",
        "camera-type": "Typ sensora kamery",
        "camera-resolution": "Rozdzielczość",
        "camera-fps": "Klatki/s (FPS)",
        "camera-bitrate": "Bitrate wideo",
        "use-rtk": "Włącz klienta NTRIP RTK",
        "ntrip-host": "Host NTRIP",
        "ntrip-port": "Port NTRIP",
        "ntrip-mount": "Punkt montowania (Mount)",
        "ntrip-user": "Użytkownik NTRIP",
        "ntrip-pass": "Hasło NTRIP",
        "fast-mode": "Szybkie wdrożenie (pomiń OS)",
        "status-ind": "Przemysłowy: Wył",
        "status-vid": "Wideo: Wył",
        "status-core": "Usługa Core: Wył",
        "status-web": "Usługa Web: Wył"
    }
};

let currentLanguage = "English";

// DOM Elements
const inputFields = [
    'rpi_host', 'rpi_user', 'rpi_pass', 'rpi_use_key', 'rpi_key_path', 'rpi_key_passphrase',
    'new_ssh_pass', 'project_source', 'app_type', 'pc_tailscale_ip', 'pc_udp_port',
    'rpi_udp_port', 'comm_mode', 'comm_protocol', 'imu_driver', 'gps_enabled', 'gps_port',
    'gps_baudrate', 'lidar_enabled', 'lidar_port', 'lidar_baudrate', 'elrs_enabled',
    'elrs_port', 'elrs_baudrate', 'camera_port', 'camera_type', 'camera_resolution',
    'camera_fps', 'camera_bitrate', 'use_rtk', 'ntrip_host', 'ntrip_port', 'ntrip_mount',
    'ntrip_user', 'ntrip_pass', 'fast_mode'
];

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize SSE connection for logs
    connectSSE();

    // 2. Fetch and apply initial configs
    fetchConfig();

    // 3. Setup event listeners
    setupListeners();

    // 4. Start periodic status updates (every 2.5s)
    setInterval(updateStatus, 2500);
    updateStatus();
});

function connectSSE() {
    const term = document.getElementById('terminal-output');
    const es = new EventSource('/api/logs');
    
    es.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const line = document.createElement('div');
            line.className = `line ${data.level || 'info'}`;
            line.innerText = `[${data.time}] ${data.message}`;
            term.appendChild(line);
            term.scrollTop = term.scrollHeight;
        } catch(e) {}
    };
    
    es.onerror = () => {
        // Retry connection silently
    };
}

function fetchConfig() {
    fetch('/api/config')
        .then(res => res.json())
        .then(data => {
            inputFields.forEach(field => {
                const el = document.getElementById(field);
                if (!el) return;
                
                if (el.type === 'checkbox') {
                    el.checked = !!data[field];
                } else {
                    el.value = data[field] || '';
                }
            });
            
            // Adjust conditional visibility
            toggleSSHFields();
            togglePlatformFields();
            
            // Language
            fetch('/api/languages')
                .then(res => res.json())
                .then(langData => {
                    const selector = document.getElementById('lang-selector');
                    selector.value = langData.current;
                    setLanguage(langData.current);
                });
        });
}

function saveConfig() {
    const payload = {};
    inputFields.forEach(field => {
        const el = document.getElementById(field);
        if (!el) return;
        payload[field] = el.type === 'checkbox' ? el.checked : el.value;
    });

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
}

function setupListeners() {
    // Auto-save on field changes
    inputFields.forEach(field => {
        const el = document.getElementById(field);
        if (!el) return;
        el.addEventListener('change', () => {
            saveConfig();
            if (field === 'rpi_use_key') toggleSSHFields();
            if (field === 'app_type') togglePlatformFields();
        });
    });

    // Language Change
    document.getElementById('lang-selector').addEventListener('change', (e) => {
        const lang = e.target.value;
        fetch('/api/change_language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: lang })
        }).then(() => {
            setLanguage(lang);
        });
    });

    // Action button listeners
    setupActionButton('btn-test-connection', '/api/action/test_connection');
    setupActionButton('btn-scan-hardware', '/api/action/scan_hardware');
    setupActionButton('btn-detect-cameras', '/api/action/detect_cameras');
    setupActionButton('btn-deploy-full', '/api/action/deploy_full');
    setupActionButton('btn-deploy-docker-update', '/api/action/deploy_docker_update');
    setupActionButton('btn-deploy-hot', '/api/action/deploy_hot');
    setupActionButton('btn-fast-camera-update', '/api/action/fast_camera_update');
    setupActionButton('btn-backup-docker', '/api/action/backup_docker');
    setupActionButton('btn-restart-service', '/api/action/restart_service');
    setupActionButton('btn-reboot-pi', '/api/action/reboot_pi', true);
    setupActionButton('btn-run-diagnostics', '/api/action/run_diagnostics');
    setupActionButton('btn-show-logs', '/api/action/show_logs');
    setupActionButton('btn-show-build-logs', '/api/action/show_build_logs');

    // Low Latency Profile Apply
    document.getElementById('btn-low-latency').addEventListener('click', () => {
        document.getElementById('camera_resolution').value = "800x600";
        document.getElementById('camera_fps').value = "30";
        document.getElementById('camera_bitrate').value = "2 Mbps";
        saveConfig();
        const term = document.getElementById('terminal-output');
        const line = document.createElement('div');
        line.className = "line success";
        line.innerText = currentLanguage === 'Polski' ? "[SUCCESS] Zastosowano profil niskiej latencji (800x600, 30 FPS, 2 Mbps)" : "[SUCCESS] Low Latency profile applied (800x600, 30 FPS, 2 Mbps)";
        term.appendChild(line);
        term.scrollTop = term.scrollHeight;
    });

    // Fetch PC IP
    document.getElementById('btn-fetch-pc-ip').addEventListener('click', () => {
        fetch('/api/fetch_pc_ip', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('pc_tailscale_ip').value = data.ip;
                }
            });
    });

    // Browse Project Directory
    document.getElementById('btn-browse-project').addEventListener('click', () => {
        fetch('/api/browse_directory', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('project_source').value = data.path;
                }
            });
    });

    // Browse SSH Key File
    document.getElementById('btn-browse-key').addEventListener('click', () => {
        fetch('/api/browse_file', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('rpi_key_path').value = data.path;
                }
            });
    });

    // Shutdown Server
    document.getElementById('btn-shutdown-server').addEventListener('click', () => {
        if (confirm(currentLanguage === 'Polski' ? "Czy na pewno chcesz wyłączyć serwer aplikacji?" : "Are you sure you want to shut down the application server?")) {
            fetch('/api/shutdown', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    alert(currentLanguage === 'Polski' ? "Serwer został wyłączony. Możesz zamknąć tę kartę." : "Server shut down. You can close this tab.");
                    window.close();
                });
        }
    });

    // Clear console
    document.getElementById('btn-clear-console').addEventListener('click', () => {
        document.getElementById('terminal-output').innerHTML = '';
    });
}

function setupActionButton(buttonId, url, needsConfirm = false) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    btn.addEventListener('click', () => {
        if (needsConfirm && !confirm("Are you sure you want to proceed?")) {
            return;
        }
        
        btn.disabled = true;
        
        fetch(url, { method: 'POST' })
            .finally(() => {
                setTimeout(() => { btn.disabled = false; }, 2000);
            });
    });
}

function toggleSSHFields() {
    const useKey = document.getElementById('rpi_use_key').checked;
    if (useKey) {
        document.getElementById('password-mode-fields').classList.add('hidden');
        document.getElementById('key-mode-fields').classList.remove('hidden');
    } else {
        document.getElementById('password-mode-fields').classList.remove('hidden');
        document.getElementById('key-mode-fields').classList.add('hidden');
    }
}

function togglePlatformFields() {
    const type = document.getElementById('app_type').value;
    const isMcs = (type === 'RCSIM_MCS');
    
    const videoCard = document.getElementById('card-video');
    const rtkCard = document.getElementById('card-rtk');
    const actionBackup = document.getElementById('btn-backup-docker');
    const actionBuildLogs = document.getElementById('btn-show-build-logs');
    
    if (isMcs) {
        videoCard.classList.add('hidden');
        rtkCard.classList.add('hidden');
        if (actionBackup) actionBackup.disabled = true;
        if (actionBuildLogs) actionBuildLogs.disabled = true;
    } else {
        videoCard.classList.remove('hidden');
        rtkCard.classList.remove('hidden');
        if (actionBackup) actionBackup.disabled = false;
        if (actionBuildLogs) actionBuildLogs.disabled = false;
    }
    
    updateStatusLabels(type);
}

function updateStatus() {
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            const pingPill = document.getElementById('ping-status');
            const pingLabel = document.getElementById('lbl-status-ping') || pingPill.querySelector('.status-label');
            if (data.ping) {
                pingPill.className = "status-pill status-online";
                pingLabel.innerText = "RPi: Online";
            } else {
                pingPill.className = "status-pill status-offline";
                pingLabel.innerText = "RPi: Offline";
            }
            
            const indPill = document.getElementById('ind-status');
            const indLabel = document.getElementById('lbl-status-ind');
            const appType = document.getElementById('app_type').value;
            
            if (data.services.industrial) {
                indPill.className = "status-pill status-online";
                indLabel.innerText = appType === 'RCSIM_MCS' ? 
                    (currentLanguage === 'Polski' ? "Usługa Core: Wł" : "Core Service: On") :
                    (currentLanguage === 'Polski' ? "Przemysłowy: Wł" : "Industrial: On");
            } else {
                indPill.className = "status-pill status-offline";
                indLabel.innerText = appType === 'RCSIM_MCS' ? 
                    (currentLanguage === 'Polski' ? "Usługa Core: Wył" : "Core Service: Off") :
                    (currentLanguage === 'Polski' ? "Przemysłowy: Wył" : "Industrial: Off");
            }

            const vidPill = document.getElementById('vid-status');
            const vidLabel = document.getElementById('lbl-status-vid');
            if (data.services.video) {
                vidPill.className = "status-pill status-online";
                vidLabel.innerText = appType === 'RCSIM_MCS' ? 
                    (currentLanguage === 'Polski' ? "Usługa Web: Wł" : "Web Service: On") :
                    (currentLanguage === 'Polski' ? "Wideo: Wł" : "Video: On");
            } else {
                vidPill.className = "status-pill status-offline";
                vidLabel.innerText = appType === 'RCSIM_MCS' ? 
                    (currentLanguage === 'Polski' ? "Usługa Web: Wył" : "Web Service: Off") :
                    (currentLanguage === 'Polski' ? "Wideo: Wył" : "Video: Off");
            }

            const formInputs = document.querySelectorAll('input, select, button:not(.btn-danger):not(#btn-clear-console)');
            formInputs.forEach(el => {
                if (data.ui_locked) {
                    if (el.id !== 'btn-deploy-full' && el.id !== 'btn-deploy-docker-update' && el.id !== 'btn-deploy-hot') {
                        el.disabled = true;
                    }
                } else {
                    el.disabled = false;
                }
            });

            document.getElementById('deploy-progress').style.width = `${data.progress}%`;
        });
}

function updateStatusLabels(platformType) {
    const isMcs = (platformType === 'RCSIM_MCS');
    const labelInd = document.getElementById('lbl-status-ind');
    const labelVid = document.getElementById('lbl-status-vid');
    
    if (isMcs) {
        labelInd.innerText = currentLanguage === 'Polski' ? "Usługa Core: Wył" : "Core Service: Off";
        labelVid.innerText = currentLanguage === 'Polski' ? "Usługa Web: Wył" : "Web Service: Off";
    } else {
        labelInd.innerText = currentLanguage === 'Polski' ? "Przemysłowy: Wył" : "Industrial: Off";
        labelVid.innerText = currentLanguage === 'Polski' ? "Wideo: Wył" : "Video: Off";
    }
}

function setLanguage(lang) {
    currentLanguage = lang;
    const trans = translations[lang];
    if (!trans) return;
    
    // Translate standard label keys
    Object.keys(trans).forEach(key => {
        const el = document.getElementById(`lbl-${key}`);
        if (el) el.innerText = trans[key];
    });

    // Translate all elements with data-translate attributes
    document.querySelectorAll('[data-translate]').forEach(el => {
        const key = el.getAttribute('data-translate');
        if (trans[key]) {
            el.innerText = trans[key];
        }
    });
}
