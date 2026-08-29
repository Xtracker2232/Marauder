from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import os
import hashlib

app = Flask(__name__)
app.secret_key = 'ma_cle_secrete_123456789'

# Base de données SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marauder.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ─── MODÈLE ──────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─── ROUTES ──────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/health')
def health():
    return "OK", 200

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
        
        if User.query.filter_by(username=username).first():
            flash('Ce pseudo est déjà pris', 'error')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            password=hashlib.sha256(password.encode()).hexdigest()
        )
        db.session.add(user)
        db.session.commit()
        
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
    return redirect(url_for('login'))

# ─── LANCEMENT ──────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Base de données créée")
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)