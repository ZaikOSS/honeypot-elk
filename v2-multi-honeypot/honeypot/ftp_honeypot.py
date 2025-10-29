from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

# Importer le logger partagé
try:
    from . import shared_logger
except ImportError:
    import shared_logger

class HoneypotFTPHandler(FTPHandler):
    """
    Handler FTP qui logue les tentatives et les commandes.
    """
    
    def on_connect(self):
        """Appelé lors de la connexion."""
        log_data = {
            "source_ip": self.remote_ip,
            "source_port": self.remote_port,
            "status": "connect"
        }
        shared_logger.log_event('ftp', log_data)

    def on_login(self, username, password, *args, **kwargs):
        """Appelé lors d'une tentative de login."""
        log_data = {
            "source_ip": self.remote_ip,
            "source_port": self.remote_port,
            "username": username,
            "password": password,
            "status": "failed_auth"
        }
        shared_logger.log_event('ftp', log_data)
        
        # Rejeter systématiquement
        self.respond("530 Login incorrect.")
        self.close_when_done()

    def on_login_failed(self, username, password, *args, **kwargs):
        """Alternative si on_login n'est pas appelé (ex: user inconnu)."""
        log_data = {
            "source_ip": self.remote_ip,
            "source_port": self.remote_port,
            "username": username,
            "password": password,
            "status": "failed_auth_unknown_user"
        }
        shared_logger.log_event('ftp', log_data)
        
    def on_disconnect(self):
        """Appelé lors de la déconnexion."""
        pass # Optionnel

    def ftp_CWD(self, path):
        """Logue les tentatives de changement de répertoire."""
        log_data = {
            "source_ip": self.remote_ip,
            "source_port": self.remote_port,
            "command": "CWD",
            "argument": path,
            "status": "denied"
        }
        shared_logger.log_event('ftp', log_data)
        self.respond("550 No such file or directory.")

    # Vous pouvez surcharger d'autres commandes FTP (STOR, RETR, etc.) de la même manière

def start_server():
    """Fonction de démarrage pour le thread FTP."""
    
    # L'authorizer rejette tout mais est nécessaire
    authorizer = DummyAuthorizer()
    # On ajoute un utilisateur "anonyme" que l'on ne validera jamais,
    # pour permettre à l'handler de traiter 'on_login'
    authorizer.add_user("anonymous", "nopass", "/tmp", perm="r") 
    authorizer.add_user("admin", "admin", "/tmp", perm="r")
    
    handler = HoneypotFTPHandler
    handler.authorizer = authorizer
    
    # Bannière FTP
    handler.banner = "220 Microsoft FTP Service"
    
    server_address = ('0.0.0.0', 21)
    server = FTPServer(server_address, handler)
    
    # configurer le logging
    server.max_cons = 256
    server.max_cons_per_ip = 5
    
    print(f"Démarrage du honeypot FTP sur 0.0.0.0:21...")
    try:
        server.serve_forever()
    except Exception as e:
        print(f"Erreur fatale du serveur FTP: {e}")
        import sys
        sys.exit(1)

if __name__ == '__main__':
    # Pour des tests directs
    start_server()
