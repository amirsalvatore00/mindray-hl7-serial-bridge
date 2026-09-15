import socket
import serial
import json
import time
import threading
import logging
import platform
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
LOG_FILE = os.path.join(BASE_DIR, "server_bridge_log.txt")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"[!] Cannot load config.json: {e}")
        sys.exit(1)

def check_ping(ip):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', '-w', '1000', ip]
    try:
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0
    except Exception:
        return False

stop_event = threading.Event()

def tcp_to_serial(sock, ser):
    while not stop_event.is_set():
        try:
            sock.settimeout(1.0)
            data = sock.recv(4096)
            if not data:
                logging.warning("[!] Mindray disconnected.")
                break
            ser.write(data)
            logging.info(f"[TCP->COM] {len(data)} bytes")
        except socket.timeout:
            continue
        except Exception as e:
            logging.warning(f"[!] TCP Error: {e}")
            break
    stop_event.set()

def serial_to_tcp(sock, ser):
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                sock.sendall(data)
                logging.info(f"[COM->TCP] {len(data)} bytes")
            time.sleep(0.05)
        except Exception as e:
            logging.warning(f"[!] Serial Error: {e}")
            break
    stop_event.set()

def scan_open_ports(ip, ports):
    open_ports = []
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.4)
                if s.connect_ex((ip, port)) == 0:
                    open_ports.append(port)
                    logging.info(f"[SCAN] Port {port} is OPEN on {ip}")
        except Exception:
            pass
    return open_ports

def run_bridge(sock, ser):
    t1 = threading.Thread(target=tcp_to_serial, args=(sock, ser), daemon=True)
    t2 = threading.Thread(target=serial_to_tcp, args=(sock, ser), daemon=True)
    t1.start()
    t2.start()
    while not stop_event.is_set():
        time.sleep(1)

def main():
    logging.info("=" * 60)
    logging.info("MINDRAY HL7 SMART BRIDGE - STARTED")
    logging.info("=" * 60)

    config = load_config()
    mindray_ip = config.get('mindray_ip', '192.168.200.191')
    com_port = config.get('com_port', 'COM10')
    baudrate = config.get('baudrate', 9600)
    scan_ports = config.get('scan_ports', [5100, 5200, 5000, 3100, 8080])
    listen_port = config.get('listen_port', 5200)
    local_ip = config.get('local_ip', '0.0.0.0')

    logging.info(f"Config: Mindray={mindray_ip} | COM={com_port}@{baudrate}")
    logging.info(f"Scan list: {scan_ports}")

    while True:
        stop_event.clear()
        ser = None
        sock = None
        server_sock = None

        try:
            ser = serial.Serial(com_port, baudrate, timeout=1)
            logging.info(f"[OK] Virtual Port {com_port} opened.")
        except Exception as e:
            logging.error(f"[FAIL] Cannot open {com_port}: {e} | retry in 5s")
            time.sleep(5)
            continue

        if not check_ping(mindray_ip):
            logging.warning(f"[!] Ping to {mindray_ip} failed. Check cable. Retry in 5s.")
            try: ser.close()
            except: pass
            time.sleep(5)
            continue
        logging.info(f"[OK] Ping to {mindray_ip} succeeded.")

        logging.info("[*] Scanning Mindray for open TCP ports...")
        open_ports = scan_open_ports(mindray_ip, scan_ports)

        connected = False

        if open_ports:
            target_port = open_ports[0]
            logging.info(f"[AUTO] Mindray acts as SERVER. Connecting as CLIENT to port {target_port}...")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                sock.settimeout(5.0)
                sock.connect((mindray_ip, target_port))
                sock.settimeout(None)
                logging.info(f"[+] Connected to Mindray on port {target_port}")
                run_bridge(sock, ser)
                connected = True
            except Exception as e:
                logging.error(f"[!] Client Mode Error: {e}")

        if not connected:
            logging.info(f"[AUTO] No open ports. Mindray acts as CLIENT. We listen on {local_ip}:{listen_port}")
            try:
                server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_sock.bind((local_ip, listen_port))
                server_sock.listen(1)
                server_sock.settimeout(2.0)
                logging.info(f"[*] Listening as SERVER on {local_ip}:{listen_port} ...")

                while not stop_event.is_set():
                    try:
                        client_sock, addr = server_sock.accept()
                        logging.info(f"[+] Mindray connected from {addr}")
                        run_bridge(client_sock, ser)
                        try: client_sock.close()
                        except: pass
                        break
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logging.error(f"[!] Accept Error: {e}")
                        break
            except Exception as e:
                logging.error(f"[!] Server Mode Error: {e}")

        stop_event.set()
        try:
            if sock: sock.close()
        except: pass
        try:
            if server_sock: server_sock.close()
        except: pass
        try:
            if ser: ser.close()
        except: pass

        logging.info("[*] Restarting engine in 5 seconds...\n")
        time.sleep(5)

if __name__ == "__main__":
    main()