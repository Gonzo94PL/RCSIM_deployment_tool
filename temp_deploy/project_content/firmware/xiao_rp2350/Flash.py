import os
import sys
import time
import paramiko

host = "192.168.31.224"
user = "pi"
password = "1"
local_file = r"C:\Users\Mateusz\Desktop\RCSIM27.04monacoSLAM\RCSIM_MCS\firmware\xiao_rp2350\firmware.uf2"
remote_file = "/home/pi/firmware.uf2"

print(f"Connecting to {host} via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(host, username=user, password=password)
    print("Connected! Uploading firmware.uf2 via SFTP...")
    
    sftp = ssh.open_sftp()
    sftp.put(local_file, remote_file)
    sftp.close()
    print("Upload completed successfully!")
    
    print("Stopping usb_rc.service to release /dev/ttyACM0...")
    stdin, stdout, stderr = ssh.exec_command("echo '1' | sudo -S systemctl stop usb_rc.service")
    stdout.read()
    time.sleep(1.0)
    
    print("Detecting Seeed Studio XIAO RP2350 serial port dynamically on RPi5...")
    py_code = """
import serial
import serial.tools.list_ports
ports = [p.device for p in serial.tools.list_ports.comports() if p.vid == 0x2886 or p.pid == 0x0058]
if ports:
    print('Found XIAO RP2350 on:', ports[0])
    try:
        serial.Serial(ports[0], 1200).close()
        print('Sent 1200bps reset touch.')
    except Exception as e:
        print('Error during reset:', e)
else:
    print('No XIAO RP2350 port found via list_ports.')
"""
    # Write Python file on RPi
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/reset_xiao.py", "w") as f:
        f.write(py_code)
    sftp.close()
    
    stdin, stdout, stderr = ssh.exec_command("/opt/usb_rc_converter/venv/bin/python3 /tmp/reset_xiao.py")
    print(stdout.read().decode('utf-8'))
    print(stderr.read().decode('utf-8'))
    ssh.exec_command("rm -f /tmp/reset_xiao.py")
    
    # Wait for device to settle in bootloader mode
    print("Waiting for RP2350 to enter BOOTSEL mode...")
    import time
    for attempt in range(20):
        # Check if any RP-series device is in BOOTSEL mode using picotool
        stdin, stdout, stderr = ssh.exec_command("echo '1' | sudo -S picotool info")
        out_data = stdout.read().decode('utf-8')
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("Found RP2350 in BOOTSEL mode! Flashing...")
            stdin, stdout, stderr = ssh.exec_command("echo '1' | sudo -S picotool load -x /home/pi/firmware.uf2")
            print("Flash output:", stdout.read().decode('utf-8'))
            print("Flash error:", stderr.read().decode('utf-8'))
            print("Flashing completed successfully!")
            break
        else:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1.0)
    else:
        print("\nTimeout waiting for BOOTSEL mode.")
        
    print("Restarting usb_rc.service...")
    stdin, stdout, stderr = ssh.exec_command("echo '1' | sudo -S systemctl start usb_rc.service")
    stdout.read()
    print("Service started.")
    
    ssh.close()
except Exception as e:
    print("Error:", e)
    sys.exit(1)