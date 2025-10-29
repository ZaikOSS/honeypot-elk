from flask import Flask, request, abort, make_response

# Importer le logger partagé
try:
    from . import shared_logger
except ImportError:
    import shared_logger

app = Flask(__name__)

FAKE_SERVER_NAME = "Apache/2.4.29 (Ubuntu)"

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH'])
def catch_all(path):
    """
    Capture toutes les requêtes, les logue, et renvoie une fausse page.
    """
    try:
        # Tenter de récupérer les données (brutes ou formulaire)
        if request.form:
            data = request.form.to_dict()
        elif request.data:
            data = request.data.decode('utf-8', 'ignore')
        else:
            data = None

        log_data = {
            "source_ip": request.remote_addr,
            "source_port": request.environ.get('REMOTE_PORT'),
            "method": request.method,
            "path": request.full_path,
            "headers": dict(request.headers),
            "data": data
        }
        
        shared_logger.log_event('http', log_data)

    except Exception as e:
        print(f"Erreur lors du logging HTTP: {e}")

    # Simuler une page "Not Found" Apache
    html_response = """
    <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
    <html><head>
    <title>404 Not Found</title>
    </head><body>
    <h1>Not Found</h1>
    <p>The requested URL was not found on this server.</p>
    <hr>
    <address>Apache/2.4.29 (Ubuntu) Server at 127.0.0.1 Port 80</address>
    </body></html>
    """
    
    response = make_response(html_response, 404)
    response.headers['Server'] = FAKE_SERVER_NAME
    response.headers['Content-Type'] = 'text/html; charset=iso-8859-1'
    return response

def start_server():
    """Fonction de démarrage pour le thread HTTP."""
    print(f"Démarrage du honeypot HTTP sur 0.0.0.0:80...")
    try:
        # Utiliser 'waitress' ou 'gunicorn' serait mieux en prod,
        # mais le serveur de dev de Flask est suffisant pour un honeypot.
        app.run(host='0.0.0.0', port=80)
    except Exception as e:
        print(f"Erreur fatale du serveur HTTP: {e}")
        import sys
        sys.exit(1)

if __name__ == '__main__':
    # Pour des tests directs
    start_server()
