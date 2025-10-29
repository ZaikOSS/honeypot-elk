#!/bin/bash
#
# Ce script construit (ou reconstruit) les images Docker
# et démarre tous les services en arrière-plan (detached).

# Quitte immédiatement si une commande échoue
set -e

# Se place dans le répertoire racine du projet (où se trouve docker-compose.yml)
SCRIPT_DIR=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
cd "$PROJECT_ROOT"

echo "Démarrage du build et lancement de la pile Honeypot-ELK v2..."

# --build: Force la reconstruction des images
# -d: Lance en mode "detached" (arrière-plan)
docker compose up --build -d

echo "-------------------------------------"
echo "Services démarrés. Vérification du statut :"
echo "-------------------------------------"

# Attend 3 secondes que les services se stabilisent avant de montrer le statut
sleep 3
docker compose ps

echo -e "\nPour voir les logs du honeypot, lancez :"
echo "docker compose logs -f honeypot-platform"
echo "Pour voir les logs de tous les services, lancez :"
echo "docker compose logs -f"
