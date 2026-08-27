from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import hashlib

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'marauder_secret_key_2025')

# Configuration base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marauder.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ─── MODÈLES ──────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    plan = db.Column(db.String(20), default='hunter')  # hunter, tracker, predator
    searches_today = db.Column(db.Integer, default=0)
    last_search_date = db.Column(db.String(10), default='')

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(500), nullable=False)
    results_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Créer la base de données
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Configuration API
BRIX_KEY = os.getenv('BRIX_KEY')
BRIX_API_URL = "https://api.brixhub.to/api/v1"

# ─── ROUTES ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            if hashlib.sha256(password.encode()).hexdigest() == user.password:
                login_user(user)
                return redirect(url_for('dashboard'))
        
        flash('Email ou mot de passe incorrect', 'error')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur est déjà pris', 'error')
            return redirect(url_for('register'))
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            plan='hunter'
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Inscription réussie ! Connectez-vous', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    history = SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.created_at.desc()).limit(10).all()
    
    # Calculer les limites selon le plan
    limits = {
        'hunter': 3,
        'tracker': 20,
        'predator': 100
    }
    max_searches = limits.get(current_user.plan, 3)
    remaining = max(0, max_searches - current_user.searches_today)
    
    return render_template('dashboard.html', 
                         user=current_user, 
                         history=history,
                         remaining=remaining,
                         max_searches=max_searches)

@app.route('/search', methods=['POST'])
@login_required
def search():
    # Vérifier les limites
    today = datetime.utcnow().strftime('%Y-%m-%d')
    if current_user.last_search_date != today:
        current_user.searches_today = 0
        current_user.last_search_date = today
        db.session.commit()
    
    limits = {
        'hunter': 3,
        'tracker': 20,
        'predator': 100
    }
    max_searches = limits.get(current_user.plan, 3)
    
    if current_user.searches_today >= max_searches:
        flash(f'Limite de {max_searches} recherches/jour atteinte', 'error')
        return redirect(url_for('dashboard'))
    
    # Récupérer les données
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    email = request.form.get('email', '').strip()
    telephone = request.form.get('telephone', '').strip()
    ville = request.form.get('ville', '').strip()
    
    # Construire la payload
    payload = {"flexible": True, "per_page": 10}
    query_parts = []
    
    if nom:
        payload["nom_famille"] = nom
        query_parts.append(f"Nom: {nom}")
    if prenom:
        payload["prenom"] = prenom
        query_parts.append(f"Prénom: {prenom}")
    if email:
        payload["email"] = email
        query_parts.append(f"Email: {email}")
    if telephone:
        payload["telephone"] = telephone
        query_parts.append(f"Tél: {telephone}")
    if ville:
        payload["ville"] = ville
        query_parts.append(f"Ville: {ville}")
    
    if not query_parts:
        flash('Remplissez au moins un champ', 'error')
        return redirect(url_for('dashboard'))
    
    # Appeler l'API
    headers = {
        "X-API-Key": BRIX_KEY,
        "Content-Type": "application/json",
        "User-Agent": "Marauder-Web/1.0"
    }
    
    try:
        response = requests.post(
            f"{BRIX_API_URL}/search",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', {}).get('results', [])
            total = data.get('meta', {}).get('total', 0)
            took = data.get('meta', {}).get('took_ms', 0)
            
            current_user.searches_today += 1
            db.session.commit()
            
            history = SearchHistory(
                user_id=current_user.id,
                query=" · ".join(query_parts),
                results_count=len(results)
            )
            db.session.add(history)
            db.session.commit()
            
            remaining = max_searches - current_user.searches_today
            
            return render_template('dashboard.html', 
                                 user=current_user,
                                 results=results,
                                 total=total,
                                 took=took,
                                 remaining=remaining,
                                 max_searches=max_searches,
                                 query=" · ".join(query_parts),
                                 history=SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.created_at.desc()).limit(10).all())
        else:
            flash(f'Erreur API: {response.status_code}', 'error')
            
    except requests.exceptions.Timeout:
        flash('L\'API met trop de temps à répondre', 'error')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ─── API INTERNE ──────────────────────────────────────────────────────────

@app.route('/api/search', methods=['POST'])
@login_required
def api_search():
    """API interne pour les appels AJAX"""
    data = request.get_json()
    
    # ... même logique que /search
    
    return jsonify({"status": "ok", "message": "Recherche effectuée"})

# ─── LANCEMENT ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)