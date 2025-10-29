import json
import os
from datetime import datetime

LOG_DIR = '/var/log/honeypot'

def log_event(service_name, log_data):
    """
    Enregistre un événement dans le fichier de log JSON approprié.
    :param service_name: 'ssh', 'http', 'ftp', etc.
    :param log_data: Un dictionnaire contenant les données à logger.
    """
    
    log_file = os.path.join(LOG_DIR, f"{service_name}-honeypot.log")
    
    # Enrichir le log avec des données communes
    full_log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": service_name,
        "data": log_data
    }
    
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(full_log_entry) + '\n')
    except Exception as e:
        print(f"Erreur lors de l'écriture du log pour {service_name}: {e}")
