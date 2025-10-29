# 🛡️ Honeypot-ELK : Plateforme de Détection d'Intrusion

Ce projet propose une plateforme de honeypots multi-protocole (SSH, HTTP, FTP) confinés via AppArmor et Seccomp. Toutes les tentatives d'intrusion sont capturées, centralisées et analysées en temps réel grâce à la pile ELK (Elasticsearch, Logstash, Kibana), permettant une corrélation fine des attaques sur plusieurs vecteurs.

> ⚠️ **Usage pédagogique et recherche uniquement.** Ne pas déployer en production sans contrôles et autorisations adéquats.

---

## 🚀 Versions du Projet

Ce dépôt contient deux versions. Il est fortement recommandé d’utiliser **v2-multi-honeypot**.

### ➡️ v2-multi-honeypot (Recommandé)

Plateforme modulaire simulant 3 services pour capturer une chaîne d’attaque complète :

| Service       | Port Hôte | Description                      |
| ------------- | --------- | -------------------------------- |
| SSH Honeypot  | 2223      | Basé sur Paramiko, imite OpenSSH |
| HTTP Honeypot | 8080      | Basé sur Flask, imite Apache     |
| FTP Honeypot  | 2121      | Basé sur pyftpdlib, imite MS FTP |

**Objectif :** Permettre l’analyse de corrélation (ex : un scan Nmap frappant les 3 ports simultanément).

### ➡️ v1-ssh-only (Legacy)

Version originale, conservée à des fins d’archive :

| Service      | Port Hôte | Description                             |
| ------------ | --------- | --------------------------------------- |
| SSH Honeypot | 2223      | Analyse brute-force sur un seul service |

---

## 🔥 L’analyse SOC en action (V2)

La V2 est conçue comme un outil d’analyste SOC pour comprendre les méthodologies d’attaque.

### Exemple de corrélation :

- Lancez un scan Nmap :  
  `nmap -p 2121,2223,8080 -sV [IP_SERVEUR]`
- Dans Kibana :
  - Filtrez par IP attaquante : `client_ip: "192.168.100.200"`
  - Observez les logs HTTP, SSH et FTP à la même seconde
  - Identifiez l’outil : absence de User-Agent dans le log HTTP → trafic automatisé (Nmap)

---

## 🛠️ Installation (V2)

```bash
git clone https://github.com/ZaikOSS/honeypot-elk.git
cd honeypot-elk/v2-multi-honeypot

# Créer le dossier des logs
mkdir -p logs && touch logs/.gitkeep

# Rendre les scripts exécutables
chmod +x ./scripts/*.sh

# Charger le profil AppArmor (mode complain)
sudo ./scripts/load_apparmor.sh
```

### ⚠️ Problèmes de Permissions ?

- **AppArmor :** Vérifiez que le profil `docker-honeypot-platform-profile` est chargé  
  `sudo apparmor_status`
- **Seccomp :**
  - Dans `docker-compose.yml` : la ligne `seccomp` doit être commentée
  - Dans `honeypot/main.py` : `apply_seccomp_filter()` doit être active

### Lancer les services :

```bash
./scripts/build_up.sh
# ou manuellement :
docker compose up --build -d
```

### Vérifier le statut :

```bash
docker compose ps
docker compose logs -f honeypot-platform
```

---

## 🔧 Configuration des Ports

| Service       | Port Hôte | Port Conteneur | Index Kibana     |
| ------------- | --------- | -------------- | ---------------- |
| SSH Honeypot  | 2223      | 22             | honeypot-ssh-\*  |
| HTTP Honeypot | 8080      | 80             | honeypot-http-\* |
| FTP Honeypot  | 2121      | 21             | honeypot-ftp-\*  |
| Kibana        | 5601      | 5601           | N/A              |
| Elasticsearch | 9200      | 9200           | N/A              |

---

## 📊 Visualisation Kibana

- Accédez à : `http://[VOTRE_IP]:5601`
- Allez dans : **Management > Index Patterns**
- Créez un pattern global :

```text
Nom du pattern : honeypot-*
Champ de temps : @timestamp
```

---

## 🧰 Dépendances Python (V2)

Fichier : `v2-multi-honeypot/honeypot/requirements.txt`

```
paramiko
requests
pyseccomp
Flask
pyftpdlib
```

---

## 🧩 Contributions

Les contributions sont les bienvenues via **issues** ou **pull requests**.

Avant de proposer une PR :

- Documenter la fonctionnalité ou le correctif
- Ne pas inclure de données sensibles
- Expliquer les impacts des règles AppArmor/Seccomp ajoutées

---

## ⚖️ Licence

Ce projet est sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## ✍️ À propos

**Auteur :** Zakaria Ouadifi (Zaikos)  
**Projet :** Honeypot-ELK — Plateforme de détection et d’analyse multi-protocole.

---

Souhaites-tu que je t’aide à rédiger le fichier [LICENSE](LICENSE), un exemple de dashboard Kibana, ou un guide pour l’analyse des logs ?
