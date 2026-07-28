import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from datetime import datetime, timedelta
import time
import re
import os
from PIL import Image, ImageTk, ImageDraw
import io

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("💬 Messagerie")
        self.root.geometry("950x650")
        
        # Variables réseau
        self.socket = None
        self.connected = False
        self.authenticated = False
        self.username = None
        self.running = False
        
        # Données
        self.messages = {}  # {user: [list of messages]}
        self.all_users = []  # Tous les utilisateurs de la base
        self.online_users = []  # Utilisateurs connectés
        self.current_conv = None
        self.current_conv_key = None  # Pour suivre les IDs
        self.typing_timer = None
        self.last_typing_time = 0
        self._seen_ids = set()
        self._notified_group_keys = set()
        self._profile_callbacks = []
        
        # Données groupes
        self.groups = {}  # {gid: gname}
        
        # Interface
        self.setup_login()
    
    # ========== INTERFACE DE CONNEXION ==========
    def setup_login(self):
        self.login_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        center = tk.Frame(self.login_frame, bg='white', relief=tk.RAISED, bd=2)
        center.place(relx=0.5, rely=0.5, anchor='center', width=350)
        
        tk.Label(center, text="💬", font=('Arial', 36), bg='white').pack(pady=(20, 0))
        tk.Label(center, text="Messagerie", font=('Arial', 18, 'bold'), 
                bg='white', fg='#075E54').pack()
        tk.Label(center, text="Connectez-vous", font=('Arial', 10), 
                bg='white', fg='#888').pack(pady=(0, 15))
        
        f = tk.Frame(center, bg='white')
        f.pack(pady=10, padx=30, fill=tk.X)
        
        tk.Label(f, text="Serveur:", bg='white', anchor='w').pack(fill=tk.X)
        self.srv_entry = tk.Entry(f, bg='#f5f5f5', relief=tk.FLAT)
        self.srv_entry.insert(0, "localhost")
        self.srv_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)
        
        tk.Label(f, text="Port:", bg='white', anchor='w').pack(fill=tk.X)
        self.port_entry = tk.Entry(f, bg='#f5f5f5', relief=tk.FLAT)
        self.port_entry.insert(0, "8888")
        self.port_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)
        
        tk.Label(f, text="Login:", bg='white', anchor='w').pack(fill=tk.X)
        self.login_entry = tk.Entry(f, bg='#f5f5f5', relief=tk.FLAT)
        self.login_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)
        
        tk.Label(f, text="Mot de passe:", bg='white', anchor='w').pack(fill=tk.X)
        self.pwd_entry = tk.Entry(f, bg='#f5f5f5', relief=tk.FLAT, show="●")
        self.pwd_entry.pack(fill=tk.X, pady=(0, 8), ipady=4)
        
        self.status = tk.Label(f, text="", bg='white', fg='red')
        self.status.pack(pady=5)
        
        self.btn = tk.Button(f, text="Se connecter", command=self.do_connect,
                            bg='#25D366', fg='white', font=('Arial', 11, 'bold'),
                            relief=tk.FLAT, height=2)
        self.btn.pack(fill=tk.X, pady=10)
        
        tk.Label(f, text="alice/1234  •  bob/5678  •  charlie/91011", 
                font=('Arial', 8), bg='white', fg='#aaa').pack(pady=(0, 5))
        
        tk.Button(f, text="Créer un compte", command=self.register_dialog,
                 bg='#128C7E', fg='white', font=('Arial', 9, 'bold'),
                 relief=tk.FLAT, height=1).pack(fill=tk.X, pady=(0, 10))
        
        self.pwd_entry.bind('<Return>', lambda e: self.do_connect())
        self.login_entry.bind('<Return>', lambda e: self.pwd_entry.focus())
    
    def register_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Créer un compte")
        dialog.geometry("350x280")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.after(50, dialog.grab_set)
        
        tk.Label(dialog, text="📝 Nouveau compte", font=('Arial', 14, 'bold'),
                bg='white', fg='#075E54').pack(pady=(20, 15))
        
        tk.Label(dialog, text="Login:", bg='white').pack()
        login_e = tk.Entry(dialog, font=('Arial', 12), bg='#f5f5f5', relief=tk.FLAT)
        login_e.pack(pady=5, padx=30, fill=tk.X, ipady=3)
        login_e.focus()
        
        tk.Label(dialog, text="Mot de passe:", bg='white').pack()
        pwd_e = tk.Entry(dialog, font=('Arial', 12), bg='#f5f5f5', relief=tk.FLAT, show="●")
        pwd_e.pack(pady=5, padx=30, fill=tk.X, ipady=3)
        
        status_lbl = tk.Label(dialog, text="", bg='white', fg='red')
        status_lbl.pack(pady=5)
        
        def do_register():
            l = login_e.get().strip()
            p = pwd_e.get().strip()
            if not l or not p:
                status_lbl.config(text="Remplissez tous les champs")
                return
            try:
                import time
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((self.srv_entry.get().strip(), int(self.port_entry.get().strip())))
                # Lire le message de bienvenue (peut être dans le buffer)
                time.sleep(0.2)
                try:
                    sock.recv(4096)
                except:
                    pass
                sock.send(f"REGISTER {l} {p}\n".encode())
                time.sleep(0.3)
                resp = sock.recv(4096).decode().strip()
                sock.close()
                if "✅" in resp:
                    status_lbl.config(text="✅ Compte créé ! Connectez-vous", fg='green')
                    dialog.after(1500, dialog.destroy)
                else:
                    status_lbl.config(text=resp.replace("❌", "").strip() or "Erreur inconnue")
            except Exception as e:
                status_lbl.config(text=f"❌ Erreur: {e}")
        
        tk.Button(dialog, text="Créer un compte", command=do_register,
                 bg='#25D366', fg='white', font=('Arial', 11, 'bold'),
                 relief=tk.FLAT).pack(pady=10, padx=30, fill=tk.X)
        pwd_e.bind('<Return>', lambda e: do_register())
    
    def _load_circle_photo(self, path, size=100):
        try:
            img = Image.open(path).convert('RGBA')
            img = img.resize((size, size), Image.LANCZOS)
            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            result.paste(img, (0, 0), mask)
            return ImageTk.PhotoImage(result)
        except:
            return None

    def _load_circle_from_bytes(self, data, size=100):
        try:
            img = Image.open(io.BytesIO(data)).convert('RGBA')
            img = img.resize((size, size), Image.LANCZOS)
            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            result.paste(img, (0, 0), mask)
            return ImageTk.PhotoImage(result)
        except:
            return None
    
    def show_profile_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Mon Profil")
        dialog.geometry("420x640")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.after(50, dialog.grab_set)
        
        # Zone scrollable
        canvas = tk.Canvas(dialog, bg='white', highlightthickness=0)
        scrollbar = tk.Scrollbar(dialog, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg='white')
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        tk.Label(scroll_frame, text=f"👤 {self.username}", font=('Arial', 18, 'bold'),
                bg='white', fg='#075E54').pack(pady=(20, 5))
        
        photo_preview = tk.Label(scroll_frame, bg='white')
        photo_preview.pack(pady=(0, 10))
        self._preview_images = []
        
        def update_preview(path):
            for img in self._preview_images:
                img = None
            self._preview_images.clear()
            if not path:
                photo_preview.config(image='')
                return
            if os.path.isfile(path):
                photo_img = self._load_circle_photo(path, 90)
                if photo_img:
                    self._preview_images.append(photo_img)
                    photo_preview.config(image=photo_img)
                    return
            try:
                raw = bytes.fromhex(path)
                if len(raw) > 50:
                    photo_img = self._load_circle_from_bytes(raw, 90)
                    if photo_img:
                        self._preview_images.append(photo_img)
                        photo_preview.config(image=photo_img)
                        return
            except:
                pass
            photo_preview.config(image='')
        
        def _add_field(label_text, show=None, height=1, default=''):
            tk.Label(scroll_frame, text=label_text, font=('Arial', 10, 'bold'),
                    bg='white', anchor='w').pack(fill=tk.X, padx=30, pady=(10, 2))
            if height > 1:
                w = tk.Text(scroll_frame, font=('Arial', 11), bg='#f5f5f5', relief=tk.FLAT,
                           height=height, width=40)
                w.pack(padx=30, pady=2, ipady=3, fill=tk.X)
                w.insert('1.0', default)
            else:
                w = tk.Entry(scroll_frame, font=('Arial', 11), bg='#f5f5f5', relief=tk.FLAT, show=show)
                w.pack(padx=30, pady=2, ipady=3, fill=tk.X)
                w.insert(0, default)
            return w
        
        self._pending_profile = True
        try:
            self.socket.send(f"GET_PROFILE {self.username}\n".encode())
        except:
            pass
        
        login_w = _add_field("Login:", default=self.username)
        pwd_w = _add_field("Mot de passe:", show="●", default="********")
        bio_w = _add_field("Bio:", height=3)
        phone_w = _add_field("Téléphone:")
        email_w = _add_field("Email:")
        address_w = _add_field("Adresse:")
        education_w = _add_field("Études:")
        work_w = _add_field("Travail:")
        
        # Photo avec upload fichier
        tk.Label(scroll_frame, text="Photo:", font=('Arial', 10, 'bold'),
                bg='white', anchor='w').pack(fill=tk.X, padx=30, pady=(10, 2))
        photo_frame = tk.Frame(scroll_frame, bg='white')
        photo_frame.pack(fill=tk.X, padx=30, pady=2)
        photo_w = tk.Entry(photo_frame, font=('Arial', 11), bg='#f5f5f5', relief=tk.FLAT)
        photo_w.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        def browse_photo():
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="Choisir une photo",
                filetypes=[("Images", "*.png *.jpg *.jpeg"), ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")]
            )
            if path:
                photo_w.delete(0, tk.END)
                photo_w.insert(0, path)
                update_preview(path)
        tk.Button(photo_frame, text="📂", command=browse_photo,
                 bg='#f5f5f5', relief=tk.FLAT, font=('Arial', 12)).pack(side=tk.RIGHT, padx=(5,0))
        
        status_lbl = tk.Label(scroll_frame, text="", bg='white', fg='green', font=('Arial', 9))
        status_lbl.pack(pady=5)
        
        def wait_profile():
            if hasattr(self, '_profile_data') and self._profile_data:
                data = self._profile_data
                if data.get('login') != self.username:
                    dialog.after(100, wait_profile)
                    return
                del self._profile_data
                fields = {
                    'bio': bio_w, 'phone': phone_w, 'email': email_w,
                    'address': address_w, 'education': education_w,
                    'work': work_w, 'photo': photo_w
                }
                for key, widget in fields.items():
                    val = data.get(key, '') or ''
                    if isinstance(widget, tk.Text):
                        widget.delete('1.0', tk.END)
                        widget.insert('1.0', val)
                    else:
                        widget.delete(0, tk.END)
                        widget.insert(0, val)
                photo_path = data.get('photo', '') or ''
                update_preview(photo_path)
                return
            dialog.after(100, wait_profile)
        
        def save_all():
            new_login = login_w.get().strip()
            new_pwd = pwd_w.get().strip()
            photo_val = photo_w.get().strip()
            if photo_val and os.path.isfile(photo_val):
                with open(photo_val, 'rb') as f:
                    photo_val = f.read().hex()
            fields = {
                'bio': bio_w.get('1.0', tk.END).strip() if isinstance(bio_w, tk.Text) else bio_w.get().strip(),
                'phone': phone_w.get().strip(),
                'email': email_w.get().strip(),
                'address': address_w.get().strip(),
                'education': education_w.get().strip(),
                'work': work_w.get().strip(),
                'photo': photo_val,
            }
            try:
                if new_login and new_login != self.username:
                    self.socket.send(f"UPDATE_PROFILE login {new_login}\n".encode())
                if new_pwd and new_pwd != "********":
                    self.socket.send(f"UPDATE_PROFILE password {new_pwd}\n".encode())
                for key, val in fields.items():
                    if val:
                        self.socket.send(f"UPDATE_PROFILE {key} {val}\n".encode())
                if new_login and new_login != self.username:
                    self.username = new_login
                status_lbl.config(text="✅ Profil mis à jour")
                dialog.after(1500, dialog.destroy)
                self.root.after(500, self.refresh)
            except:
                status_lbl.config(text="❌ Erreur réseau", fg='red')
        
        if hasattr(self, '_is_admin') and self._is_admin:
            tk.Button(scroll_frame, text="👥 Gérer les utilisateurs", command=self.admin_users_dialog,
                     bg='#e74c3c', fg='white', font=('Arial', 10, 'bold'),
                     relief=tk.FLAT).pack(pady=10, padx=30, fill=tk.X)
        
        tk.Button(scroll_frame, text="Sauvegarder", command=save_all,
                 bg='#25D366', fg='white', font=('Arial', 11, 'bold'),
                 relief=tk.FLAT).pack(pady=10, padx=30, fill=tk.X)
        
        dialog.after(200, wait_profile)
        try:
            self.socket.send(f"GET_PROFILE {self.username}\n".encode())
        except:
            pass
    
    def admin_users_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Gestion des utilisateurs")
        dialog.geometry("400x400")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.after(50, dialog.grab_set)
        
        tk.Label(dialog, text="👥 Tous les utilisateurs", font=('Arial', 14, 'bold'),
                bg='white', fg='#075E54').pack(pady=(15, 10))
        
        listbox = tk.Listbox(dialog, font=('Arial', 11), relief=tk.FLAT,
                            bg='white', selectbackground='#e74c3c', selectforeground='white')
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        for u in self.all_users:
            if u != self.username:
                listbox.insert(tk.END, u)
        
        def delete_user():
            sel = listbox.curselection()
            if sel:
                target = listbox.get(sel[0])
                if messagebox.askyesno("🗑️ Supprimer", f"Supprimer '{target}' définitivement ?"):
                    try:
                        self.socket.send(f"DELETE_USER {target}\n".encode())
                        messagebox.showinfo("✅ Succès", f"Utilisateur '{target}' supprimé")
                        listbox.delete(sel[0])
                        self.root.after(500, self.refresh)
                    except:
                        messagebox.showerror("Erreur", "Erreur réseau")
        
        tk.Button(dialog, text="🗑️ SUPPRIMER L'UTILISATEUR", command=delete_user,
                 bg='#e74c3c', fg='white', font=('Arial', 11, 'bold'),
                 relief=tk.FLAT).pack(pady=10, padx=20, fill=tk.X)
    
    # ========== CONNEXION ==========
    def do_connect(self):
        server = self.srv_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except:
            port = 8888
        login = self.login_entry.get().strip()
        password = self.pwd_entry.get().strip()
        
        if not login or not password:
            messagebox.showerror("Erreur", "Remplissez tous les champs")
            return
        
        self.btn.config(state=tk.DISABLED, text="⏳ Connexion...")
        self.status.config(text="Connexion en cours...", fg='orange')
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
            self.socket.connect((server, port))
            self.socket.settimeout(None)
            
            self.connected = True
            self.running = True
            
            self.socket.send(f"LOGIN {login} {password}\n".encode())
            
            response = ""
            while True:
                try:
                    chunk = self.socket.recv(4096).decode()
                    if not chunk:
                        break
                    response += chunk
                    if "✅" in chunk or "❌" in chunk:
                        break
                except:
                    break
            
            if "Authentifié" in response:
                self.username = login
                self.authenticated = True
                
                self.login_frame.destroy()
                self.setup_chat()
                
                threading.Thread(target=self.receive, daemon=True).start()
                self.root.after(200, lambda: self.socket.send("ALLUSERS\n".encode()))
                self.root.after(500, self.refresh)
                
                messagebox.showinfo("Succès", f"✅ Connecté en tant que {login}")
            else:
                self.status.config(text="❌ Authentification échouée", fg='red')
                self.socket.close()
                self.connected = False
                self.btn.config(state=tk.NORMAL, text="Se connecter")
                messagebox.showerror("Erreur", "❌ Identifiants incorrects")
                
        except Exception as e:
            self.status.config(text=f"❌ Erreur: {e}", fg='red')
            self.btn.config(state=tk.NORMAL, text="Se connecter")
            messagebox.showerror("Erreur", f"Connexion échouée: {e}")
    
    # ========== INTERFACE DE CHAT ==========
    def setup_chat(self):
        self.chat_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        
        main = tk.PanedWindow(self.chat_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        main.pack(fill=tk.BOTH, expand=True)
        
        # === GAUCHE : Liste des utilisateurs ===
        left = tk.Frame(main, bg='white', width=250)
        main.add(left, width=250)
        
        # En-tête avec bouton déconnexion
        header = tk.Frame(left, bg='#075E54', height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text=f"👤 {self.username}", font=('Arial', 14, 'bold'),
                bg='#075E54', fg='white').pack(side=tk.LEFT, padx=15, pady=10)
        
        # Bouton Profil
        tk.Button(header, text="⚙ Profil", command=self.show_profile_dialog,
                 bg='#128C7E', fg='white', relief=tk.FLAT,
                 font=('Arial', 10, 'bold'), cursor='hand2',
                 padx=8).pack(side=tk.RIGHT, padx=2)
        
        # Bouton DÉCONNEXION
        tk.Button(header, text="Déconnexion", command=self.do_logout,
                 bg='#c0392b', fg='white', relief=tk.FLAT,
                 font=('Arial', 10, 'bold'), cursor='hand2',
                 padx=10).pack(side=tk.RIGHT, padx=10)
        
        # Section utilisateurs connectés
        tk.Label(left, text="● En ligne", font=('Arial', 10, 'bold'),
                bg='white', fg='#4CAF50').pack(anchor='w', padx=15, pady=(10, 5))
        
        self.online_listbox = tk.Listbox(left, font=('Arial', 10), relief=tk.FLAT,
                                         bg='#f0f8f0', height=4,
                                         selectbackground='#25D366', selectforeground='white')
        self.online_listbox.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.online_listbox.bind('<<ListboxSelect>>', self.on_user_selected)
        
        # Section tous les utilisateurs
        tk.Label(left, text="○ Tous les utilisateurs", font=('Arial', 10, 'bold'),
                bg='white', fg='#666').pack(anchor='w', padx=15, pady=(10, 5))
        
        self.user_listbox = tk.Listbox(left, font=('Arial', 10), relief=tk.FLAT,
                                       bg='white', height=10,
                                       selectbackground='#25D366', selectforeground='white')
        self.user_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        self.user_listbox.bind('<<ListboxSelect>>', self.on_user_selected)
        
        # === CENTRE : Chat ===
        center = tk.Frame(main, bg='white')
        main.add(center, width=500)
        
        self.chat_header = tk.Frame(center, bg='#075E54', height=50)
        self.chat_header.pack(fill=tk.X)
        self.chat_header.pack_propagate(False)
        
        self.chat_label = tk.Label(self.chat_header, text="Sélectionnez un utilisateur",
                                  font=('Arial', 14, 'bold'), bg='#075E54', fg='white')
        self.chat_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.online_label = tk.Label(self.chat_header, text="", font=('Arial', 9),
                                    bg='#075E54', fg='#4CAF50')
        self.online_label.pack(side=tk.LEFT, padx=10)
        
        self.typing_label = tk.Label(self.chat_header, text="", font=('Arial', 9, 'italic'),
                                    bg='#075E54', fg='#FFD700')
        self.typing_label.pack(side=tk.LEFT, padx=10)
        
        self.download_label = tk.Label(self.chat_header, text="", font=('Arial', 9, 'bold'),
                                      bg='#075E54', fg='#FFD700')
        self.download_label.pack(side=tk.LEFT, padx=10)
        
        self.msg_frame = tk.Frame(center, bg='#ece5dd')
        self.msg_frame.pack(fill=tk.BOTH, expand=True)
        
        self.msg_canvas = tk.Canvas(self.msg_frame, bg='#ece5dd', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.msg_frame, orient=tk.VERTICAL, command=self.msg_canvas.yview)
        self.msg_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.msg_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.msg_inner = tk.Frame(self.msg_canvas, bg='#ece5dd')
        self.msg_inner.bind('<Configure>', lambda e: self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox('all')))
        self.msg_canvas.create_window((0, 0), window=self.msg_inner, anchor='nw')
        
        input_frame = tk.Frame(center, bg='white', height=60)
        input_frame.pack(fill=tk.X)
        input_frame.pack_propagate(False)
        
        self.input_text = tk.Text(input_frame, height=2, font=('Arial', 11),
                                  wrap=tk.WORD, relief=tk.FLAT, padx=10, pady=5)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.input_text.bind("<Return>", self.on_enter)
        self.input_text.bind("<Shift-Return>", lambda e: self.input_text.insert(tk.INSERT, '\n'))
        self.input_text.bind("<KeyRelease>", self.on_typing)
        
        self.file_btn = tk.Button(input_frame, text="📎", command=self.send_file,
                                 bg='#f5f5f5', font=('Arial', 14),
                                 relief=tk.FLAT, width=3)
        self.file_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        self.send_btn = tk.Button(input_frame, text="Envoyer", command=self.send_message,
                                 bg='#25D366', fg='white', font=('Arial', 10, 'bold'),
                                 relief=tk.FLAT, padx=15)
        self.send_btn.pack(side=tk.RIGHT, padx=10, pady=8)
        
        # === DROITE : Actions ===
        right = tk.Frame(main, bg='white', width=120)
        main.add(right, width=120)
        
        self.del_frame = None
        self.del_entry = None
        
        tk.Button(right, text="⟳ Rafraîchir", command=self.refresh,
                 bg='#f5f5f5', font=('Arial', 10, 'bold'),
                 relief=tk.FLAT).pack(fill=tk.X, pady=10, padx=10)
        
        # === Groupes ===
        grp_frame = tk.LabelFrame(right, text="Groupes", font=('Arial', 10, 'bold'),
                                  bg='white', padx=10, pady=10)
        grp_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.grp_listbox = tk.Listbox(grp_frame, font=('Arial', 9), relief=tk.FLAT,
                                      bg='white', height=4,
                                      selectbackground='#075E54', selectforeground='white')
        self.grp_listbox.pack(fill=tk.X)
        self.grp_listbox.bind('<<ListboxSelect>>', self.on_group_selected)
        
        tk.Button(grp_frame, text="+ Créer un groupe", command=self.create_group_dialog,
                 bg='#f5f5f5', font=('Arial', 9, 'bold'),
                 relief=tk.FLAT).pack(fill=tk.X, pady=(5,0))
        tk.Button(grp_frame, text="+ Ajouter membre", command=self.add_member_dialog,
                 bg='#f5f5f5', font=('Arial', 9, 'bold'),
                 relief=tk.FLAT).pack(fill=tk.X, pady=(2,0))
        
        self.auto_refresh()
    
    def auto_refresh(self):
        if self.connected and self.authenticated:
            self.refresh()
        if self.connected and self.authenticated:
            self.root.after(2000, self.auto_refresh)
    
    # ========== RÉCEPTION ==========
    def receive(self):
        buffer = ""
        while self.running and self.connected:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self.process_line(line.strip())
            except:
                break
        
        if self.running:
            self.running = False
            self.connected = False
            self.root.after(0, lambda: messagebox.showerror("Déconnexion", "Connexion perdue"))
    
    def process_line(self, line):
        """Traite une ligne reçue du serveur"""
        # === Tous les utilisateurs (ALLUSERS) ===
        if line.startswith('🟢') or line.startswith('🔴'):
            user = line[2:].strip()
            if user and user != self.username:
                if user not in self.all_users:
                    self.all_users.append(user)
                if line.startswith('🟢'):
                    if user not in self.online_users:
                        self.online_users.append(user)
                else:
                    if user in self.online_users:
                        self.online_users.remove(user)
                self.root.after(0, self.update_lists)
            return
        
        # === Membres du groupe (AVANT le générique - et 👥) ===
        if line.startswith('👥 Membres du groupe'):
            self._parsing_members = True
            self._current_members_list = []
            self._current_members_gid = getattr(self, '_pending_members_gid', None)
            return
        
        if getattr(self, '_parsing_members', False) and line.startswith('- '):
            member_name = line[2:].strip()
            if member_name:
                self._current_members_list.append(member_name)
            return
        
        if '-- END MEMBERS --' in line and getattr(self, '_parsing_members', False):
            if self._current_members_gid and self._current_members_list:
                if not hasattr(self, '_group_members'):
                    self._group_members = {}
                self._group_members[self._current_members_gid] = self._current_members_list
            self._parsing_members = False
            return
        
        # === Utilisateurs connectés ===
        if line.startswith('- '):
            user = line[2:].strip()
            if user and user != self.username:
                if user not in self.online_users:
                    self.online_users.append(user)
                if user not in self.all_users:
                    self.all_users.append(user)
                self.root.after(0, self.update_lists)
            return
        
        if line.startswith('👥') or line.startswith('👤'):
            self.root.after(0, self.update_lists)
            return
        
        # === Ligne "Messages pour" - signale le début d'une liste ===
        if '📨' in line and 'Messages' in line:
            self._seen_ids = set()
            return
        
        # === Liste des groupes ===
        if line.startswith('📋 VOS GROUPES'):
            self.groups = {}
            self._owned_groups = set()
            self.root.after(0, self.update_lists)
            return
        if re.match(r'^\d+:', line):
            match = re.match(r'(\d+):\s+([^*]+)', line)
            if match:
                gid = int(match.group(1))
                gname = match.group(2).strip()
                self.groups[gid] = gname
                is_owner = ' *' in line
                if is_owner:
                    self._owned_groups.add(gid)
                conv = f"📢 {gname}"
                if conv not in self.all_users:
                    self.all_users.append(conv)
                self.root.after(0, self.update_lists)
            return
        if line.startswith('📭 Vous n\'êtes dans aucun groupe'):
            self.groups = {}
            self.root.after(0, self.update_lists)
            return
        
        # === GROUPE message ===
        if '[GROUPE]' in line:
            match = re.search(r'Dans\s+"(.+?)"\s+\(ID:(\d+)\)\s+:\s+(\w+):\s+(.+)', line)
            if match:
                gname, gid, sender, content = match.group(1), match.group(2), match.group(3), match.group(4)
                conv = f"📢 {gname}"
                if conv not in self.all_users:
                    self.all_users.append(conv)
                if conv not in self.messages:
                    self.messages[conv] = []
                # Vérification doublon
                key = (conv, sender, content)
                found = key in getattr(self, '_notified_group_keys', set())
                if found:
                    self._notified_group_keys.discard(key)
                if not found:
                    for existing in self.messages[conv]:
                        if existing[2] == content and existing[0] == sender:
                            found = True
                            break
                if not found:
                    self.messages[conv].append((sender, conv, content,
                                               datetime.now().strftime('%Y-%m-%d %H:%M:%S'), False, 0))
                    self.root.after(0, self.update_lists)
                    if self.current_conv == conv:
                        self.root.after(0, lambda: self.show_conversation(conv))
            return
        
        # === Fin de liste ===
        if '-- END LIST --' in line:
            self._notified_group_keys = set()
            # Purger les messages supprimés
            for conv in list(self.messages.keys()):
                self.messages[conv] = [m for m in self.messages[conv] if m[5] == 0 or m[5] in self._seen_ids]
            if self.current_conv_key:
                self.root.after(0, lambda k=self.current_conv_key: self.show_conversation(k))
            return
        
        # === Messages ===
        if line.startswith('[ENVOYÉ]') or line.startswith('[REÇU]'):
            self.parse_message(line)
            return
        
        # === Ligne avec ID (récupère l'ID) ===
        if 'ID:' in line and '📅' in line:
            self.parse_id(line)
            return
        
        # === Nouveau message ===
        if 'Nouveau message de' in line:
            match = re.search(r'de\s+(\w+)', line)
            if match:
                sender = match.group(1)
                self.root.after(0, self.refresh)
                self.root.after(0, lambda s=sender: messagebox.showinfo(
                    "📩 Nouveau message", f"Nouveau message de {s}"))
            return
        
        # === Message envoyé ===
        if 'Message envoyé' in line:
            self.root.after(0, self.refresh)
            return
        
        # === Indicateur de frappe ===
        if '📝' in line and 'tape...' in line and not '[' in line:
            sender = line.replace('📝', '').replace('tape...', '').strip()
            self.root.after(0, lambda s=sender: self.show_typing(s))
            return
        if '📝' in line and "quelqu'un écrit" in line:
            self.root.after(0, self.show_typing_group)
            return
        if 'CLEAR_TYPING' in line and '[' not in line:
            self.root.after(0, self.hide_typing)
            return
        if 'CLEAR_TYPING_GROUP' in line:
            self.root.after(0, self.hide_typing)
            return
        
        # === Notification groupe ===
        if line.startswith('📩 Vous avez été ajouté au groupe'):
            self.root.after(0, self.refresh)
            self.root.after(0, lambda: messagebox.showinfo("📢 Groupe", line))
            return
        if line.startswith('📩 [') and '] ' in line:
            match = re.search(r'\[(.+?)\]\s+(\w+):\s+(.*)', line)
            if match:
                gname, sender, content = match.group(1), match.group(2), match.group(3)
                conv = f"📢 {gname}"
                if conv not in self.messages:
                    self.messages[conv] = []
                found = False
                for existing in self.messages[conv]:
                    if existing[2] == content and existing[0] == sender and existing[5] == 0:
                        found = True
                        break
                if not found:
                    self.messages[conv].append((sender, conv, content,
                                               datetime.now().strftime('%Y-%m-%d %H:%M:%S'), False, 0))
                    self._notified_group_keys.add((conv, sender, content))
                    self.root.after(0, self.update_lists)
                    if self.current_conv == conv:
                        self.root.after(0, lambda: self.show_conversation(conv))
                self.root.after(0, self.refresh)
            return
        
        # === Fichier reçu ===
        if line.startswith('📁 Fichier recu de') and '(groupe ' in line:
            match = re.search(r'de\s+(\w+)\s+\(groupe\s+(.+?)\):\s+(.+?):(\d+):(.+)', line)
            if match:
                sender, gname, filename, size, hex_data = match.group(1), match.group(2), match.group(3), match.group(4), match.group(5)
                os.makedirs("received_files", exist_ok=True)
                try:
                    with open(f"received_files/{filename}", 'wb') as f:
                        f.write(bytes.fromhex(hex_data))
                except:
                    pass
                conv = f"📢 {gname}"
                msg_content = f"📁:{filename}:{size}"
                if conv not in self.messages:
                    self.messages[conv] = []
                self.messages[conv].append((sender, conv, msg_content,
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'), False, 0))
                self.root.after(0, self.update_lists)
                if self.current_conv == conv:
                    self.root.after(0, lambda: self.show_conversation(conv))
            return
        if line.startswith('📁 Fichier recu de'):
            match = re.search(r'de\s+(\w+):\s+(.+?):(\d+):(.+)', line)
            if match:
                sender, filename, size, hex_data = match.group(1), match.group(2), match.group(3), match.group(4)
                os.makedirs("received_files", exist_ok=True)
                try:
                    with open(f"received_files/{filename}", 'wb') as f:
                        f.write(bytes.fromhex(hex_data))
                except:
                    pass
                msg_content = f"📁:{filename}:{size}"
                conv = sender
                if conv not in self.messages:
                    self.messages[conv] = []
                self.messages[conv].append((sender, self.username, msg_content,
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'), False, 0))
                self.root.after(0, self.update_lists)
                if self.current_conv == conv:
                    self.root.after(0, lambda: self.show_conversation(conv))
            return
        if line.startswith('✅ Fichier'):
            match = re.search(r'Fichier\s+(.+?)\s+envoyé', line)
            if match:
                filename = match.group(1)
                if self.current_conv:
                    conv = self.current_conv
                    msg_content = f"📁:{filename}:0"
                    if conv not in self.messages:
                        self.messages[conv] = []
                    self.messages[conv].append((self.username, conv, msg_content,
                                               datetime.now().strftime('%Y-%m-%d %H:%M:%S'), True, 0))
                    self.root.after(0, self.update_lists)
                    if self.current_conv == conv:
                        self.root.after(0, lambda: self.show_conversation(conv))
            return
        if line.startswith('FILE_DATA '):
            parts = line.split(' ', 2)
            if len(parts) >= 2:
                filename = parts[1]
                if len(parts) == 3:
                    hex_data = parts[2]
                    os.makedirs("received_files", exist_ok=True)
                    try:
                        with open(f"received_files/{filename}", 'wb') as f:
                            f.write(bytes.fromhex(hex_data))
                        self.root.after(0, lambda: self.download_label.config(text=""))
                        if hasattr(self, '_pending_file') and self._pending_file == filename:
                            self._pending_file = None
                            self.root.after(0, lambda f=filename: self._open_saved(f))
                    except Exception as e:
                        self.root.after(0, lambda: self.download_label.config(text=""))
                        self.root.after(0, lambda f=filename: messagebox.showerror("Erreur", f"Échec téléchargement {f}: {e}"))
                else:
                    self.root.after(0, lambda: self.download_label.config(text=""))
            return
        
        if line.startswith('❌ Fichier introuvable') or line.startswith('❌ Erreur de lecture'):
            self.root.after(0, lambda: self.download_label.config(text=""))
            if hasattr(self, '_pending_file') and self._pending_file:
                f = self._pending_file
                self._pending_file = None
                self.root.after(0, lambda fn=f: messagebox.showerror("Erreur", f"Fichier '{fn}' introuvable sur le serveur"))
            return
        
        # === Profil utilisateur ===
        if line.startswith('PROFILE '):
            parts = line[8:].split('|', 9)
            if len(parts) >= 9:
                login, bio, photo, phone, email, address, education, work, is_admin = parts[:9]
                data = {
                    'login': login, 'bio': bio, 'photo': photo,
                    'phone': phone, 'email': email, 'address': address,
                    'education': education, 'work': work, 'is_admin': is_admin
                }
                self._profile_data = dict(data)
                self._is_admin = (is_admin == '1')
                for cb in self._profile_callbacks[:]:
                    try:
                        cb(data)
                    except:
                        pass
            return
        
        # === Suppression ===
        if 'supprimé avec succès' in line or line.startswith('🗑️ Message groupe'):
            id_match = re.search(r'Message(?: groupe)?\s+(\d+)', line)
            if id_match and self.current_conv_key and self.current_conv_key in self.messages:
                msg_id = int(id_match.group(1))
                self.messages[self.current_conv_key] = [m for m in self.messages[self.current_conv_key] if m[5] != msg_id]
            self.root.after(0, lambda: messagebox.showinfo("✅ Succès", line))
            self.root.after(0, lambda c=self.current_conv_key: self.show_conversation(c) if c else None)
            return
        if 'Message introuvable' in line:
            self.root.after(0, lambda: messagebox.showerror("❌ Erreur", line))
            return
        if 'message(s) supprimé(s)' in line:
            self.messages = {}
            self.root.after(0, lambda c=self.current_conv_key: self.show_conversation(c) if c else None)
            self.root.after(0, self.refresh)
            return
        

    
    def parse_id(self, line):
        """Récupère l'ID du message et la conv_key depuis la ligne"""
        try:
            id_match = re.search(r'ID:\s*(\d+)', line)
            if not id_match:
                return
            msg_id = int(id_match.group(1))
            self._seen_ids.add(msg_id)
            
            date_match = re.search(r'📅\s*([\d\-:\s]+)', line)
            date_str = date_match.group(1).strip() if date_match else ''
            
            is_read = '✔️' in line
            
            # Extraire la conv_key (format: login1:login2)
            conv_match = re.search(r'\|\s*(\w+:\w+)\s*$', line)
            conv_key = conv_match.group(1) if conv_match else None
            
            # Vérifier si c'est un message de groupe (a un ID mais pas de conv_key)
            is_group_line = '[GROUPE]' in line or conv_key is None
            
            # Utiliser le message en attente de parse_message
            pending = getattr(self, '_pending_msg', None)
            if pending and conv_key:
                sender, receiver, content = pending
                self._pending_msg = None
                # Stocker sous conv_key (p.ex. "alice:bob")
                if conv_key not in self.messages:
                    self.messages[conv_key] = []
                # Vérifier doublon
                found = any(existing[2] == content and existing[0] == sender
                           for existing in self.messages[conv_key])
                if not found:
                    self.messages[conv_key].append((sender, receiver, content,
                                                   date_str, is_read, msg_id))
                    self.root.after(0, self.update_lists)
                    if self.current_conv_key == conv_key:
                        self.root.after(0, lambda: self.show_conversation(conv_key))
            else:
                # Fallback: recherche dans toutes les conversations (messages sans conv_key)
                best = None
                for conv in list(self.messages.keys()):
                    msgs = self.messages[conv]
                    for i in range(len(msgs) - 1, -1, -1):
                        if msgs[i][5] == 0:
                            best = (conv, i)
                            break
                    if best:
                        break
                if best:
                    conv, i = best
                    old = self.messages[conv][i]
                    self.messages[conv][i] = (old[0], old[1], old[2], date_str, is_read, msg_id)
                    self.root.after(0, lambda c=conv: self.show_conversation(c) if self.current_conv_key == c else None)
        except:
            pass
    
    def parse_message(self, line):
        """Parse un message depuis la liste"""
        try:
            if '[ENVOYÉ]' in line:
                match = re.search(r'À\s+(\w+)\s+:\s*(.+)', line)
                if match:
                    dest = match.group(1)
                    content = match.group(2).strip()
                    content = re.sub(r'\s*\([\d\-:\s]+\)\s*', '', content)
                    content = re.sub(r'\s*ID:\s*\d+\s*', '', content)
                    content = re.sub(r'\s*[✔️📩]\s*', '', content)
                    content = re.sub(r'\s*\|\s*\w+:\w+\s*$', '', content)
                    content = content.strip()
                    self._pending_msg = (self.username, dest, content)
            else:
                match = re.search(r'De\s+(\w+)\s+:\s*(.+)', line)
                if match:
                    sender = match.group(1)
                    content = match.group(2).strip()
                    content = re.sub(r'\s*\([\d\-:\s]+\)\s*', '', content)
                    content = re.sub(r'\s*ID:\s*\d+\s*', '', content)
                    content = re.sub(r'\s*[✔️📩]\s*', '', content)
                    content = re.sub(r'\s*\|\s*\w+:\w+\s*$', '', content)
                    content = content.strip()
                    self._pending_msg = (sender, self.username, content)
        except:
            pass
    
    def add_message(self, sender, receiver, content, msg_id):
        """Ajoute un message dans le cache"""
        conv = receiver if sender == self.username else sender

        if conv not in self.messages:
            self.messages[conv] = []
        
        if conv not in self.all_users and conv != self.username:
            self.all_users.append(conv)
        
        for existing in self.messages[conv]:
            if existing[2] == content:
                return
        
        self.messages[conv].append((sender, receiver, content, 
                                   datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0, msg_id))
        self.root.after(0, self.update_lists)
        
        if self.current_conv == conv:
            self.root.after(0, lambda: self.show_conversation(conv))
    
    # ========== AFFICHAGE ==========
    def update_lists(self):
        """Met à jour les deux listes"""
        self.update_online_list()
        self.update_all_users_list()
        self.update_groups_list()
    
    def update_online_list(self):
        """Met à jour la liste des utilisateurs connectés"""
        self.online_listbox.delete(0, tk.END)
        
        online = sorted([u for u in self.online_users if u != self.username])
        if not online:
            self.online_listbox.insert(tk.END, "Aucun utilisateur en ligne")
        else:
            for user in online:
                self.online_listbox.insert(tk.END, f"● {user}")
    
    def update_all_users_list(self):
        """Met à jour la liste de tous les utilisateurs"""
        self.user_listbox.delete(0, tk.END)
        
        all_users = set(self.all_users)
        for key in self.messages.keys():
            if not key.startswith('📢 '):
                all_users.add(self.key_to_display(key))
        all_users.discard(self.username)
        
        # Filtrer ceux qui sont déjà en ligne (pour éviter les doublons)
        offline_users = sorted([u for u in all_users if u not in self.online_users])
        
        if not offline_users:
            self.user_listbox.insert(tk.END, "Aucun autre utilisateur")
        else:
            for user in offline_users:
                self.user_listbox.insert(tk.END, f"○ {user}")
    
    def on_user_selected(self, event):
        """Sélection d'un utilisateur (depuis l'une ou l'autre liste)"""
        # Vérifier d'abord la liste en ligne
        selection = self.online_listbox.curselection()
        if selection:
            name = self.online_listbox.get(selection[0])
            name = name.replace("●", "").strip()
            self.set_current_conv(name)
            return
        
        # Puis la liste de tous les utilisateurs
        selection = self.user_listbox.curselection()
        if selection:
            name = self.user_listbox.get(selection[0])
            name = name.replace("○", "").strip()
            self.set_current_conv(name)
    
    def set_current_conv(self, name):
        """Définit la conversation courante"""
        display = self.key_to_display(name) if ':' in name else name
        conv_key = self.display_to_key(name)
        self.current_conv = display
        self.current_conv_key = conv_key
        self.chat_label.config(text=f"💬 {display}")
        self.typing_label.config(text="")
        
        # Rendre le nom cliquable pour voir le profil
        if not conv_key.startswith('📢 '):
            self.chat_label.bind('<Button-1>', lambda e, u=display: self.view_user_profile(u))
            self.chat_label.config(cursor='hand2')
        else:
            self.chat_label.unbind('<Button-1>')
            self.chat_label.config(cursor='')
        
        # Nettoyer les boutons supplémentaires dans le header
        for w in self.chat_header.winfo_children():
            if w not in (self.chat_label, self.online_label, self.typing_label):
                w.destroy()
        
        if conv_key.startswith('📢 '):
            gname_display = conv_key[2:].strip()
            self.online_label.config(text="👥 Groupe", fg='#FF9800')
            gid = None
            for id_, n in self.groups.items():
                if n == gname_display:
                    gid = id_
                    break
            if gid:
                # Récupérer les membres
                self._pending_members_gid = gid
                try:
                    self.socket.send(f"GROUP_MEMBERS {gid}\n".encode())
                except:
                    pass
                # Bouton Membres
                tk.Button(self.chat_header, text="👥", command=lambda g=gid: self.show_group_members_dialog(g),
                         bg='#075E54', fg='white', relief=tk.FLAT,
                         font=('Arial', 12), cursor='hand2',
                         padx=8).pack(side=tk.RIGHT, padx=2)
                # Bouton Quitter le groupe
                tk.Button(self.chat_header, text="🚪", command=lambda g=gid: self.leave_group_confirm(g),
                         bg='#e67e22', fg='white', relief=tk.FLAT,
                         font=('Arial', 12), cursor='hand2',
                         padx=8).pack(side=tk.RIGHT, padx=2)
                # Bouton Supprimer (si créateur)
                if hasattr(self, '_owned_groups') and gid in self._owned_groups:
                    tk.Button(self.chat_header, text="🗑️", command=self.delete_group_confirm,
                             bg='#c0392b', fg='white', relief=tk.FLAT,
                             font=('Arial', 12), cursor='hand2',
                             padx=8).pack(side=tk.RIGHT, padx=2)
        elif display in self.online_users:
            self.online_label.config(text="● En ligne", fg='#4CAF50')
        else:
            self.online_label.config(text="○ Hors ligne", fg='red')
        
        # Nettoyer TOUS les widgets affichés (évite les fuites entre conversations)
        for k in list(getattr(self, '_displayed', {}).keys()):
            for w in self._displayed[k].values():
                try:
                    w.destroy()
                except:
                    pass
            del self._displayed[k]
        for widget in self.msg_inner.winfo_children():
            widget.destroy()
        
        self.show_conversation(conv_key)
    
    def display_to_key(self, name):
        if name.startswith('📢 '):
            return name
        parts = name.split(':')
        if len(parts) == 2:
            return name
        return ':'.join(sorted([self.username, name]))

    def key_to_display(self, key):
        if key.startswith('📢 '):
            return key[2:].strip()
        parts = key.split(':')
        if len(parts) == 2:
            return parts[0] if parts[1] == self.username else parts[1]
        return key

    def show_conversation(self, name):
        """Affiche les messages sans recréer ceux déjà affichés"""
        conv_key = self.display_to_key(name)
        # Ignorer si la conversation a changé entre-temps (safety)
        if conv_key != getattr(self, 'current_conv_key', None):
            return
        
        if not hasattr(self, '_displayed'):
            self._displayed = {}
        if conv_key not in self._displayed:
            self._displayed[conv_key] = {}
        
        displayed = self._displayed[conv_key]
        messages = self.messages.get(conv_key, [])
        current_keys = {(m[2], m[5]) for m in messages}
        
        at_bottom = (self.msg_canvas.yview()[1] >= 0.99)
        
        # Créer d'abord les nouveaux messages (pour éviter le flash)
        for msg in messages:
            key = (msg[2], msg[5])
            if key not in displayed:
                frame = tk.Frame(self.msg_inner, bg='#ece5dd')
                frame.pack(fill=tk.X)
                self._render_message_in(frame, msg)
                displayed[key] = frame
        
        # Puis supprimer ceux qui ne sont plus dans le cache
        for key in list(displayed.keys()):
            if key not in current_keys:
                displayed[key].destroy()
                del displayed[key]
        
        if not messages and '_empty' not in displayed:
            empty = tk.Frame(self.msg_inner, bg='#ece5dd')
            empty.pack(fill=tk.X, pady=50)
            tk.Label(empty, text="📭 Aucun message", font=('Arial', 14),
                    bg='#ece5dd', fg='gray').pack()
            displayed['_empty'] = empty
        elif messages and '_empty' in displayed:
            displayed['_empty'].destroy()
            del displayed['_empty']
        
        self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox('all'))
        if at_bottom:
            self.msg_canvas.yview_moveto(1.0)
    
    def display_message(self, msg):
        """Affiche un message (crée le cadre extérieur)"""
        frame = tk.Frame(self.msg_inner, bg='#ece5dd')
        frame.pack(fill=tk.X, padx=10, pady=3)
        self._render_message_in(frame, msg)
    
    def _render_message_in(self, frame, msg):
        """Rend le contenu du message dans un cadre déjà packé"""
        sender, receiver, content, date, is_read, msg_id = msg
        is_sent = (sender == self.username)
        is_file = content.startswith('📁:')
        is_group = receiver.startswith('📢 ') if hasattr(self, 'current_conv') and self.current_conv else False
        
        if is_sent:
            container = tk.Frame(frame, bg='#dcf8c6', relief=tk.RAISED, bd=1)
            container.pack(side=tk.RIGHT, anchor='e', padx=(50, 10))
        else:
            container = tk.Frame(frame, bg='white', relief=tk.RAISED, bd=1)
            container.pack(side=tk.LEFT, anchor='w', padx=(10, 50))
        
        if is_group and sender != self.username:
            name_lbl = tk.Label(container, text=sender, font=('Arial', 9, 'bold'),
                               bg=container['bg'], fg='#075E54', cursor='hand2')
            name_lbl.pack(padx=10, pady=(5, 0), anchor='w')
            name_lbl.bind('<Button-1>', lambda e, u=sender: self.view_user_profile(u))
        elif is_group:
            tk.Label(container, text="Vous", font=('Arial', 9, 'bold'),
                    bg=container['bg'], fg='#075E54').pack(padx=10, pady=(5, 0), anchor='w')
        
        if is_file:
            parts = content.split(':', 2)
            filename = parts[1] if len(parts) > 1 else "fichier"
            size = parts[2] if len(parts) > 2 else "?"
            cmd = lambda e, f=filename: self.open_file(f)
            sub = tk.Frame(container, bg=container['bg'], cursor='hand2')
            sub.pack(fill=tk.X, padx=10, pady=8)
            sub.bind('<Button-1>', cmd)
            icon = tk.Label(sub, text="📁", font=('Arial', 24), bg=container['bg'], cursor='hand2')
            icon.pack(side=tk.LEFT, padx=(0, 10))
            icon.bind('<Button-1>', cmd)
            name_lbl = tk.Label(sub, text=filename, font=('Arial', 11, 'bold'), bg=container['bg'],
                    fg='#075E54', wraplength=250, cursor='hand2')
            name_lbl.pack(anchor='nw')
            name_lbl.bind('<Button-1>', cmd)
            size_text = f"{size} octets" if size != '0' else "fichier"
            size_lbl = tk.Label(sub, text=size_text, font=('Arial', 9), bg=container['bg'],
                    fg='gray', cursor='hand2')
            size_lbl.pack(anchor='nw')
            size_lbl.bind('<Button-1>', cmd)
        else:
            tk.Label(container, text=content, font=('Arial', 11),
                    bg=container['bg'], wraplength=350, justify=tk.LEFT).pack(padx=10, pady=5)
        
        info = tk.Frame(container, bg=container['bg'])
        info.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        try:
            dt = datetime.strptime(date, '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)
            date_str = dt.strftime('%H:%M')
        except:
            date_str = date[:5] if len(date) >= 5 else date
        
        tk.Label(info, text=date_str, font=('Arial', 8), bg=container['bg'], fg='gray').pack(side=tk.LEFT)
        
        if msg_id and is_sent and not is_group:
            del_cmd = lambda e, m=msg_id, g=is_group: self.delete_message(m, group=g)
            tk.Label(info, text="🗑️", font=('Arial', 11), bg=container['bg'],
                    fg='gray', cursor='hand2').pack(side=tk.RIGHT, padx=(5, 0))
            info.winfo_children()[-1].bind('<Button-1>', del_cmd)
        
        if is_sent:
            status = "✔️" if is_read else "📩"
            tk.Label(info, text=status, font=('Arial', 8), bg=container['bg'], fg='gray').pack(side=tk.RIGHT, padx=(0, 5))
    
    # ========== ACTIONS ==========
    def view_user_profile(self, username):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Profil de {username}")
        dialog.geometry("380x460")
        dialog.configure(bg='#f0f2f5')
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.after(50, dialog.grab_set)

        header = tk.Frame(dialog, bg='#075E54', height=130)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        photo_preview = tk.Label(header, bg='#075E54', fg='white', font=('Arial', 36))
        photo_preview.place(relx=0.5, y=45, anchor='center')

        tk.Label(header, text=username, font=('Arial', 18, 'bold'),
                bg='#075E54', fg='white').place(relx=0.5, y=95, anchor='center')

        status_lbl = tk.Label(header, text="", font=('Arial', 9),
                             bg='#075E54', fg='#a8e6cf')
        status_lbl.place(relx=0.5, y=118, anchor='center')

        card = tk.Frame(dialog, bg='white', bd=0, highlightbackground='#e0e0e0',
                       highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True, padx=15, pady=(15, 10))

        info_lbl = tk.Label(card, text="Chargement...", font=('Arial', 11),
                           bg='white', fg='#555', justify=tk.CENTER)
        info_lbl.pack(expand=True, padx=20, pady=30)

        profile_data = []

        def on_response(data):
            if data.get('login') == username:
                profile_data.append(data)

        self._profile_callbacks.append(on_response)

        def cleanup():
            if on_response in self._profile_callbacks:
                self._profile_callbacks.remove(on_response)
        dialog.protocol("WM_DELETE_WINDOW", lambda: (cleanup(), dialog.destroy()))

        try:
            self.socket.send(f"GET_PROFILE {username}\n".encode())
        except:
            pass

        def check():
            if profile_data:
                data = profile_data[0]
                photo_val = (data.get('photo') or '').strip()
                username_online = username in self.online_users

                loaded = False
                if photo_val:
                    try:
                        raw = bytes.fromhex(photo_val)
                        if len(raw) > 50:
                            img = self._load_circle_from_bytes(raw, 70)
                            if img:
                                photo_preview.config(image=img, bg='#075E54')
                                photo_preview.image = img
                                loaded = True
                    except:
                        pass
                    if not loaded and os.path.isfile(photo_val):
                        img = self._load_circle_photo(photo_val, 70)
                        if img:
                            photo_preview.config(image=img, bg='#075E54')
                            photo_preview.image = img
                            loaded = True
                if not loaded:
                    photo_preview.config(text='👤', bg='#075E54')

                status_lbl.config(
                    text="● En ligne" if username_online else "○ Hors ligne",
                    fg='#a8e6cf' if username_online else '#ccc'
                )

                items = []
                bio = (data.get('bio') or '').strip()
                phone = (data.get('phone') or '').strip()
                email = (data.get('email') or '').strip()
                address = (data.get('address') or '').strip()
                education = (data.get('education') or '').strip()
                work = (data.get('work') or '').strip()

                if bio: items.append(('📝', bio))
                if phone: items.append(('📞', phone))
                if email: items.append(('✉', email))
                if address: items.append(('📍', address))
                if education: items.append(('🎓', education))
                if work: items.append(('💼', work))

                if items:
                    lines = []
                    for icon, val in items:
                        lines.append(f"{icon}  {val}")
                    info_lbl.config(text='\n\n'.join(lines), justify=tk.LEFT)
                else:
                    info_lbl.config(
                        text="(aucune information)",
                        fg='#999', font=('Arial', 11, 'italic')
                    )
            else:
                dialog.after(100, check)

        dialog.after(100, check)

    def refresh(self):
        if self.connected and self.authenticated:
            try:
                self.socket.send("ALLUSERS\n".encode())
                self.socket.send("USERS\n".encode())
                self.socket.send("LIST\n".encode())
                self.socket.send("LIST_GROUPS\n".encode())
            except:
                pass
    
    def on_typing(self, event=None):
        if not self.current_conv or not self.connected:
            return
        content = self.input_text.get("1.0", tk.END).strip()
        if not content:
            self.stop_typing()
            return
        try:
            if self.current_conv.startswith('📢 '):
                gname = self.current_conv[2:].strip()
                gid = None
                for id_, n in self.groups.items():
                    if n == gname:
                        gid = id_
                        break
                if gid:
                    self.socket.send(f"GROUP_TYPING {gid}\n".encode())
            else:
                self.socket.send(f"TYPING {self.current_conv}\n".encode())
        except:
            pass
        self.last_typing_time = time.time()
        if self.typing_timer:
            self.root.after_cancel(self.typing_timer)
        self.typing_timer = self.root.after(2000, self.stop_typing)
    
    def stop_typing(self):
        if self.current_conv and self.connected:
            try:
                if self.current_conv.startswith('📢 '):
                    gname = self.current_conv[2:].strip()
                    gid = None
                    for id_, n in self.groups.items():
                        if n == gname:
                            gid = id_
                            break
                    if gid:
                        self.socket.send(f"GROUP_STOP_TYPING {gid}\n".encode())
                else:
                    self.socket.send(f"STOP_TYPING {self.current_conv}\n".encode())
            except:
                pass
        self.typing_timer = None

    def show_typing_group(self):
        if self.current_conv and self.current_conv.startswith('📢 '):
            self.typing_label.config(text="✏️ Quelqu'un écrit...")
    
    def show_typing(self, sender):
        if sender == self.current_conv and not self.current_conv.startswith('📢 '):
            self.typing_label.config(text=f"✏️ {sender} tape...")
    
    def hide_typing(self):
        self.typing_label.config(text="")
    
    def send_file(self):
        if not self.current_conv:
            messagebox.showinfo("Info", "Sélectionnez d'abord un utilisateur")
            return
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="Choisir un fichier")
        if not path:
            return
        try:
            with open(path, 'rb') as f:
                data = f.read()
            filename = path.split('/')[-1]
            hex_data = data.hex()
            if self.current_conv.startswith('📢 '):
                gname = self.current_conv[2:].strip()
                gid = None
                for id_, n in self.groups.items():
                    if n == gname:
                        gid = id_
                        break
                if gid:
                    self.socket.sendall(f"GROUP_FILE {gid} {filename} {hex_data}\n".encode())
                    messagebox.showinfo("📁 Transfert", f"Fichier envoyé au groupe")
                else:
                    messagebox.showerror("Erreur", "Groupe introuvable")
            else:
                self.socket.sendall(f"FILE {self.current_conv} {filename} {hex_data}\n".encode())
                messagebox.showinfo("📁 Transfert", f"Fichier envoyé à {self.current_conv}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur fichier: {e}")
    
    def _open_saved(self, filename):
        filepath = f"received_files/{filename}"
        if os.path.exists(filepath):
            try:
                import subprocess
                subprocess.Popen(['xdg-open', filepath])
            except Exception as e:
                messagebox.showerror("Erreur",
                    f"Impossible d'ouvrir {filename}\n\nLe fichier est bien téléchargé :\n{os.path.abspath(filepath)}\n\nOuvrez-le manuellement depuis ce dossier.")
        else:
            messagebox.showerror("Erreur", f"Fichier {filename} introuvable")

    def open_file(self, filename):
        filepath = f"received_files/{filename}"
        if os.path.exists(filepath):
            self._open_saved(filename)
        else:
            try:
                self._pending_file = filename
                self.download_label.config(text=f"⏳ Téléchargement de {filename}...")
                self.socket.sendall(f"GET_FILE {filename}\n".encode())
            except:
                self.download_label.config(text="")
                messagebox.showerror("Erreur", "Impossible de télécharger le fichier")
    
    def send_message(self):
        if not self.current_conv:
            messagebox.showinfo("Info", "Sélectionnez d'abord un utilisateur")
            return
        
        content = self.input_text.get("1.0", tk.END).strip()
        if not content:
            return
        
        try:
            if self.current_conv.startswith('📢 '):
                gname = self.current_conv[2:].strip()
                gid = None
                for id_, n in self.groups.items():
                    if n == gname:
                        gid = id_
                        break
                if gid:
                    self.socket.send(f"GROUP_SEND {gid} {content}\n".encode())
                else:
                    messagebox.showerror("Erreur", "Groupe introuvable")
                    return
            else:
                self.socket.send(f"SEND {self.current_conv} {content}\n".encode())
            self.input_text.delete("1.0", tk.END)
            self.stop_typing()
            self.root.after(300, self.refresh)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {e}")
    
    def delete_message(self, msg_id=None, group=False):
        if msg_id is None:
            return
        if not messagebox.askyesno("🗑️ Supprimer", "Supprimer ce message ?\nCette action est irréversible."):
            return
        try:
            if group or (self.current_conv and self.current_conv.startswith('📢 ')):
                self.socket.send(f"GROUP_DELETE {msg_id}\n".encode())
            else:
                self.socket.send(f"DELETE {msg_id}\n".encode())
            self.root.after(300, self.refresh)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {e}")
    
    # ========== GROUPES ==========
    def update_groups_list(self):
        self.grp_listbox.delete(0, tk.END)
        for gid, gname in self.groups.items():
            self.grp_listbox.insert(tk.END, f"📢 {gname}")
        if not self.groups:
            self.grp_listbox.insert(tk.END, "Aucun groupe")
    
    def on_group_selected(self, event):
        selection = self.grp_listbox.curselection()
        if selection:
            name = self.grp_listbox.get(selection[0])
            if name == "Aucun groupe":
                return
            gid = None
            for id_, n in self.groups.items():
                if f"📢 {n}" == name:
                    gid = id_
                    break
            self.set_current_conv(f"📢 {self.groups[gid]}")
    
    def create_group_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Nouveau groupe")
        dialog.geometry("350x200")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.after(50, dialog.grab_set)
        
        tk.Label(dialog, text="Créer un groupe", font=('Arial', 14, 'bold'),
                bg='white', fg='#075E54').pack(pady=(20, 10))
        tk.Label(dialog, text="Nom du groupe:", bg='white').pack()
        entry = tk.Entry(dialog, font=('Arial', 12), bg='#f5f5f5', relief=tk.FLAT)
        entry.pack(pady=10, padx=30, fill=tk.X, ipady=4)
        entry.focus()
        
        def confirm():
            name = entry.get().strip()
            if name:
                try:
                    self.socket.send(f"CREATE_GROUP {name}\n".encode())
                    self.root.after(500, self.refresh)
                    dialog.destroy()
                    messagebox.showinfo("✅ Succès", f"Groupe '{name}' créé")
                except:
                    messagebox.showerror("Erreur", "Erreur réseau")
            else:
                messagebox.showerror("Erreur", "Nom invalide")
        
        tk.Button(dialog, text="✅ CRÉER", command=confirm,
                 bg='#25D366', fg='white', font=('Arial', 11, 'bold'),
                 relief=tk.FLAT).pack(pady=10, padx=30, fill=tk.X)
        entry.bind('<Return>', lambda e: confirm())
    
    def add_member_dialog(self):
        if not self.current_conv or not self.current_conv.startswith('📢 '):
            messagebox.showinfo("Info", "Sélectionnez d'abord un groupe")
            return
        gname = self.current_conv[2:].strip()
        gid = None
        for id_, n in self.groups.items():
            if n == gname:
                gid = id_
                break
        if not gid:
            messagebox.showerror("Erreur", "Groupe introuvable")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Ajouter un membre")
        dialog.geometry("400x350")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.after(50, dialog.grab_set)
        
        tk.Label(dialog, text=f"Ajouter à '{gname}'", font=('Arial', 14, 'bold'),
                bg='white', fg='#075E54').pack(pady=(15, 5))
        
        loading = tk.Label(dialog, text="⏳ Chargement des membres...", font=('Arial', 11),
                          bg='white', fg='gray')
        loading.pack(pady=20)
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(dialog, textvariable=search_var, font=('Arial', 11),
                               bg='#f5f5f5', relief=tk.FLAT)
        list_frame = tk.Frame(dialog, bg='white')
        scrollbar = tk.Scrollbar(list_frame)
        listbox = tk.Listbox(list_frame, font=('Arial', 11), relief=tk.FLAT,
                            bg='white', selectbackground='#25D366', selectforeground='white',
                            yscrollcommand=scrollbar.set)
        
        def populate_listbox():
            loading.pack_forget()
            search_entry.pack(pady=5, padx=20, fill=tk.X, ipady=3)
            search_entry.insert(0, "🔍 Rechercher...")
            search_entry.bind('<FocusIn>', lambda e: search_entry.delete(0, tk.END) if search_entry.get() == "🔍 Rechercher..." else None)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
            scrollbar.config(command=listbox.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            listbox.pack(fill=tk.BOTH, expand=True)
            
            excluded = set()
            if hasattr(self, '_group_members') and gid in self._group_members:
                excluded = set(self._group_members[gid])
            excluded.add(self.username)
            
            all_users.clear()
            all_users.extend(sorted([u for u in self.all_users if u not in excluded]))
            for u in all_users:
                listbox.insert(tk.END, u)
        
        all_users = []
        
        def wait_members():
            if hasattr(self, '_group_members') and gid in self._group_members:
                populate_listbox()
            else:
                try:
                    self._pending_members_gid = gid
                    self.socket.send(f"GROUP_MEMBERS {gid}\n".encode())
                except:
                    pass
                dialog.after(500, wait_members)
        
        search_var.trace('w', lambda *args: self._filter_listbox(search_var, listbox, all_users))
        
        def confirm():
            sel = listbox.curselection()
            if sel:
                user = listbox.get(sel[0])
                try:
                    self.socket.send(f"ADD_TO_GROUP {gid} {user}\n".encode())
                    self.root.after(500, self.refresh)
                    dialog.destroy()
                except:
                    messagebox.showerror("Erreur", "Erreur réseau")
        
        tk.Button(dialog, text="✅ AJOUTER", command=confirm,
                 bg='#25D366', fg='white', font=('Arial', 11, 'bold'),
                 relief=tk.FLAT).pack(pady=10, padx=20, fill=tk.X)
        listbox.bind('<Double-Button-1>', lambda e: confirm())
        
        # Démarrer le chargement
        try:
            self._pending_members_gid = gid
            self.socket.send(f"GROUP_MEMBERS {gid}\n".encode())
        except:
            pass
        dialog.after(300, wait_members)
    
    def show_group_members_dialog(self, gid):
        gname = self.groups.get(gid, "?")
        is_owner = hasattr(self, '_owned_groups') and gid in self._owned_groups
        self._pending_members_gid = gid
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Membres - {gname}")
        dialog.geometry("350x400")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.after(50, dialog.grab_set)
        
        tk.Label(dialog, text=f"👥 Membres de '{gname}'", font=('Arial', 14, 'bold'),
                bg='white', fg='#075E54').pack(pady=(15, 10))
        
        loading = tk.Label(dialog, text="⏳ Chargement...", font=('Arial', 11),
                          bg='white', fg='gray')
        loading.pack(pady=20)
        
        member_frame = tk.Frame(dialog, bg='white')
        member_frame.pack_forget()
        
        def refresh_members():
            if hasattr(self, '_group_members') and gid in self._group_members:
                members = self._group_members[gid]
                loading.pack_forget()
                # Supprimer les anciens widgets de membres
                for w in member_frame.winfo_children():
                    w.destroy()
                member_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
                for m in members:
                    row = tk.Frame(member_frame, bg='white')
                    row.pack(fill=tk.X, pady=2)
                    if m == self.username:
                        tk.Label(row, text=f"👑 {m} (moi)", font=('Arial', 11),
                                bg='white', fg='#075E54', anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)
                    else:
                        tk.Label(row, text=f"{m}", font=('Arial', 11),
                                bg='white', anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)
                        if is_owner:
                            tk.Button(row, text="❌", font=('Arial', 9),
                                     bg='#e74c3c', fg='white', relief=tk.FLAT,
                                     command=lambda u=m: self.kick_member(gid, gname, u, dialog)).pack(side=tk.RIGHT, padx=2)
            else:
                try:
                    self.socket.send(f"GROUP_MEMBERS {gid}\n".encode())
                except:
                    pass
                dialog.after(1000, refresh_members)
        
        try:
            self.socket.send(f"GROUP_MEMBERS {gid}\n".encode())
        except:
            pass
        dialog.after(500, refresh_members)
        
        tk.Button(dialog, text="✅ FERMER", command=dialog.destroy,
                 bg='#25D366', fg='white', font=('Arial', 11, 'bold'),
                 relief=tk.FLAT).pack(pady=10, padx=20, fill=tk.X)
    
    def delete_group_confirm(self):
        if not self.current_conv or not self.current_conv.startswith('📢 '):
            return
        gname = self.current_conv[2:].strip()
        gid = None
        for id_, n in self.groups.items():
            if n == gname:
                gid = id_
                break
        if not gid:
            return
        if messagebox.askyesno("🗑️ Supprimer le groupe",
                              f"Supprimer définitivement '{gname}' ?\nCette action est irréversible."):
            try:
                self.socket.send(f"DELETE_GROUP {gid}\n".encode())
                messagebox.showinfo("✅ Succès", f"Groupe '{gname}' supprimé")
                self.current_conv = None
                self.current_conv_key = None
                self.chat_label.config(text="Sélectionnez un utilisateur")
                self.online_label.config(text="")
                self.typing_label.config(text="")
                self.root.after(500, self.refresh)
            except:
                messagebox.showerror("Erreur", "Erreur réseau")

    def leave_group_confirm(self, gid):
        gname = self.groups.get(gid, "?")
        if messagebox.askyesno("🚪 Quitter le groupe",
                              f"Quitter '{gname}' ?"):
            try:
                self.socket.send(f"LEAVE_GROUP {gid}\n".encode())
                messagebox.showinfo("✅ Succès", f"Vous avez quitté '{gname}'")
                if gid in self.groups:
                    del self.groups[gid]
                self.current_conv = None
                self.current_conv_key = None
                self.chat_label.config(text="Sélectionnez un utilisateur")
                self.online_label.config(text="")
                self.typing_label.config(text="")
                self.root.after(500, self.refresh)
            except:
                messagebox.showerror("Erreur", "Erreur réseau")

    def _filter_listbox(self, search_var, listbox, all_users):
        q = search_var.get().lower()
        listbox.delete(0, tk.END)
        for u in all_users:
            if q in u.lower():
                listbox.insert(tk.END, u)
    
    def kick_member(self, gid, gname, target, dialog):
        if messagebox.askyesno("❌ Retirer un membre",
                              f"Retirer '{target}' du groupe '{gname}' ?"):
            try:
                self.socket.send(f"REMOVE_FROM_GROUP {gid} {target}\n".encode())
                dialog.destroy()
            except:
                messagebox.showerror("Erreur", "Erreur réseau")

    
    def on_enter(self, event):
        if not event.state & 0x1:
            self.send_message()
            return "break"
        return None
    
    def do_logout(self):
        if messagebox.askyesno("Déconnexion", "Voulez-vous vous déconnecter ?"):
            self.running = False
            self.connected = False
            self.authenticated = False
            if self.socket:
                try:
                    self.socket.send("QUIT\n".encode())
                    self.socket.settimeout(0.5)
                    self.socket.close()
                except:
                    pass
            self.chat_frame.destroy()
            self.setup_login()
            self.status.config(text="Déconnecté", fg='orange')
    
    def quit_app(self):
        self.running = False
        if self.socket:
            try:
                self.socket.send("QUIT\n".encode())
                self.socket.close()
            except:
                pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()