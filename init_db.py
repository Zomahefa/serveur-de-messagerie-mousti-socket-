import sqlite3
import os

DB_NAME = "messagerie.db"

def init_database():
    """Initialise la base de données avec les tables nécessaires"""
    
    # Supprimer l'ancienne base si elle existe (pour repartir de zéro)
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"✅ Ancienne base supprimée : {DB_NAME}")
    
    # Connexion à la base (la crée automatiquement)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table des utilisateurs
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        bio TEXT DEFAULT '',
        photo TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        address TEXT DEFAULT '',
        education TEXT DEFAULT '',
        work TEXT DEFAULT '',
        is_admin INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Table des messages
    cursor.execute("""
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_read BOOLEAN DEFAULT 0,
        FOREIGN KEY (sender_id) REFERENCES users(id),
        FOREIGN KEY (receiver_id) REFERENCES users(id)
    )
    """)
    
    # Tables des groupes
    cursor.execute("""
    CREATE TABLE groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        creator_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE group_members (
        group_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (group_id, user_id)
    )
    """)
    cursor.execute("""
    CREATE TABLE group_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Ajouter des utilisateurs de test
    users = [
        ('alice', '1234'),
        ('bob', '5678'),
        ('charlie', '91011'),
        ('diana', 'password')
    ]
    
    cursor.executemany("INSERT INTO users (login, password) VALUES (?, ?)", users)
    
    # Alice est admin
    cursor.execute("UPDATE users SET is_admin = 1 WHERE login = 'alice'")
    
    # Valider les changements
    conn.commit()
    
    print("✅ Base de données créée avec succès !")
    print(f"📁 {DB_NAME}")
    print("👥 Utilisateurs créés :", [user[0] for user in users])
    
    # Fermer la connexion
    conn.close()

if __name__ == "__main__":
    init_database()
