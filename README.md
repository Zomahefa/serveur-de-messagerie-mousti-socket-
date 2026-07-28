# Messagerie Instantanée — Client-Serveur TCP/IP

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python)
![TCP/IP](https://img.shields.io/badge/Protocol-TCP%2FIP-005C84)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57)
![bcrypt](https://img.shields.io/badge/Security-bcrypt-4EA94B)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-FF6F00)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Application de messagerie instantanée temps réel** développée en Python — architecture client-serveur, communication TCP/IP, interface graphique Tkinter, base de données SQLite, chiffrement bcrypt, et journalisation complète.

> **⭐ Points clés :** multithreading, protocole textuel, transfert de fichiers, messagerie de groupe, profils utilisateur, administration, 176 000+ lignes de logs de tests.

---

## Table des matières

- [Architecture](#architecture)
- [Technologies](#technologies)
- [Fonctionnalités](#fonctionnalités)
- [Sécurité](#sécurité)
- [Journalisation et tests](#journalisation-et-tests)
- [Problème résolu : transfert de fichiers](#problème-résolu-transfert-de-fichiers)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Protocole réseau](#protocole-réseau)
- [Structure du projet](#structure-du-projet)
- [Améliorations futures](#améliorations-futures)

---

## Architecture

L'application suit une architecture **client-serveur classique** avec communication **TCP/IP** :

```
   Machine A (Client)            Serveur                 Machine B (Client)
   ┌─────────────────┐     ┌────────────────────┐     ┌─────────────────┐
   │   client.py     │────▶│    server.py       │◀────│   client.py     │
   │  Interface GUI  │TCP  │  Port 8888 (TCP)   │TCP  │  Interface GUI  │
   │   Tkinter       │◀────│  Multithreading    │────▶│   Tkinter       │
   └─────────────────┘     │  SQLite + Logs     │     └─────────────────┘
                           └────────────────────┘
```

### Choix techniques

| Décision | Choix | Justification |
|----------|-------|--------------|
| **Protocole** | TCP (SOCK_STREAM) | Livraison garantie, ordre préservé, connexion persistante — essentiel pour une messagerie |
| **Concurrence** | Multithreading (1 thread/client) | Isolation des connexions, pas de blocage entre clients |
| **Stockage fichiers** | Disque + référence BDD | Performance : les fichiers binaires ne sont pas en BDD, seulement 📁:nom:taille |
| **Transport fichiers** | Hexadécimal + sendall() | Conversion binaire→hex pour passage dans le protocole texte, sendall() pour intégrité |

### Pourquoi TCP plutôt qu'UDP ?

| Critère | TCP (notre choix) | UDP |
|---------|------------------|-----|
| Livraison | **Garantie** (acquittements) | Perte possible |
| Ordre | **Préservé** | Non garanti |
| Connexion | **Persistante** (suivi d'état) | Sans état |
| Bidirectionnel | **Full-duplex simultané** | Unidirectionnel |

> Dans une messagerie, la fiabilité prime sur la vitesse. Perdre un message ou le recevoir dans le désordre rendrait la conversation incohérente. TCP est le choix adapté.

---

## Technologies

| Technologie | Rôle |
|------------|------|
| **Python 3.8+** | Langage principal |
| **Socket TCP** | Communication réseau |
| **Threading** | Gestion des connexions simultanées |
| **Tkinter** | Interface graphique du client |
| **SQLite 3** | Base de données locale |
| **bcrypt** | Hachage des mots de passe |
| **Pillow (PIL)** | Traitement des images de profil |
| **Logging** | Journalisation côté serveur |

---

## Fonctionnalités

### Authentification et comptes
- Inscription avec login et mot de passe (hash bcrypt)
- Connexion sécurisée (vérification bcrypt)
- Migration automatique des anciens mots de passe vers bcrypt
- Profil complet : photo, bio, téléphone, email, adresse, éducation, travail
- Modification du profil en temps réel
- Changement de login et mot de passe

###  Messagerie privée
- Envoi et réception en temps réel
- Bulles de message (vert = moi, blanc = autre)
- Horodatage automatique
- Indicateur de lecture : ✔️ (lu) / 📩 (non lu)
- Suppression individuelle ou totale de ses messages
- Scroll automatique vers le bas
- Raccourci Entrée pour envoyer, Shift+Entrée pour nouvelle ligne

###  Messagerie de groupe
- Création de groupes avec nom personnalisé
- Ajout de membres avec notification
- Messages à tous les membres connectés
- Affichage du nom de l'expéditeur
- Retrait d'un membre (créateur seulement)
- Quitter un groupe / Supprimer un groupe (créateur)

###  Transfert de fichiers
- Envoi en privé et en groupe
- Fichiers convertis en hexadécimal pour transport TCP
- Stocké sur le serveur dans `received_files/`
- Cache local chez chaque client
- **Téléchargement automatique** si fichier absent du cache (`GET_FILE`)
- Ouverture avec l'application par défaut du système
- Utilisation du fonction `sendall()` qui garantit l'envoi complet des gros fichiers

### Indicateur de frappe (Typing)
- " X tape..." en temps réel
- Arrêt automatique après 2 secondes d'inactivité
- Version groupe : "Quelqu'un écrit..."

###  Profils utilisateur
- Consultation du profil des autres utilisateurs
- Photo de profil avec prévisualisation circulaire
- Upload depuis le navigateur de fichiers
- Statut en ligne / hors ligne visible

###  Administration
- Interface de gestion des utilisateurs (admin seulement)
- Suppression définitive d'un compte utilisateur
- Vérification du statut admin avant chaque action sensible

###  Interface utilisateur
- Fenêtre divisée en 3 panneaux redimensionnables
- Design sobre (inspiré WhatsApp)
- Rafraîchissement automatique toutes les 2 secondes
- Indicateur de connexion (vert/rouge)
- Gestion propre de la fermeture

---

## Sécurité

### Mots de passe (bcrypt)
Chaque mot de passe est hashé avec un **sel aléatoire** (bcrypt.gensalt()). Même si la base de données fuit, les mots de passe sont protégés contre les attaques par rainbow tables.

### Administration
- Seul l'utilisateur avec `is_admin = 1` peut supprimer des comptes
- Toute tentative non autorisée est loggée et bloquée

### Journalisation
- Toutes les actions sont horodatées avec l'adresse IP
- Niveaux : INFO (succès), WARNING (tentatives échouées), ERROR (erreurs)
- Traçabilité complète pour audit

---

## Journalisation et tests

> **176 949 lignes de logs** — preuve de tests intensifs avec multiples utilisateurs simultanés.

### Exemples de logs

```
2026-07-11 13:00:01,744 - INFO    - Serveur démarré sur 0.0.0.0:8888
2026-07-11 13:00:24,708 - WARNING - Tentative échouée depuis ('192.168.1.42', 59786)
2026-07-11 13:00:35,548 - INFO    - alice authentifié depuis ('192.168.1.42', 59786)
2026-07-11 13:02:08,090 - INFO    - ('192.168.1.42', 59786) - SEND bob Bonjour Bob !
2026-07-11 13:40:33,647 - WARNING - bob a tenté de supprimer le message 6 sans autorisation
2026-07-11 13:40:58,430 - INFO    - bob a supprimé le message 3
2026-07-11 16:42:16,545 - INFO    - alice a supprimé tous ses messages (5 messages)
```

Chaque entrée contient : **timestamp** | **niveau** | **action détaillée** → traçabilité complète.

## Installation

### Prérequis
- Python 3.8 ou supérieur
- `pip` (gestionnaire de paquets)

### Dépendances
```bash
pip install bcrypt Pillow
```

### Cloner
```bash
git clone https://github.com/Zomahefa/serveur-de-messagerie-mousti-socket-.git
cd serveur-de-messagerie-mousti-socket-
```

### Démarrer le serveur
```bash
python3 server.py
```
Le serveur écoute sur **toutes les interfaces** (0.0.0.0:8888).

### Lancer le(s) client(s)
```bash
python3 client.py
```
Renseigner l'adresse IP du serveur et le port (8888). Connectez-vous avec un compte existant ou créez-en un.

### Utilisateurs de test
| Login | Mot de passe | Admin |
|-------|-------------|-------|
| alice | 1234 | ✅ |
| bob | 5678 | ❌ |
| charlie | 91011 | ❌ |
| diana | password | ❌ |

---

## Structure du projet

```
serveur_messagerie/
├── server.py              # Serveur TCP multithread (958 lignes)
├── client.py              # Client graphique Tkinter (1884 lignes)
├── init_db.py             # Script d'initialisation de la BDD
├── requirements.txt       # Dépendances Python
├── messagerie.db          # Base de données SQLite
├── logs/
│   └── serveur.log        # Journal du serveur (176 949 lignes)
├── received_files/        # Fichiers transférés
├── README.md              # Documentation
└── guide-presentation-messagerie.pdf  # Guide de présentation
```

---

## Protocole réseau

Protocole **textuel** — chaque commande est terminée par `\n`.

| Commande | Description |
|----------|-------------|
| `REGISTER login password` | Créer un compte |
| `LOGIN login password` | Se connecter |
| `SEND user message` | Message privé |
| `ALLUSERS` | Lister tous les utilisateurs |
| `USERS` | Lister les connectés |
| `FILE dest nom hex_data` | Envoyer un fichier |
| `GET_FILE nom` | Télécharger un fichier |
| `CREATE_GROUP nom` | Créer un groupe |
| `ADD_TO_GROUP id user` | Ajouter un membre |
| `GROUP_SEND id message` | Message de groupe |
| `GROUP_FILE id nom hex` | Fichier dans un groupe |
| `DELETE_GROUP id` | Supprimer un groupe |
| `LEAVE_GROUP id` | Quitter un groupe |
| `GET_PROFILE user` | Consulter un profil |
| `UPDATE_PROFILE champ valeur` | Modifier son profil |
| `DELETE_USER user` | Supprimer un utilisateur (admin) |
| `DELETE id` / `DELETE ALL` | Supprimer un/ts les messages |
| `QUIT` | Se déconnecter |

---

## Améliorations futures

- [ ] Chiffrement TLS/SSL (données chiffrées sur le réseau)
- [ ] Chiffrement de bout en bout (messages illisibles même par le serveur)
- [ ] Rate limiting (blocage après N tentatives échouées)
- [ ] Interface web (WebSocket + React/Vue.js)
- [ ] Application mobile (Flutter/Kotlin)
- [ ] Stockage cloud des fichiers
- [ ] Nettoyage automatique des fichiers obsolètes
- [ ] Microservices (séparation chat, fichiers, auth)

---

## À propos

Projet développé dans le cadre d'un travail pratique sur l'architecture réseau et la programmation système en Python.

> Si ce projet vous est utile, n'hésitez pas à laisser une ⭐ sur le dépôt GitHub !
