"""
src/hardware/system_actions.py
Bezpieczne funkcje systemowe do zarządzania Raspberry Pi 5 z poziomu Web UI.
"""
import logging
import subprocess

logger = logging.getLogger(__name__)

def restart_service() -> bool:
    """Restartuje główną usługę usb_rc."""
    try:
        logger.info("system_actions: restartowanie usługi usb_rc za pomocą systemctl...")
        subprocess.Popen(["sudo", "systemctl", "restart", "usb_rc.service"])
        return True
    except Exception as e:
        logger.error("system_actions: Błąd restartu usługi: %s", e)
        return False

def reboot_system() -> bool:
    """Restartuje całe Raspberry Pi."""
    try:
        logger.warning("system_actions: Urządzenie zostanie zrestartowane natychmiast!")
        subprocess.Popen(["sudo", "reboot"])
        return True
    except Exception as e:
        logger.error("system_actions: Błąd restartu systemu: %s", e)
        return False

def shutdown_system() -> bool:
    """Zamyka bezpiecznie Raspberry Pi po wylądowaniu modelu."""
    try:
        logger.warning("system_actions: Bezpieczne wyłączanie zasilania systemu...")
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        return True
    except Exception as e:
        logger.error("system_actions: Błąd wyłączania systemu: %s", e)
        return False
