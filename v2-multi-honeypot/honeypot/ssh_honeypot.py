import paramiko
import socket
import sys
import threading
import requests
from datetime import datetime, timedelta

# Importer le logger partagé
try:
    from . import shared_logger
except ImportError:
    import shared_logger

# --- Configuration Honeypot ---
SERVER_ADDRESS = '0.0.0.0'
SERVER_PORT = 22
HOST_KEY_FILE = 'server_key.pem'

# --- Configuration Bonus Brute-Force ---
BRUTEFORCE_THRESHOLD = 5
BRUTEFORCE_TIMEFRAME_SEC = 60
WEBHOOK_URL = ""  # Mettez ici votre URL de webhook
ip_attempts = {}
attempts_lock = threading.Lock()

# Générer une clé de serveur
try:
    host_key = paramiko.RSAKey(filename=HOST_KEY_FILE)
except IOError:
    print("Génération d'une nouvelle clé de serveur SSH...")
    host_key = paramiko.RSAKey.generate(2048)
    host_key.write_private_key_file(HOST_KEY_FILE)

def send_webhook_alert(ip, count):
    """Envoie une alerte via webhook."""
    if not WEBHOOK_URL:
        return
    message = f"🚨 Alerte Brute-Force SSH! {count} tentatives de {ip} en 1 minute."
    payload = {'content': message}
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Échec de l'envoi du webhook SSH: {e}")

def check_bruteforce(ip):
    """Vérifie si une IP est en train de brute-force."""
    with attempts_lock:
        now = datetime.now()
        if ip not in ip_attempts:
            ip_attempts[ip] = []
        
        valid_attempts = [t for t in ip_attempts[ip] if now - t < timedelta(seconds=BRUTEFORCE_TIMEFRAME_SEC)]
        valid_attempts.append(now)
        ip_attempts[ip] = valid_attempts
        
        if len(valid_attempts) > BRUTEFORCE_THRESHOLD:
            print(f"*** BRUTE-FORCE SSH DÉTECTÉ *** de {ip}")
            log_data = {
                "source_ip": ip,
                "source_port": 0,
                "username": "N/A",
                "password": "N/A",
                "status": "bruteforce_detected",
                "attempt_count": len(valid_attempts)
            }
            shared_logger.log_event('ssh', log_data)
            send_webhook_alert(ip, len(valid_attempts))
            ip_attempts[ip] = []

class HoneypotAuthHandler(paramiko.ServerInterface):
    """Gère l'authentification (rejette tout mais enregistre)."""
    def __init__(self, client_address):
        self.client_ip = client_address[0]
        self.client_port = client_address[1]

    def check_auth_password(self, username, password):
        log_data = {
            "source_ip": self.client_ip,
            "source_port": self.client_port,
            "username": username,
            "password": password,
            "status": "failed_auth",
            "auth_type": "password"
        }
        shared_logger.log_event('ssh', log_data)
        check_bruteforce(self.client_ip)
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        log_data = {
            "source_ip": self.client_ip,
            "source_port": self.client_port,
            "username": username,
            "key_fingerprint": f"key_type={key.get_name()} len={len(key.get_fingerprint())}",
            "status": "failed_auth",
            "auth_type": "publickey"
        }
        shared_logger.log_event('ssh', log_data)
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def check_channel_shell_request(self, channel):
        return True

    def check_channel_exec_request(self, channel, command):
        cmd_str = command.decode('utf-8', 'ignore')
        log_data = {
            "source_ip": self.client_ip,
            "source_port": self.client_port,
            "status": "command_exec",
            "command": cmd_str
        }
        shared_logger.log_event('ssh', log_data)
        channel.send_exit_status(1) 
        return True


class HoneypotConnection(threading.Thread):
    def __init__(self, client, client_address):
        super().__init__()
        self.client = client
        self.client_address = client_address

    def run(self):
        print(f"Nouvelle connexion SSH de {self.client_address[0]}:{self.client_address[1]}")
        try:
            transport = paramiko.Transport(self.client)
            transport.add_server_key(host_key)
            auth_handler = HoneypotAuthHandler(self.client_address)
            transport.start_server(server=auth_handler)
            
            channel = transport.accept(20)
            if channel is not None:
                channel.send("Welcome.\r\n$ ")
                cmd_buffer = ""
                while True:
                    data = channel.recv(1024).decode('utf-8', 'ignore')
                    if not data or '\r' in data:
                        cmd = cmd_buffer.strip()
                        if cmd:
                            log_data = {
                                "source_ip": self.client_address[0],
                                "source_port": self.client_address[1],
                                "status": "command_shell",
                                "command": cmd
                            }
                            shared_logger.log_event('ssh', log_data)
                            channel.send(f"-bash: {cmd}: command not found\r\n$ ")
                        cmd_buffer = ""
                        if not data or cmd == "exit":
                            break
                    else:
                        cmd_buffer += data
                channel.close()
            transport.close()
        except Exception as e:
            if 'Error reading SSH protocol banner' not in str(e): # Ignore common scan noise
                print(f"Erreur de connexion/transport SSH: {e}")
        finally:
            self.client.close()


def start_server():
    """Fonction de démarrage pour le thread SSH."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((SERVER_ADDRESS, SERVER_PORT))
        sock.listen(100)
        print(f"Démarrage du honeypot SSH sur {SERVER_ADDRESS}:{SERVER_PORT}...")

        while True:
            client, client_address = sock.accept()
            HoneypotConnection(client, client_address).start()

    except Exception as e:
        print(f"Erreur fatale du socket SSH: {e}")
        sys.exit(1)
