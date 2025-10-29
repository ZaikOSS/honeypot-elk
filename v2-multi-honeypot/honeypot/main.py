import sys
import os
import threading
import time

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

# Importer les modules honeypot
try:
    from . import ssh_honeypot
    from . import http_honeypot
    from . import ftp_honeypot
except ImportError:
    # Gérer le cas où le script est exécuté directement
    import ssh_honeypot
    import http_honeypot
    import ftp_honeypot

LOG_DIR = '/var/log/honeypot'

def apply_seccomp_filter():
    """Applique un filtre Seccomp pour bloquer execve."""
    print("Application du filtre Seccomp global...")
    try:
        f = seccomp.SyscallFilter(seccomp.ALLOW)
        f.add_rule(seccomp.ERRNO(1), "execve")
        f.add_rule(seccomp.ERRNO(1), "execveat")
        f.load()
        print("Filtre Seccomp chargé. 'execve' est maintenant bloqué pour ce processus et ses enfants.")
    except Exception as e:
        print(f"CRITIQUE: Échec du chargement du filtre Seccomp: {e}")
        sys.exit(1)

def start_service(name, start_function):
    """Démarre un service dans un thread dédié."""
    print(f"Démarrage du service {name}...")
    try:
        thread = threading.Thread(target=start_function, name=f"{name}-Thread")
        thread.daemon = True  # Permet au programme de se fermer même si les threads tournent
        thread.start()
        print(f"Service {name} démarré.")
        return thread
    except Exception as e:
        print(f"Erreur lors du démarrage du service {name}: {e}")

if __name__ == "__main__":
    # 1. Appliquer le confinement Seccomp
    apply_seccomp_filter() # Activé pour le moment, voir note Dockerfile
    
    # 2. Assurer que le dossier de log existe
    print(f"Vérification du dossier de log : {LOG_DIR}")
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 3. Démarrer les services
    services = {
        "SSH": ssh_honeypot.start_server,
        "HTTP": http_honeypot.start_server,
        "FTP": ftp_honeypot.start_server,
    }
    
    threads = []
    for name, func in services.items():
        threads.append(start_service(name, func))

    # 4. Garder le script principal en vie
    print("Tous les services sont lancés. Le conteneur est opérationnel.")
    try:
        while True:
            # Vérifier si un thread est mort
            for t in threads:
                if not t.is_alive():
                    print(f"ERREUR: Le thread {t.name} est mort !")
                    # Gérer le redémarrage si nécessaire
            time.sleep(60)
    except KeyboardInterrupt:
        print("Arrêt des services...")
        sys.exit(0)
