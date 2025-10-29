import paramiko
import socket
import sys
import threading
import json
import os
import requests
# Seccomp import: try the original name, else fallback to pyseccomp
try:
    import seccomp
except ImportError:
    try:
        import pyseccomp as seccomp
    except ImportError:
        print("CRITIQUE: Ni 'seccomp' ni 'pyseccomp' n'a été trouvé.")
        print("Veuillez installer 'pyseccomp' via pip.")
        sys.exit(1)

from datetime import datetime, timedelta

def apply_seccomp_filter():
    """Applique un filtre Seccomp pour bloquer execve."""
    print("Application du filtre Seccomp...")
    try:
        # 1. Crée un filtre qui autorise tout par défaut
        f = seccomp.SyscallFilter(seccomp.ALLOW)

        # 2. Ajoute une règle pour bloquer 'execve' et 'execveat'
        #    Retourne EPERM (Operation not permitted)
        f.add_rule(seccomp.ERRNO(1), "execve")
        f.add_rule(seccomp.ERRNO(1), "execveat")

        # 3. Charge le filtre
        f.load()
        print("Filtre Seccomp chargé. 'execve' est maintenant bloqué pour ce processus.")

        # --- DÉBUT DU BLOC DE TEST ---
        print("\n--- TEST SECCOMP (ATTENDU: ÉCHEC) ---")
        print("Tentative d'exécution de 'ls' via os.execvp...")
        try:
            # os.execvp tente de remplacer ce script par 'ls'
            # C'est l'appel système 'execve' que nous avons bloqué
            os.execvp("ls", ["ls", "/app"])
            
            # Si on arrive ici, le filtre a échoué
            print("TEST SECCOMP ÉCHOUÉ: 'execvp' a fonctionné.") 
        except OSError as e:
            # C'est le succès ! L'OS a refusé d'exécuter.
            print(f"TEST SECCOMP RÉUSSI: L'exécution a été bloquée avec succès !")
            print(f"Erreur attrapée: {e}")
        print("--- FIN DU TEST SECCOMP ---\n")
        # --- FIN DU BLOC DE TEST ---

    except Exception as e:
        print(f"CRITIQUE: Échec du chargement du filtre Seccomp: {e}")
        sys.exit(1) # Arrêter si la sécurité échoue

# --- Configuration Honeypot ---
SERVER_ADDRESS = '0.0.0.0'
SERVER_PORT = 22  # Le port 22 du conteneur (mappé à 2223 sur l'hôte)
LOG_FILE = '/var/log/honeypot/ssh-honeypot.log'

# --- Configuration Bonus Brute-Force  ---
BRUTEFORCE_THRESHOLD = 5
BRUTEFORCE_TIMEFRAME_SEC = 60
# Mettez ici votre URL de webhook (ex: Discord, Slack)
WEBHOOK_URL = "" 
ip_attempts = {}
attempts_lock = threading.Lock()

# Générer une clé de serveur
try:
    host_key = paramiko.RSAKey(filename='server_key.pem')
except IOError:
    print("Génération d'une nouvelle clé de serveur...")
    host_key = paramiko.RSAKey.generate(2048)
    host_key.write_private_key_file('server_key.pem')

def log_attempt(ip, port, username, password, status, commands=None):
    """Enregistre la tentative au format JSON."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "source_ip": ip,
        "source_port": port,
        "username": username,
        "password": password,
        "status": status,
        "commands": commands if commands else []
    }
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(f"Erreur lors de l'écriture du log: {e}")

def send_webhook_alert(ip, count):
    """Envoie une alerte via webhook."""
    if not WEBHOOK_URL:
        return

    message = f"🚨 Alerte Brute-Force! {count} tentatives de {ip} en 1 minute."
    payload = {'content': message}
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Échec de l'envoi du webhook: {e}")

def check_bruteforce(ip):
    """Vérifie si une IP est en train de brute-force."""
    with attempts_lock:
        now = datetime.now()
        
        # Initialiser l'IP si elle n'existe pas
        if ip not in ip_attempts:
            ip_attempts[ip] = []
        
        # Nettoyer les anciennes tentatives
        valid_attempts = [t for t in ip_attempts[ip] if now - t < timedelta(seconds=BRUTEFORCE_TIMEFRAME_SEC)]
        
        # Ajouter la tentative actuelle
        valid_attempts.append(now)
        ip_attempts[ip] = valid_attempts
        
        # Vérifier le seuil
        if len(valid_attempts) > BRUTEFORCE_THRESHOLD:
            print(f"*** BRUTE-FORCE DÉTECTÉ *** de {ip} ({len(valid_attempts)} tentatives)")
            # Loguer l'événement de brute-force
            log_attempt(ip, 0, "N/A", "N/A", "bruteforce_detected")
            # Envoyer l'alerte
            send_webhook_alert(ip, len(valid_attempts))
            # Réinitialiser le compteur pour éviter le spam d'alertes
            ip_attempts[ip] = []

class HoneypotAuthHandler(paramiko.ServerInterface):
    """Gère l'authentification (rejette tout mais enregistre)."""
    def __init__(self, client_address):
        self.client_ip = client_address[0]
        self.client_port = client_address[1]

    def check_auth_password(self, username, password):
        # Enregistre la tentative
        log_attempt(self.client_ip, self.client_port, username, password, "failed_auth")
        # Vérifie le brute-force
        check_bruteforce(self.client_ip)
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password'

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    # ... (le reste des méthodes pour simuler un shell et logger les commandes) ...
    def check_channel_shell_request(self, channel):
        return True

    def check_channel_exec_request(self, channel, command):
        # Log la commande et ferme
        cmd_str = command.decode('utf-8', 'ignore')
        log_attempt(self.client_ip, self.client_port, "N/A", "N/A", "command_exec", [cmd_str])
        channel.send_exit_status(1) 
        return True


class HoneypotConnection(threading.Thread):
    def __init__(self, client, client_address):
        super().__init__()
        self.client = client
        self.client_address = client_address

    def run(self):
        print(f"Nouvelle connexion de {self.client_address[0]}:{self.client_address[1]}")
        try:
            transport = paramiko.Transport(self.client)
            transport.add_server_key(host_key)
            auth_handler = HoneypotAuthHandler(self.client_address)
            transport.start_server(server=auth_handler)
            
            channel = transport.accept(20)
            if channel is not None:
                # Simuler un shell pour logger les commandes
                channel.send("Bienvenue.\r\n$ ")
                cmd_buffer = ""
                while True:
                    data = channel.recv(1024).decode('utf-8', 'ignore')
                    if not data or '\r' in data:
                        cmd = cmd_buffer.strip()
                        if cmd:
                            log_attempt(self.client_ip, self.client_port, "N/A", "N/A", "command_shell", [cmd])
                            channel.send(f"-bash: {cmd}: commande introuvable\r\n$ ")
                        cmd_buffer = ""
                        if not data or cmd == "exit":
                            break
                    else:
                        cmd_buffer += data
                channel.close()
            transport.close()
        except Exception as e:
            print(f"Erreur de connexion/transport: {e}")
        finally:
            self.client.close()


def start_server():
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
        print(f"Erreur fatale du socket: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Applique le filtre Seccomp au démarrage
    apply_seccomp_filter() 

    # Assure que le dossier de log existe
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    start_server()
