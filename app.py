from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from datetime import datetime
import hashlib
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_key_123')

# ─── BASE DE DONNÉES ──────────────────────────────────

# Récupérer DATABASE_URL depuis Railway (ou .env)
DATABASE_URL = os.getenv('DATABASE_URL')

# Si on est sur Railway, DATABASE_URL est automatiquement fournie
# Sinon, on utilise SQLite en local
if DATABASE_URL:
    # Railway utilise postgres:// mais SQLAlchemy nécessite postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # En local, utiliser SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marauder.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ─── MODÈLES ──────────────────────────────────

class User(UserMixin, db.Model):
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
        
        if User.query.filter_by(username=username).first():
            flash('Ce pseudo est déjà pris', 'error')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            password=hashlib.sha256(password.encode()).hexdigest()
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Inscription réussie ! Connectez-vous', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return f"""
    <h1>Bienvenue {current_user.username} !</h1>
    <a href='/logout'>Déconnexion</a>
    """

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ─── LANCEMENT ──────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Base de données connectée")
        print(f"📁 DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)