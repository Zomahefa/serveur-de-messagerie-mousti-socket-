# Messagerie - Application de Chat Client-Serveur

Une application de messagerie instantanee complete en Python, fonctionnant en reseau TCP avec une interface graphique Tkinter. Elle permet des conversations privees, des discussions de groupe, le transfert de fichiers, la gestion de profils utilisateur et bien plus encore.

---

## Architecture

L'application suit une architecture client-serveur classique :

```
                     +-------------------+
                     |   Serveur TCP      |
                     |   (server.py)      |
                     |   Port 8888        |
                     +--------+----------+
                              |
              +---------------+---------------+
              |               |               |
         +----+----+    +----+----+    +----+----+
         | Client  |    | Client  |    | Client  |
         |   A     |    |   B     |    |   C     |
         +---------+    +---------+    +---------+
```

- **Serveur** : centralise les connexions, achemine les messages, gere la base de donnees SQLite et les groupes.
- **Client** : interface graphique Tkinter qui se connecte au serveur pour envoyer et recevoir des messages en temps reel.
- **Base de donnees** : SQLite locale (messagerie.db) contenant utilisateurs, messages prives, groupes, membres et messages de groupe.

### Flux de donnees

Chaque client maintient une connexion TCP persistante avec le serveur. Les messages sont echanges sous forme de texte delimite par des sauts de ligne. Le serveur utilise du multithreading (un thread par client) pour gerer les connexions simultanees.

---

## Technologies utilisees

| Technologie         | Utilisation                                          |
|---------------------|------------------------------------------------------|
| Python 3            | Langage principal                                    |
| Socket              | Communication reseau TCP                             |
| Threading           | Gestion des connexions simultanees                   |
| Tkinter             | Interface graphique du client                        |
| SQLite 3            | Base de donnees locale                               |
| bcrypt              | Hachage des mots de passe                            |
| Pillow (PIL)        | Traitement des images de profil                      |
| Logging             | Journalisation cote serveur                          |
| datetime            | Horodatage des messages                              |
| re                  | Analyse des protocoles texte                         |
| os / io / time      | Gestion des fichiers, timeouts, etc.                 |

---

## Fonctionnalites

### Authentification et comptes

- Inscription avec login et mot de passe
- Connexion avec verification via bcrypt
- Mise a jour automatique des mots de passe en clair vers bcrypt (compatibilite ascendante)
- Profil utilisateur avec photo, bio, telephone, email, adresse, education, travail
- Modification du profil en temps reel (champs individuels ou en masse)
- Changement de login et de mot de passe
- Suppression de compte (admin seulement)

### Messagerie privee

- Envoi et reception de messages individuels en temps reel
- Affichage des messages en bulles (vert pour soi, blanc pour les autres)
- Horodatage de chaque message
- Indicateur de lecture (lu / non lu)
- Suppression de ses propres messages
- Detection et filtrage des doublons cote client
- Scroll automatique vers le bas aux nouveaux messages
- Raccourci Entree pour envoyer, Shift+Entree pour nouvelle ligne

### Messagerie de groupe

- Creation de groupes avec nom personnalise
- Ajout de membres via une interface de recherche
- Affichage de la liste des membres d'un groupe
- Envoi de messages a tout le groupe
- Suppression de message dans un groupe
- Retrait d'un membre (proprietaire seulement)
- Quitter un groupe
- Suppression d'un groupe (proprietaire seulement)

### Transfert de fichiers

- Envoi de fichier a un utilisateur
- Envoi de fichier a un groupe
- Selection via boite de dialogue systeme
- Affichage dans la conversation avec nom et taille
- Telechargement et ouverture automatique avec l'application par defaut du systeme
- Sauvegarde dans le dossier `received_files/`

### Indicateur de frappe (Typing Indicator)

- Notification "X tape..." affichee en temps reel
- Arret automatique apres 2 secondes d'inactivite
- Prise en charge des discussions de groupe ("Quelqu'un ecrit...")

### Liste des utilisateurs

- Utilisateurs connectes affiches avec un indicateur vert
- Utilisateurs hors ligne listes separement
- Mise a jour automatique toutes les 2 secondes
- Conversation privee demarree par clic sur un nom

### Profil utilisateur

- Consultation du profil des autres utilisateurs
- Photo de profil avec previsualisation circulaire
- Upload de photo depuis le navigateur de fichiers
- Carte de visite avec toutes les informations personnelles
- Statut en ligne / hors ligne visible

### Administration

- Interface de gestion des utilisateurs (admin seulement)
- Suppression definitive d'un compte utilisateur

### Interface utilisateur

- Fenetre divisee en trois panneaux redimensionnables
- Design sobre avec couleurs distinctives (fond gris, bulles vertes)
- Barre de statut de connexion
- Rafraichissement manuel et automatique
- Gestion de la fermeture propre (envoi de QUIT)

---

## Installation et utilisation

### Prerequis

- Python 3.8 ou superieur installe sur la machine

### Cloner le projet

```bash
git clone <url-du-depot>
cd serveur_messagerie
```

### Installer les dependances

```bash
pip install bcrypt Pillow
```

### Initialiser la base de donnees (optionnel - fait automatiquement au premier demarrage)

```bash
python3 init_db.py
```

Cette commande cree la base avec 4 utilisateurs de test : alice (admin), bob, charlie, diana.

### Lancer le serveur

```bash
python3 server.py
```

Le serveur demarre sur le port 8888 et ecoute sur toutes les interfaces reseau.

### Lancer le client

Dans un autre terminal (ou une autre machine) :

```bash
python3 client.py
```

Renseigner l'adresse IP du serveur et le port (8888 par defaut), puis le login et le mot de passe.

### Lancer plusieurs clients simultanement

Pour tester la messagerie, ouvrez plusieurs terminaux et lancez `python3 client.py` dans chacun. Connectez-vous avec des utilisateurs differents pour echanger des messages.

---

## Installation par systeme d'exploitation

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-pip
pip install bcrypt Pillow
git clone <url-du-depot>
cd serveur_messagerie
python3 server.py    # terminal 1
python3 client.py    # terminal 2, 3, etc.
```

### Linux (Fedora)

```bash
sudo dnf install python3 python3-pip
pip install bcrypt Pillow
git clone <url-du-depot>
cd serveur_messagerie
python3 server.py
python3 client.py
```

### macOS

```bash
# Installer Homebrew si necessaire : /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python3
pip3 install bcrypt Pillow
git clone <url-du-depot>
cd serveur_messagerie
python3 server.py
python3 client.py
```

### Windows (PowerShell)

```powershell
# Installer Python depuis python.org (cocher "Add Python to PATH")
pip install bcrypt Pillow
git clone <url-du-depot>
cd serveur_messagerie
python server.py
python client.py
```

---

## Utilisateurs de test

| Login   | Mot de passe | Administrateur |
|---------|-------------|----------------|
| alice   | 1234        | Oui            |
| bob     | 5678        | Non            |
| charlie | 91011       | Non            |
| diana   | password    | Non            |

---

## Structure du projet

```
serveur_messagerie/
  server.py           - Serveur TCP multithread
  client.py           - Client graphique Tkinter
  init_db.py          - Script d'initialisation de la base
  requirements.txt    - Dependances Python
  messagerie.db       - Base de donnees SQLite
  logs/               - Journaux du serveur
  received_files/     - Fichiers telecharges
```

---

## Protocole reseau

Le protocole est base sur du texte brut termine par un saut de ligne (`\n`). Exemples de commandes :

| Commande                          | Description                        |
|-----------------------------------|------------------------------------|
| `REGISTER login password`         | Creer un compte                    |
| `LOGIN login password`            | Se connecter                       |
| `SEND user message`               | Envoyer un message prive           |
| `ALLUSERS`                        | Lister tous les utilisateurs       |
| `USERS`                           | Lister les utilisateurs connectes  |
| `CREATE_GROUP nom`                | Creer un groupe                    |
| `ADD_TO_GROUP id user`            | Ajouter un membre au groupe        |
| `GROUP_SEND id message`           | Envoyer un message de groupe       |
| `FILE dest nom hex_data`          | Envoyer un fichier                 |
| `GET_PROFILE user`                | Consulter un profil                |
| `UPDATE_PROFILE champ valeur`     | Modifier son profil                |
| `DELETE_GROUP id`                 | Supprimer un groupe                |
| `LEAVE_GROUP id`                  | Quitter un groupe                  |
| `DELETE_USER user`                | Supprimer un utilisateur (admin)   |
| `DELETE id`                       | Supprimer un message               |
| `QUIT`                            | Se deconnecter                     |

---

## A propos

Projet de messagerie instantanee developpe en Python dans le cadre d'un travail pratique. Architecture client-serveur avec interface graphique, chiffrement des mots de passe, gestion de groupes et transfert de fichiers.

Si ce projet vous a ete utile, n'hesitez pas a laisser une etoile sur le depot GitHub. Cela aide beaucoup et motive a continuer a l'ameliorer.
