````markdown
# Projet 1: Honeypot SSH avec Confinement & Monitoring ELK

[cite_start]Ce projet implémente un honeypot SSH en Python, conçu pour simuler un serveur SSH et enregistrer toutes les tentatives d'intrusion. [cite: 8] [cite_start]Les données collectées sont ensuite centralisées, parsées et visualisées en temps réel à l'aide de la pile ELK (Elasticsearch, Logstash, Kibana). [cite: 13, 14]

L'accent est mis sur la sécurité du honeypot lui-même grâce à des techniques de confinement avancées, notamment **AppArmor** et **Seccomp**, pour garantir que même si le honeypot était compromis, l'attaquant ne pourrait pas s'échapper vers le système hôte.

Ce projet est spécifiquement configuré pour fonctionner sur des machines à faibles ressources (4 Go de RAM).

## 🚀 Fonctionnalités

* [cite_start]**Honeypot SSH** : Un serveur SSH factice écrit en Python (avec `paramiko`) qui écoute sur le port `2223` et rejette toutes les connexions tout en enregistrant les identifiants. [cite: 8]
* [cite_start]**Journalisation JSON** : Toutes les tentatives (IP, port, login, mot de passe, commandes) sont enregistrées dans un fichier `ssh-honeypot.log` au format JSON. [cite: 13]
* **Monitoring ELK** : La pile ELK (version 6.8.13) est configurée pour une faible consommation de RAM :
    * **Logstash** : Surveille le fichier de log, le parse et y ajoute la géolocalisation des IP.
    * **Elasticsearch** : Stocke et indexe tous les logs.
    * [cite_start]**Kibana** : Fournit une interface web pour la visualisation, les dashboards et les cartes géographiques des attaques. [cite: 14]
* [cite_start]**Confinement AppArmor** : Un profil AppArmor personnalisé (`docker-honeypot-profile`) est appliqué au conteneur du honeypot pour lui interdire l'accès aux fichiers sensibles (comme `/etc` ou `/proc`) et l'exécution de commandes. [cite: 11]
* [cite_start]**Confinement Seccomp** : Le script Python applique lui-même un filtre `pyseccomp` pour bloquer les appels système dangereux, notamment `execve`, l'empêchant d'exécuter des programmes externes. [cite: 12]
* [cite_start]**Bonus : Détection de Brute-Force** : Le script détecte les attaques par force brute (seuil de 5 tentatives/minute par IP) et peut envoyer une alerte via webhook. [cite: 15]

## 🏗️ Architecture des Services et Ports

Ce projet utilise 4 services principaux orchestrés par `docker-compose.yml`.

| Service | Port (Hôte) | Description |
| :--- | :--- | :--- |
| `ssh-honeypot` | `2223` | **(Point d'attaque)** Le honeypot SSH visible sur le réseau. |
| `kibana` | `5601` | **(Interface Web)** L'interface de visualisation Kibana. |
| `elasticsearch` | `9200` | L'API de la base de données Elasticsearch. |
| `logstash` | - | (Port interne) Traite les logs et les envoie à Elasticsearch. |

## 🛠️ Prérequis

Avant de commencer, assurez-vous que votre système hôte (votre serveur "Lite Linux") dispose des éléments suivants :

1.  Docker
2.  Docker Compose
3.  Les utilitaires AppArmor

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose apparmor-utils
````

## 🚀 Instructions d'Installation et de Lancement

Suivez ces étapes depuis le terminal de votre serveur.

### Étape 1 : Charger le Profil AppArmor

C'est l'étape la plus importante. Elle doit être faite **avant** de lancer les conteneurs. Nous copions le profil de sécurité dans le système et le chargeons.

```bash
# 1. Copier le profil dans le répertoire système d'AppArmor
sudo cp /home/zaikos/Desktop/honeypot-elk/apparmor/docker-honeypot-profile /etc/apparmor.d/

# 2. Charger le profil en mode "complain" (alerte sans bloquer)
# (Note : Sur votre système, il est peut-être déjà passé en mode "enforce" (bloquant), ce qui est encore mieux)
sudo apparmor_parser -r -C /etc/apparmor.d/docker-honeypot-profile
```

### Étape 2 : Construire et Démarrer les Conteneurs

Cette commande va construire l'image de votre honeypot et démarrer les 4 services en arrière-plan.

```bash
# Assurez-vous d'être dans le dossier du projet
cd /home/zaikos/Desktop/honeypot-elk/

# Construire les images et démarrer les services
docker compose up --build -d
```

> **Note :** Le démarrage de la pile ELK (surtout Elasticsearch) peut prendre 2 à 3 minutes sur une machine avec peu de RAM.

### Étape 3 : Vérifier le Lancement

1.  **Vérifier les conteneurs :**

    ```bash
    docker compose ps
    ```

    Assurez-vous que les 4 services (`ssh-honeypot`, `elasticsearch`, `logstash`, `kibana`) sont bien en état `running` ou `Up`.

2.  **Tester le Honeypot :**
    Depuis une **autre machine** (votre PC Windows), simulez une attaque :

    ```bash
    ssh -p 2223 nimportequoi@192.168.100.100
    ```

    La connexion doit être refusée.

3.  **Vérifier les logs JSON (sur le serveur) :**

    ```bash
    tail -f /home/zaikos/Desktop/honeypot-elk/logs/ssh-honeypot.log
    ```

    Vous devriez voir une ligne JSON apparaître pour votre tentative de connexion.

### Étape 4 : Accéder à Kibana

1.  Ouvrez votre navigateur web et allez à l'adresse de votre serveur :
    **`http://192.168.100.100:5601`**

2.  **Configurer l'Index Pattern** (la première fois) :

      * Allez dans **Management** (icône ⚙️).
      * Cliquez sur **Index Patterns** (dans la section Kibana).
      * Cliquez sur **Create index pattern**.
      * Entrez `ssh-honeypot-*` comme nom et cliquez sur "Next step".
      * Choisissez `@timestamp` comme champ de temps.
      * Cliquez sur **Create index pattern**.

3.  Allez dans l'onglet **Discover** (icône 🧭) pour voir vos logs d'attaque en temps réel \!

## 🔒 Vérification de la Sécurité

Voici comment prouver que les confinements AppArmor et Seccomp sont actifs.

### 1\. Vérification AppArmor (Blocage de Fichiers)

Nous testons si le profil AppArmor bloque bien l'accès à `/etc/passwd` depuis l'intérieur du conteneur.

  * **Commande de Test :**
    ```bash
    docker compose exec ssh-honeypot cat /etc/passwd
    ```
  * **Résultat Attendu (Succès) :**
    ```
    cat: /etc/passwd: Permission denied
    ```
    Cette erreur `Permission denied` prouve que AppArmor a intercepté et bloqué la tentative de lecture.

### 2\. Vérification Seccomp (Blocage d'Exécution)

Nous vérifions que le script `honeypot.py` (avec le bloc de test) a bien bloqué sa propre tentative d'exécuter `ls` (`execve`).

  * **Commande de Vérification :**
    ```bash
    docker compose logs ssh-honeypot
    ```
  * **Résultat Attendu (Succès) :**
    Vous devez voir ces lignes dans les logs de démarrage :
    ```
    ssh-honeypot  | Application du filtre Seccomp...
    ssh-honeypot  | Filtre Seccomp chargé. 'execve' est maintenant bloqué pour ce processus.
    ssh-honeypot  |
    ssh-honeypot  | --- TEST SECCOMP (ATTENDU: ÉCHEC) ---
    ssh-honeypot  | Tentative d'exécution de 'ls' via os.execvp...
    ssh-honeypot  | TEST SECCOMP RÉUSSI: L'exécution a été bloquée avec succès !
    ssh-honeypot  | Erreur attrapée: [Errno 1] Operation not permitted
    ssh-honeypot  | --- FIN DU TEST SECCOMP ---
    ssh-honeypot  |
    ssh-honeypot  | Génération d'une nouvelle clé de serveur...
    ssh-honeypot  | Démarrage du honeypot SSH sur 0.0.0.0:22...
    ```
    Cette sortie confirme que `pyseccomp` est actif et a bloqué l'appel `execve`.

## 🧼 Étape Finale (Nettoyage)

Maintenant que le test Seccomp est vérifié, vous devriez **retirer le bloc de test** de votre fichier `honeypot.py` pour le rendre propre.

1.  **Modifiez `honeypot.py`** :

    ```bash
    nano /home/zaikos/Desktop/honeypot-elk/honeypot/honeypot.py
    ```

    Supprimez tout le "BLOC DE TEST" (les 14 lignes que nous avons ajoutées à l'intérieur de la fonction `apply_seccomp_filter`).

2.  **Reconstruisez et redémarrez** uniquement le honeypot :

    ```bash
    docker compose up --build -d ssh-honeypot
    ```

Votre projet est maintenant complet, sécurisé et opérationnel.

```
```
