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
        
        user = User.query.filter_by(username=username).first()
        if user and hashlib.sha256(password.encode()).hexdigest() == user.password:
            login_user(user)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Pseudo ou mot de passe incorrect', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Vérifier si l'utilisateur existe déjà
        if User.query.filter_by(username=username).first():
            flash('Ce pseudo est déjà pris', 'error')
            return redirect(url_for('register'))
        
        # Créer l'utilisateur
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = User(username=username, password=hashed_password)
        
        db.session.add(user)
        db.session.commit()
        
        # CONNEXION AUTOMATIQUE
        login_user(user)
        
        flash('Inscription réussie ! Bienvenue !', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnecté', 'success')
    return redirect(url_for('login'))

# ─── DEBUG ──────────────────────────────────

@app.route('/debug/db')
def debug_db():
    """Vérifier l'état de la base de données"""
    from sqlalchemy import inspect
    
    html = "<h1>🔍 Debug Base de données</h1>"
    
    # 1. Vérifier la connexion
    try:
        db.engine.connect()
        html += "<p>✅ Connexion à la base OK</p>"
    except Exception as e:
        html += f"<p>❌ Erreur de connexion: {e}</p>"
        return html
    
    # 2. Voir les tables existantes
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    html += f"<p>📋 Tables existantes: {tables}</p>"
    
    # 3. Voir les utilisateurs
    users = User.query.all()
    html += f"<p>👤 Nombre d'utilisateurs: {len(users)}</p>"
    
    if users:
        html += "<ul>"
        for u in users:
            html += f"<li>ID: {u.id} - Pseudo: {u.username} - Hash: {u.password[:20]}...</li>"
        html += "</ul>"
    else:
        html += "<p style='color:orange;'>⚠️ Aucun utilisateur trouvé</p>"
    
    html += '<br><a href="/">← Retour</a>'
    return html

# ─── CRÉATION DES TABLES ──────────────────────────────────

def init_db():
    """Créer les tables si elles n'existent pas"""
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tables créées avec succès")
            print(f"📁 DATABASE: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tables existantes: {tables}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la création des tables: {e}")

# ─── LANCEMENT ──────────────────────────────────

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
else:
    # Pour Gunicorn (Railway)
    init_db()