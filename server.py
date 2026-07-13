import socket
import threading
import sqlite3
import os
import bcrypt
from datetime import datetime
import logging

# Configuration
HOST = '0.0.0.0'
PORT = 8888
DB_NAME = "messagerie.db"
LOG_FILE = "logs/serveur.log"

# Configurer les logs
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.running = True
        self.connected_users = {}  # {user_id: client_socket}
        self.init_db_tables()
    
    def init_db_tables(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""\n        CREATE TABLE IF NOT EXISTS groups (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            name TEXT NOT NULL,\n            creator_id INTEGER NOT NULL,\n            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n        )\n        """)
        cursor.execute("""\n        CREATE TABLE IF NOT EXISTS group_members (\n            group_id INTEGER NOT NULL,\n            user_id INTEGER NOT NULL,\n            PRIMARY KEY (group_id, user_id)\n        )\n        """)
        cursor.execute("""\n        CREATE TABLE IF NOT EXISTS group_messages (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            group_id INTEGER NOT NULL,\n            sender_id INTEGER NOT NULL,\n            content TEXT NOT NULL,\n            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n        )\n        """)
        conn.commit()
        conn.close()
        
    def start(self):
        """Démarre le serveur"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        print(f"🚀 Serveur démarré sur {self.host}:{self.port}")
        print("📡 En attente de connexions...")
        print("Appuyez sur Ctrl+C pour arrêter\n")
        logging.info(f"Serveur démarré sur {self.host}:{self.port}")
        
        try:
            while self.running:
                client_socket, address = self.server_socket.accept()
                print(f"🔗 Nouvelle connexion de {address}")
                logging.info(f"Nouvelle connexion de {address}")
                
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("\n⚠️ Arrêt du serveur demandé...")
            self.running = False
            logging.info("Arrêt du serveur demandé")
        finally:
            self.server_socket.close()
            print("✅ Serveur arrêté")
            logging.info("Serveur arrêté")
    
    def get_db_connection(self):
        """Retourne une connexion à la base SQLite"""
        return sqlite3.connect(DB_NAME)
    
    def authenticate_user(self, login, password):
        """Vérifie les identifiants avec bcrypt (fallback plaintext)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, login, password FROM users WHERE login = ?",
            (login,)
        )
        row = cursor.fetchone()
        
        if row:
            user_id, username, stored_pw = row
            try:
                if bcrypt.checkpw(password.encode(), stored_pw.encode()):
                    conn.close()
                    return (user_id, username)
            except (ValueError, AttributeError):
                pass
            if stored_pw == password:
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
                conn.commit()
                conn.close()
                return (user_id, username)
        
        conn.close()
        return None
    
    def get_user_by_id(self, user_id):
        """Récupère le login d'un utilisateur par son ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT login FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def get_user_by_login(self, login):
        """Récupère un utilisateur par son login"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, login FROM users WHERE login = ?", (login,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_unread_count(self, user_id):
        """Récupère le nombre de messages non lus"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0",
            (user_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def mark_messages_as_read(self, user_id):
        """Marque tous les messages d'un utilisateur comme lus"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE messages SET is_read = 1 WHERE receiver_id = ? AND is_read = 0",
            (user_id,)
        )
        conn.commit()
        conn.close()
    
    def delete_message(self, message_id, user_id):
        """Supprime un message si l'utilisateur en est l'expéditeur. Retourne le login du destinataire si succès."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer l'autre partie avant suppression
        cursor.execute(
            """SELECT receiver.login FROM messages 
               JOIN users as receiver ON messages.receiver_id = receiver.id
               WHERE messages.id = ? AND messages.sender_id = ?""",
            (message_id, user_id)
        )
        row = cursor.fetchone()
        other = row[0] if row else None
        
        cursor.execute(
            "DELETE FROM messages WHERE id = ? AND sender_id = ?",
            (message_id, user_id)
        )
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected_rows > 0, other

    def delete_all_messages(self, user_id):
        """Supprime tous les messages d'un utilisateur (uniquement ceux qu'il a envoyés)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM messages WHERE sender_id = ?",
            (user_id,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def send_message(self, sender_id, receiver_login, content):
        """Envoie un message à un utilisateur"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE login = ?", (receiver_login,))
        receiver = cursor.fetchone()
        
        if receiver:
            receiver_id = receiver[0]
            cursor.execute(
                "INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
                (sender_id, receiver_id, content)
            )
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    
    def create_group(self, name, creator_id):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO groups (name, creator_id) VALUES (?, ?)", (name, creator_id))
        group_id = cursor.lastrowid
        cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (group_id, creator_id))
        conn.commit()
        conn.close()
        return group_id
    
    def add_to_group(self, group_id, member_login):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE login = ?", (member_login,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return None
        try:
            cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (group_id, user[0]))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False
    
    def send_group_message(self, group_id, sender_id, content):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, sender_id))
        if not cursor.fetchone():
            conn.close()
            return None
        cursor.execute("INSERT INTO group_messages (group_id, sender_id, content) VALUES (?, ?, ?)", (group_id, sender_id, content))
        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return msg_id
    
    def get_user_groups(self, user_id):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""\n            SELECT g.id, g.name\n            FROM groups g\n            JOIN group_members gm ON g.id = gm.group_id\n            WHERE gm.user_id = ?\n        """, (user_id,))
        groups = cursor.fetchall()
        conn.close()
        return groups
    
    def get_group_members(self, group_id):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""\n            SELECT u.login\n            FROM users u\n            JOIN group_members gm ON u.id = gm.user_id\n            WHERE gm.group_id = ?\n        """, (group_id,))
        members = [row[0] for row in cursor.fetchall()]
        conn.close()
        return members
    
    def get_group_name(self, group_id):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def delete_group_message(self, msg_id, user_id):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT group_id FROM group_messages WHERE id = ? AND sender_id = ?", (msg_id, user_id))
        row = cursor.fetchone()
        gid = row[0] if row else None
        if gid:
            cursor.execute("DELETE FROM group_messages WHERE id = ? AND sender_id = ?", (msg_id, user_id))
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            return affected > 0, gid
        conn.close()
        return False, None
    
    def get_messages(self, user_id):
        """Récupère les messages d'un utilisateur avec leurs IDs"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        username = self.get_user_by_id(user_id)
        
        cursor.execute("""\n            SELECT \n                sender.login as expediteur,\n                receiver.login as destinataire,\n                messages.content,\n                messages.sent_at,\n                messages.is_read,\n                messages.id\n            FROM messages\n            JOIN users as sender ON messages.sender_id = sender.id\n            JOIN users as receiver ON messages.receiver_id = receiver.id\n            WHERE receiver_id = ? OR sender_id = ?\n            ORDER BY messages.sent_at DESC\n            LIMIT 50\n        """, (user_id, user_id))
        
        messages = cursor.fetchall()
        
        result = ""
        if messages:
            result = f"\n📨 Messages pour {username} (derniers 50) :\n"
            result += "=" * 70 + "\n"
            for exp, dest, content, date, is_read, msg_id in messages:
                lu = "✔️" if is_read else "📩"
                conv_key = ':'.join(sorted([exp, dest]))
                if exp == username:
                    result += f"[ENVOYÉ] À {dest} : {content}\n"
                    result += f"   📅 {date} | ID: {msg_id} | {lu} | {conv_key}\n"
                else:
                    result += f"[REÇU]  De {exp} : {content}\n"
                    result += f"   📅 {date} | ID: {msg_id} | {lu} | {conv_key}\n"
                result += "-" * 70 + "\n"
        
        # Ajouter les messages de groupe
        cursor.execute("""\n            SELECT gm.id, g.name, g.id, u.login, gm.content, gm.sent_at\n            FROM group_messages gm\n            JOIN groups g ON gm.group_id = g.id\n            JOIN users u ON gm.sender_id = u.id\n            WHERE gm.group_id IN (SELECT group_id FROM group_members WHERE user_id = ?)\n            ORDER BY gm.sent_at DESC\n            LIMIT 50\n        """, (user_id,))
        group_msgs = cursor.fetchall()
        
        if group_msgs:
            for msg_id, gname, gid, sender, content, date in group_msgs:
                result += f'[GROUPE] Dans "{gname}" (ID:{gid}) : {sender}: {content}\n'
                result += f"   📅 {date} | ID: {msg_id} | ✔️\n"
                result += "-" * 70 + "\n"
        
        conn.close()
        
        if not messages and not group_msgs:
            result = "📭 Aucun message\n"
        
        if messages or group_msgs:
            result += "=" * 70 + "\n"
            result += "💡 Pour supprimer un message: DELETE <ID>\n"
        result += "-- END LIST --\n"
        
        return result
    
    def get_connected_users(self):
        """Retourne la liste des utilisateurs connectés"""
        if not self.connected_users:
            return "👤 Aucun utilisateur connecté\n"
        
        result = "👥 Utilisateurs connectés :\n"
        for user_id in self.connected_users:
            username = self.get_user_by_id(user_id)
            if username:
                result += f"- {username}\n"
        return result
    
    def get_all_users(self):
        """Retourne tous les utilisateurs de la base avec leur statut"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT login FROM users ORDER BY login")
        all_users = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        connected_logins = set()
        for uid in self.connected_users:
            name = self.get_user_by_id(uid)
            if name:
                connected_logins.add(name)
        
        result = "📋 UTILISATEURS :\n"
        for user in all_users:
            if user in connected_logins:
                result += f"🟢 {user}\n"
            else:
                result += f"🔴 {user}\n"
        return result
    
    def handle_client(self, client_socket, address):
        """Gère un client connecté"""
        authenticated = False
        user_id = None
        username = None
        
        try:
            welcome = "Bienvenue sur le serveur de messagerie !\n"
            welcome += "Veuillez vous authentifier : LOGIN <login> <mot_de_passe>\n"
            client_socket.send(welcome.encode())
            
            buffer = ""
            while True:
                chunk = client_socket.recv(1024).decode()
                if not chunk:
                    break
                buffer += chunk
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    
                    print(f"[{address}] {line}")
                    logging.info(f"{address} - {line}")
                    
                    if not authenticated:
                        if line.startswith("REGISTER "):
                            parts = line.split(" ", 2)
                            if len(parts) == 3:
                                _, login, password = parts
                                if len(login) < 2 or len(password) < 2:
                                    client_socket.send("❌ Login et mot de passe doivent faire au moins 2 caractères\n".encode())
                                else:
                                    conn = self.get_db_connection()
                                    cursor = conn.cursor()
                                    try:
                                        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                                        cursor.execute("INSERT INTO users (login, password) VALUES (?, ?)", (login, hashed))
                                        conn.commit()
                                        conn.close()
                                        client_socket.send(f"✅ Compte '{login}' créé avec succès ! Connectez-vous avec LOGIN\n".encode())
                                    except sqlite3.IntegrityError:
                                        conn.close()
                                        client_socket.send("❌ Ce login est déjà pris\n".encode())
                            else:
                                client_socket.send("❌ Format: REGISTER <login> <password>\n".encode())
                        
                        elif line.startswith("LOGIN "):
                            parts = line.split(" ", 2)
                            if len(parts) == 3:
                                _, login, password = parts
                                user = self.authenticate_user(login, password)
                                if user:
                                    authenticated = True
                                    user_id = user[0]
                                    username = user[1]
                                    self.connected_users[user_id] = client_socket
                                    
                                    unread = self.get_unread_count(user_id)
                                    
                                    response = f"✅ Authentifié avec succès ! Bienvenue {username} !\n"
                                    response += f"📩 Vous avez {unread} message(s) non lu(s)\n"
                                    response += "Commandes disponibles :\n"
                                    response += "- SEND <destinataire> <message>\n"
                                    response += "- LIST\n"
                                    response += "- USERS\n"
                                    response += "- ALLUSERS\n"
                                    response += "- DELETE <id_message> (supprimer un message)\n"
                                    response += "- DELETE ALL (supprimer tous vos messages)\n"
                                    response += "- CREATE_GROUP <nom>\n"
                                    response += "- ADD_TO_GROUP <id> <utilisateur>\n"
                                    response += "- GROUP_SEND <id> <message>\n"
                                    response += "- GROUP_FILE <id> <nom> <hex>\n"
                                    response += "- LIST_GROUPS\n"
                                    response += "- GROUP_MEMBERS <id>\n"
                                    response += "- QUIT\n"
                                    client_socket.send(response.encode())
                                    print(f"✅ {username} authentifié depuis {address}")
                                    logging.info(f"{username} authentifié depuis {address}")
                                else:
                                    response = "❌ Identifiants incorrects. Réessayez : LOGIN <login> <mot_de_passe>\n"
                                    client_socket.send(response.encode())
                                    logging.warning(f"Tentative échouée depuis {address}")
                            else:
                                response = "❌ Format incorrect. Utilisez : LOGIN <login> <mot_de_passe>\n"
                                client_socket.send(response.encode())
                        else:
                            response = "❌ Veuillez vous authentifier d'abord : LOGIN <login> <mot_de_passe>\n"
                            client_socket.send(response.encode())
                    
                    else:
                        if line.startswith("SEND "):
                            parts = line.split(" ", 2)
                            if len(parts) == 3:
                                _, receiver_login, message = parts
                                success = self.send_message(user_id, receiver_login, message)
                                if success:
                                    response = f"✅ Message envoyé à {receiver_login}\n"
                                    receiver = self.get_user_by_login(receiver_login)
                                    if receiver and receiver[0] in self.connected_users:
                                        try:
                                            self.connected_users[receiver[0]].send(f"📩 Nouveau message de {username}\n".encode())
                                        except:
                                            pass
                                else:
                                    response = f"❌ Utilisateur {receiver_login} inexistant\n"
                                client_socket.send(response.encode())
                            else:
                                response = "❌ Format incorrect. Utilisez : SEND <destinataire> <message>\n"
                                client_socket.send(response.encode())
                        
                        elif line == "LIST":
                            self.mark_messages_as_read(user_id)
                            messages = self.get_messages(user_id)
                            client_socket.send(messages.encode())
                        
                        elif line == "USERS":
                            users = self.get_connected_users()
                            client_socket.send(users.encode())
                        
                        elif line == "ALLUSERS":
                            users = self.get_all_users()
                            client_socket.send(users.encode())
                        
                        elif line.startswith("DELETE "):
                            parts = line.split(" ", 1)
                            if len(parts) == 2:
                                _, param = parts
                                if param == "ALL":
                                    deleted_count = self.delete_all_messages(user_id)
                                    if deleted_count > 0:
                                        response = f"🗑️ {deleted_count} message(s) supprimé(s)\n"
                                    else:
                                        response = "📭 Aucun message à supprimer\n"
                                    client_socket.send(response.encode())
                                    logging.info(f"{username} a supprimé tous ses messages ({deleted_count} messages)")
                                else:
                                    try:
                                        msg_id = int(param)
                                        success, other_login = self.delete_message(msg_id, user_id)
                                        if success:
                                            response = f"🗑️ Message {msg_id} supprimé avec succès\n"
                                            logging.info(f"{username} a supprimé le message {msg_id}")
                                        else:
                                            response = "❌ Message introuvable ou vous n'êtes pas autorisé à le supprimer\n"
                                            logging.warning(f"{username} a tenté de supprimer le message {msg_id} sans autorisation")
                                    except ValueError:
                                        response = "❌ ID invalide. Utilisez : DELETE <id> ou DELETE ALL\n"
                                client_socket.send(response.encode())
                            else:
                                response = "❌ Format incorrect. Utilisez : DELETE <id> ou DELETE ALL\n"
                                client_socket.send(response.encode())
                        
                        elif line.startswith("TYPING "):
                            _, target = line.split(" ", 1)
                            for uid, sock in self.connected_users.items():
                                if self.get_user_by_id(uid) == target:
                                    try:
                                        sock.send(f"📝 {username} tape...\n".encode())
                                    except:
                                        pass
                                    break
                        
                        elif line.startswith("STOP_TYPING "):
                            _, target = line.split(" ", 1)
                            for uid, sock in self.connected_users.items():
                                if self.get_user_by_id(uid) == target:
                                    try:
                                        sock.send("CLEAR_TYPING\n".encode())
                                    except:
                                        pass
                                    break
                        
                        elif line.startswith("FILE "):
                            parts = line.split(" ", 3)
                            if len(parts) == 4:
                                _, target, filename, hex_data = parts
                                os.makedirs("received_files", exist_ok=True)
                                filepath = f"received_files/{filename}"
                                try:
                                    file_bytes = bytes.fromhex(hex_data)
                                    with open(filepath, 'wb') as f:
                                        f.write(file_bytes)
                                    size = len(file_bytes)
                                    self.send_message(user_id, target, f"📁:{filename}:{size}")
                                    for uid, sock in self.connected_users.items():
                                        if self.get_user_by_id(uid) == target:
                                            try:
                                                sock.send(f"📁 Fichier recu de {username}: {filename}:{size}:{hex_data}\n".encode())
                                            except:
                                                pass
                                            break
                                    client_socket.send(f"✅ Fichier {filename} envoyé à {target}\n".encode())
                                except:
                                    client_socket.send("❌ Erreur lors du transfert du fichier\n".encode())
                            else:
                                client_socket.send("❌ Format: FILE <dest> <nom> <hex_data>\n".encode())
                        
                        elif line.startswith("GET_FILE "):
                            _, filename = line.split(" ", 1)
                            filename = filename.strip()
                            filepath = f"received_files/{filename}"
                            if os.path.exists(filepath):
                                try:
                                    with open(filepath, 'rb') as f:
                                        hex_data = f.read().hex()
                                    client_socket.send(f"FILE_DATA {filename} {hex_data}\n".encode())
                                except:
                                    client_socket.send("❌ Erreur de lecture du fichier\n".encode())
                            else:
                                client_socket.send("❌ Fichier introuvable\n".encode())
                        
                        elif line.startswith("CREATE_GROUP "):
                            _, group_name = line.split(" ", 1)
                            group_name = group_name.strip()
                            if group_name:
                                group_id = self.create_group(group_name, user_id)
                                client_socket.send(f"✅ Groupe '{group_name}' créé (ID: {group_id})\n".encode())
                            else:
                                client_socket.send("❌ Nom de groupe invalide\n".encode())
                        
                        elif line.startswith("ADD_TO_GROUP "):
                            parts = line.split(" ", 2)
                            if len(parts) == 3:
                                _, gid_str, member_login = parts
                                try:
                                    gid = int(gid_str)
                                    result = self.add_to_group(gid, member_login)
                                    if result is None:
                                        client_socket.send(f"❌ Utilisateur {member_login} inexistant\n".encode())
                                    elif result:
                                        client_socket.send(f"✅ {member_login} ajouté au groupe\n".encode())
                                        gname = self.get_group_name(gid)
                                        m = self.get_user_by_login(member_login)
                                        if m and m[0] in self.connected_users:
                                            name = gname or f"groupe (ID: {gid})"
                                            self.connected_users[m[0]].send(f"📩 Vous avez été ajouté dans {name}\n".encode())
                                    else:
                                        client_socket.send(f"❌ {member_login} déjà dans le groupe\n".encode())
                                except ValueError:
                                    client_socket.send("❌ ID de groupe invalide\n".encode())
                            else:
                                client_socket.send("❌ Format: ADD_TO_GROUP <id> <user>\n".encode())
                        
                        elif line.startswith("GROUP_SEND "):
                            parts = line.split(" ", 2)
                            if len(parts) == 3:
                                _, gid_str, message = parts
                                try:
                                    gid = int(gid_str)
                                    msg_id = self.send_group_message(gid, user_id, message)
                                    if msg_id is None:
                                        client_socket.send("❌ Vous n'êtes pas membre de ce groupe\n".encode())
                                    else:
                                        gname = self.get_group_name(gid)
                                        for m_login in self.get_group_members(gid):
                                            m = self.get_user_by_login(m_login)
                                            if m and m[0] in self.connected_users and m[0] != user_id:
                                                try:
                                                    self.connected_users[m[0]].send(f"📩 [{gname}] {username}: {message}\n".encode())
                                                except:
                                                    pass
                                        # Stocker aussi les messages de fichiers dans le groupe
                                        client_socket.send(f"✅ Message envoyé au groupe '{gname}'\n".encode())
                                except ValueError:
                                    client_socket.send("❌ ID de groupe invalide\n".encode())
                            else:
                                client_socket.send("❌ Format: GROUP_SEND <id> <message>\n".encode())
                        
                        elif line.startswith("GROUP_TYPING "):
                            _, gtid_str = line.split(" ", 1)
                            try:
                                gtid = int(gtid_str.strip())
                                gname = self.get_group_name(gtid)
                                if gname:
                                    for mt_login in self.get_group_members(gtid):
                                        mt = self.get_user_by_login(mt_login)
                                        if mt and mt[0] in self.connected_users and mt[0] != user_id:
                                            try:
                                                self.connected_users[mt[0]].send(f"📝 [{gname}] quelqu'un écrit...\n".encode())
                                            except:
                                                pass
                            except ValueError:
                                pass
                        
                        elif line.startswith("GROUP_STOP_TYPING "):
                            _, gstid_str = line.split(" ", 1)
                            try:
                                gstid = int(gstid_str.strip())
                                gname = self.get_group_name(gstid)
                                if gname:
                                    for mt_login in self.get_group_members(gstid):
                                        mt = self.get_user_by_login(mt_login)
                                        if mt and mt[0] in self.connected_users and mt[0] != user_id:
                                            try:
                                                self.connected_users[mt[0]].send(f"CLEAR_TYPING_GROUP [{gname}]\n".encode())
                                            except:
                                                pass
                            except ValueError:
                                pass
                        
                        elif line.startswith("GROUP_FILE "):
                            parts = line.split(" ", 3)
                            if len(parts) == 4:
                                _, gid_str, filename, hex_data = parts
                                try:
                                    gid = int(gid_str)
                                    file_bytes = bytes.fromhex(hex_data)
                                    os.makedirs("received_files", exist_ok=True)
                                    with open(f"received_files/{filename}", 'wb') as f:
                                        f.write(file_bytes)
                                    size = len(file_bytes)
                                    self.send_group_message(gid, user_id, f"📁:{filename}:{size}")
                                    gname = self.get_group_name(gid)
                                    for m_login in self.get_group_members(gid):
                                        m = self.get_user_by_login(m_login)
                                        if m and m[0] in self.connected_users and m[0] != user_id:
                                            try:
                                                self.connected_users[m[0]].send(
                                                    f"📁 Fichier recu de {username} (groupe {gname}): {filename}:{size}:{hex_data}\n".encode()
                                                )
                                            except:
                                                pass
                                    client_socket.send(f"✅ Fichier {filename} envoyé au groupe '{gname}'\n".encode())
                                except:
                                    client_socket.send("❌ Erreur fichier groupe\n".encode())
                            else:
                                client_socket.send("❌ Format: GROUP_FILE <id> <nom> <hex>\n".encode())
                        
                        elif line == "LIST_GROUPS":
                            groups = self.get_user_groups(user_id)
                            if groups:
                                result = "📋 VOS GROUPES :\n"
                                for gid, gname in groups:
                                    creator_id = self.get_group_creator(gid)
                                    mark = " *" if creator_id == user_id else ""
                                    result += f"  {gid}: {gname}{mark}\n"
                                client_socket.send(result.encode())
                            else:
                                client_socket.send("📭 Vous n'êtes dans aucun groupe\n".encode())
                        
                        elif line.startswith("DELETE_GROUP "):
                            _, dgid_str = line.split(" ", 1)
                            try:
                                dgid = int(dgid_str.strip())
                                if self.delete_group(dgid, user_id):
                                    client_socket.send("✅ Groupe supprimé\n".encode())
                                else:
                                    client_socket.send("❌ Seul le créateur peut supprimer le groupe\n".encode())
                            except ValueError:
                                client_socket.send("❌ ID de groupe invalide\n".encode())
                        
                        elif line.startswith("GROUP_MEMBERS "):
                            _, gid_str = line.split(" ", 1)
                            try:
                                gid = int(gid_str.strip())
                                members = self.get_group_members(gid)
                                gname = self.get_group_name(gid)
                                if gname:
                                    result = f"👥 Membres du groupe '{gname}':\n"
                                    for m in members:
                                        result += f"  - {m}\n"
                                    result += "-- END MEMBERS --\n"
                                    client_socket.send(result.encode())
                                else:
                                    client_socket.send("❌ Groupe introuvable\n".encode())
                            except ValueError:
                                client_socket.send("❌ ID de groupe invalide\n".encode())
                        
                        elif line.startswith("GROUP_DELETE "):
                            _, gmid_str = line.split(" ", 1)
                            try:
                                gmid = int(gmid_str.strip())
                                success, gid = self.delete_group_message(gmid, user_id)
                                if success:
                                    msg = f"🗑️ Message groupe {gmid} supprimé\n"
                                    client_socket.send(msg.encode())
                                else:
                                    client_socket.send("❌ Message introuvable ou pas l'expéditeur\n".encode())
                            except ValueError:
                                client_socket.send("❌ ID invalide\n".encode())
                        
                        elif line.startswith("LEAVE_GROUP "):
                            _, lgid_str = line.split(" ", 1)
                            try:
                                lgid = int(lgid_str.strip())
                                gname = self.get_group_name(lgid)
                                if not gname:
                                    client_socket.send("❌ Groupe introuvable\n".encode())
                                    continue
                                conn = self.get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM group_members WHERE group_id = ? AND user_id = ?", (lgid, user_id))
                                affected = cursor.rowcount
                                conn.commit()
                                conn.close()
                                if affected > 0:
                                    client_socket.send(f"✅ Vous avez quitté le groupe '{gname}'\n".encode())
                                    for m_login in self.get_group_members(lgid):
                                        m = self.get_user_by_login(m_login)
                                        if m and m[0] in self.connected_users:
                                            try:
                                                self.connected_users[m[0]].send(f"📩 {username} a quitté le groupe '{gname}'\n".encode())
                                            except:
                                                pass
                                else:
                                    client_socket.send("❌ Vous n'êtes pas membre de ce groupe\n".encode())
                            except ValueError:
                                client_socket.send("❌ ID de groupe invalide\n".encode())
                        
                        elif line.startswith("REMOVE_FROM_GROUP "):
                            parts = line.split(" ", 2)
                            if len(parts) == 3:
                                _, rgid_str, target_user = parts
                                try:
                                    rgid = int(rgid_str.strip())
                                    conn = self.get_db_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT creator_id FROM groups WHERE id = ?", (rgid,))
                                    row = cursor.fetchone()
                                    if row and row[0] == user_id:
                                        cursor.execute("""DELETE FROM group_members 
                                            WHERE group_id = ? AND user_id = (SELECT id FROM users WHERE login = ?)""",
                                            (rgid, target_user))
                                        affected = cursor.rowcount
                                        conn.commit()
                                        conn.close()
                                        if affected > 0:
                                            client_socket.send(f"✅ {target_user} retiré du groupe\n".encode())
                                            gname = self.get_group_name(rgid)
                                            for m_login in self.get_group_members(rgid):
                                                m = self.get_user_by_login(m_login)
                                                if m and m[0] in self.connected_users:
                                                    try:
                                                        self.connected_users[m[0]].send(
                                                            f"📩 {target_user} a été retiré du groupe '{gname}' par {username}\n".encode())
                                                    except:
                                                        pass
                                            for uid, sock in self.connected_users.items():
                                                if self.get_user_by_id(uid) == target_user:
                                                    try:
                                                        sock.send(f"📩 Vous avez été retiré du groupe '{gname}' par {username}\n".encode())
                                                    except:
                                                        pass
                                                    break
                                        else:
                                            client_socket.send("❌ Utilisateur introuvable dans ce groupe\n".encode())
                                    else:
                                        conn.close()
                                        client_socket.send("❌ Seul le créateur peut retirer des membres\n".encode())
                                except ValueError:
                                    client_socket.send("❌ ID de groupe invalide\n".encode())
                            else:
                                client_socket.send("❌ Format: REMOVE_FROM_GROUP <id> <utilisateur>\n".encode())
                        
                        elif line.startswith("GET_PROFILE "):
                            _, target_login = line.split(" ", 1)
                            conn = self.get_db_connection()
                            cursor = conn.cursor()
                            try:
                                cursor.execute("SELECT login, bio, photo, phone, email, address, education, work, is_admin FROM users WHERE login = ?", (target_login.strip(),))
                                row = cursor.fetchone()
                            except sqlite3.OperationalError:
                                cursor.execute("SELECT login, bio, photo, is_admin FROM users WHERE login = ?", (target_login.strip(),))
                                r = cursor.fetchone()
                                row = (r[0], r[1], r[2], '', '', '', '', '', r[3]) if r else None
                            conn.close()
                            if row:
                                client_socket.send(f"PROFILE {row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}|{row[6]}|{row[7]}|{row[8]}\n".encode())
                            else:
                                client_socket.send("❌ Utilisateur introuvable\n".encode())
                        
                        elif line.startswith("UPDATE_PROFILE "):
                            rest = line[14:].strip()
                            space = rest.find(' ')
                            if space > 0:
                                field = rest[:space]
                                value = rest[space+1:]
                                conn = self.get_db_connection()
                                cursor = conn.cursor()
                                if field == "bio":
                                    cursor.execute("UPDATE users SET bio = ? WHERE id = ?", (value, user_id))
                                    conn.commit()
                                    conn.close()
                                    client_socket.send("✅ Bio mise à jour\n".encode())
                                elif field == "login":
                                    try:
                                        cursor.execute("UPDATE users SET login = ? WHERE id = ?", (value, user_id))
                                        conn.commit()
                                        conn.close()
                                        client_socket.send(f"✅ Login changé en '{value}'\n".encode())
                                    except sqlite3.IntegrityError:
                                        conn.close()
                                        client_socket.send("❌ Ce login est déjà pris\n".encode())
                                elif field == "password":
                                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (value, user_id))
                                    conn.commit()
                                    conn.close()
                                    client_socket.send("✅ Mot de passe mis à jour\n".encode())
                                elif field in ("phone", "email", "address", "education", "work", "photo"):
                                    cursor.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
                                    conn.commit()
                                    conn.close()
                                    client_socket.send(f"✅ {field.capitalize()} mis à jour\n".encode())
                                else:
                                    conn.close()
                                    client_socket.send("❌ Champ invalide (bio, login, password, phone, email, address, education, work, photo)\n".encode())
                            else:
                                client_socket.send("❌ Format: UPDATE_PROFILE <bio|login|password> <valeur>\n".encode())
                        
                        elif line.startswith("DELETE_USER "):
                            _, target_login = line.split(" ", 1)
                            target_login = target_login.strip()
                            conn = self.get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
                            row = cursor.fetchone()
                            if row and row[0] == 1:
                                cursor.execute("DELETE FROM users WHERE login = ?", (target_login,))
                                affected = cursor.rowcount
                                conn.commit()
                                conn.close()
                                if affected > 0:
                                    client_socket.send(f"✅ Utilisateur '{target_login}' supprimé\n".encode())
                                    # Déconnecter si connecté
                                    for uid, sock in list(self.connected_users.items()):
                                        if self.get_user_by_id(uid) == target_login:
                                            try:
                                                sock.send("❌ Votre compte a été supprimé par l'administrateur\n".encode())
                                                sock.close()
                                            except:
                                                pass
                                            del self.connected_users[uid]
                                            break
                                else:
                                    client_socket.send("❌ Utilisateur introuvable\n".encode())
                            else:
                                conn.close()
                                client_socket.send("❌ Seul l'administrateur peut supprimer des utilisateurs\n".encode())
                        
                        elif line == "QUIT":
                            response = "👋 Au revoir !\n"
                            client_socket.send(response.encode())
                            break
                        
                        else:
                            response = "❌ Commande inconnue. Utilisez : SEND, LIST, USERS, DELETE, CREATE_GROUP, GROUP_SEND, LIST_GROUPS, GROUP_MEMBERS, LEAVE_GROUP, REMOVE_FROM_GROUP, GET_PROFILE, UPDATE_PROFILE ou QUIT\n"
                            client_socket.send(response.encode())
                        
        except Exception as e:
            print(f"❌ Erreur avec {address}: {e}")
            logging.error(f"Erreur avec {address}: {e}")
        finally:
            if user_id and user_id in self.connected_users:
                del self.connected_users[user_id]
            client_socket.close()
            if username:
                print(f"🔌 {username} déconnecté de {address}")
                logging.info(f"{username} déconnecté de {address}")
            else:
                print(f"🔌 Client non authentifié déconnecté de {address}")

    def get_group_creator(self, group_id):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT creator_id FROM groups WHERE id = ?", (group_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def delete_group(self, group_id, user_id):
        creator = self.get_group_creator(group_id)
        if creator != user_id:
            return False
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM group_messages WHERE group_id = ?", (group_id,))
        cursor.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))
        cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        conn.commit()
        conn.close()
        return True


if __name__ == "__main__":
    server = ChatServer(HOST, PORT)
    server.start()