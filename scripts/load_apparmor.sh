#!/bin/bash
#
# Ce script charge le profil AppArmor requis pour le honeypot.
# DOIT être exécuté avec sudo.

# Quitte immédiatement si une commande échoue
set -e
# Erreur si une variable non définie est utilisée
set -u

# Vérifie les permissions root
if [ "$EUID" -ne 0 ]; then
  echo "Erreur: Ce script doit être exécuté en tant que root (avec sudo)."
  exit 1
fi

# Trouve le chemin racine du projet (un niveau au-dessus du dossier 'scripts')
SCRIPT_DIR=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

PROFILE_SRC="$PROJECT_ROOT/apparmor/docker-honeypot-profile"
PROFILE_DEST="/etc/apparmor.d/docker-honeypot-profile"

echo "[1/2] Copie du profil AppArmor vers $PROFILE_DEST..."
cp "$PROFILE_SRC" "$PROFILE_DEST"

echo "[2/2] Chargement du profil AppArmor (en mode 'complain')..."
# -r = replace (remplacer), -C = complain (se plaindre, ne pas bloquer)
# Pour un mode production (bloquant), retirez le '-C'
apparmor_parser -r -C "$PROFILE_DEST"

echo "Succès ! Le profil AppArmor 'docker-honeypot-profile' est chargé."
echo "Vous pouvez maintenant lancer le script build_up.sh."
