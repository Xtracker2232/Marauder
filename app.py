from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from datetime import datetime
import hashlib

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_key_123')

# ─── BASE DE DONNÉES ──────────────────────────────────

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marauder.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ─── MODÈLES ──────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─── ROUTES ──────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"🔍 Tentative de connexion: {username}")
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            print(f"👤 Utilisateur trouvé: {user.username}")
            print(f"🔑 Mot de passe stocké: {user.password}")
            print(f"🔑 Mot de passe saisi: {hashlib.sha256(password.encode()).hexdigest()}")
        
        if user and hashlib.sha256(password.encode()).hexdigest() == user.password:
            login_user(user)
            print(f"✅ Connexion réussie: {username}")
            return redirect(url_for('dashboard'))
        
        print(f"❌ Échec de connexion: {username}")
        flash('Pseudo ou mot de passe incorrect', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"📝 Tentative d'inscription: {username}")
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"❌ Pseudo déjà pris: {username}")
            flash('Ce pseudo est déjà pris', 'error')
            return redirect(url_for('register'))
        
        # Créer l'utilisateur
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = User(
            username=username,
            password=hashed_password
        )
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ Inscription réussie: {username}")
        print(f"🔑 Mot de passe hashé: {hashed_password}")
        
        flash('Inscription réussie ! Connectez-vous', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard</title>
        <style>
            body {{
                background: #0a0a0a;
                color: #fff;
                font-family: sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                flex-direction: column;
                gap: 20px;
            }}
            h1 {{ font-size: 32px; }}
            a {{ color: #fff; text-decoration: none; padding: 10px 20px; border: 1px solid #333; border-radius: 8px; }}
            a:hover {{ background: #1a1a1a; }}
            .info {{ color: #666; font-size: 14px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h1>Bienvenue {current_user.username} !</h1>
        <a href="/logout">Déconnexion</a>
        <div class="info">ID: {current_user.id} · Créé le: {current_user.created_at}</div>
    </body>
    </html>
    """

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ─── VÉRIFICATION DE LA BASE DE DONNÉES ──────────────

@app.route('/debug/users')
def debug_users():
    users = User.query.all()
    html = "<h1>Utilisateurs dans la base</h1><ul>"
    for u in users:
        html += f"<li>ID: {u.id} - Pseudo: {u.username} - Hash: {u.password[:20]}...</li>"
    html += f"</ul><p>Total: {len(users)} utilisateur(s)</p>"
    html += '<a href="/">Retour</a>'
    return html

# ─── LANCEMENT ──────────────────────────────────

with app.app_context():
    try:
        db.create_all()
        print("✅ Tables créées avec succès")
        print(f"📁 DATABASE: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Vérifier si la table existe
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables existantes: {tables}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)