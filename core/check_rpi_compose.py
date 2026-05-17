import os

import paramiko


def check_rpi_compose():
    try:
        # Load credentials from environment variables / Pobierz dane z env
        host = os.environ.get("RCSIM_RPI_IP", "192.168.31.224")
        user = os.environ.get("RCSIM_RPI_USER", "pi")
        pwd = os.environ.get(
            "RCSIM_RPI_PASS", "1"
        )  # Fallback to '1' for backward compatibility

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=pwd, timeout=15)

        print("--- RPi docker-compose.yml ---")
        stdin, stdout, stderr = client.exec_command(
            "cat /home/pi/rcsim_project/docker-compose.yml"
        )
        print(stdout.read().decode("utf-8"))

        client.close()
    except Exception as e:
        print(f"Check failed: {e}")


if __name__ == "__main__":
    check_rpi_compose()
