from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_mail import Mail, Message

# --- 1. CRIAÇÃO DO APP ---
app = Flask(__name__)

# O Render fornece a SECRET_KEY nas variáveis de ambiente.
# Se não houver, ele usa a de teste.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-secreta-de-teste-123')

# --- 2. CONFIGURAÇÃO DE E-MAIL ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'kngb1981@gmail.com'
# Puxa a senha SEM ESPAÇOS das configurações do Render
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('Sistema Amigurumi', 'kngb1981@gmail.com')

# --- 3. CONFIGURAÇÃO DO BANCO DE DADOS ---
uri = os.environ.get("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///novo_banco_pro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 4. INICIALIZAÇÃO DAS EXTENSÕES ---
db = SQLAlchemy(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- 5. MODELOS (Tabelas) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)
    vendas = db.relationship('Venda', backref='dono', lazy=True)
    encomendas = db.relationship('Encomenda', backref='dono', lazy=True)
    gastos = db.relationship('Gasto', backref='dono', lazy=True)

class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    produto = db.Column(db.String(100))
    valor = db.Column(db.Float, default=0.0)
    data = db.Column(db.String(20), default=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Encomenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    item = db.Column(db.String(100))
    prazo = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, default=0.0)
    data = db.Column(db.String(20), default=lambda: datetime.now().strftime("%d/%m/%Y"))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Criar o banco de dados se não existir
with app.app_context():
    db.create_all()

# --- 6. ROTAS ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('vendas'))
        flash("Usuário ou senha inválidos.")
    return render_template("login.html")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Este usuário já existe.")
            return redirect(url_for('cadastro'))
        hashed_password = generate_password_hash(password)
        novo_usuario = User(username=username, email=email, password=hashed_password)
        db.session.add(novo_usuario)
        db.session.commit()
        flash("Cadastro realizado! Agora faça login.")
        return redirect(url_for('login'))
    return render_template("cadastro.html")

@app.route("/")
@login_required
def vendas():
    vendas_lista = Venda.query.filter_by(user_id=current_user.id).order_by(Venda.id.desc()).all()
    total = sum(v.valor for v in vendas_lista)
    return render_template("vendas.html", vendas=vendas_lista, total=round(total, 2))

@app.route("/add_venda", methods=["POST"])
@login_required
def add_venda():
    nova_venda = Venda(
        cliente=request.form.get("cliente"),
        produto=request.form.get("produto"),
        valor=float(request.form.get("valor") or 0),
        user_id=current_user.id
    )
    db.session.add(nova_venda)
    db.session.commit()
    return redirect(url_for('vendas'))

@app.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        email_digitado = request.form.get("email")
        user = User.query.filter_by(email=email_digitado).first()
        if user:
            try:
                msg = Message("Recuperação de Senha", recipients=[email_digitado])
                link = url_for('resetar_senha', email=email_digitado, _external=True)
                msg.body = f"Olá {user.username}, clique no link para resetar sua senha: {link}"
                mail.send(msg)
                flash("E-mail enviado! Verifique sua caixa de entrada.")
                return redirect(url_for('login'))
            except Exception as e:
                flash(f"Erro ao enviar: {str(e)}")
        else:
            flash("E-mail não cadastrado.")
    return render_template("esqueci_senha.html")

@app.route("/resetar-senha/<email>", methods=["GET", "POST"])
def resetar_senha(email):
    if request.method == "POST":
        nova_senha = request.form.get("nova_senha")
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(nova_senha)
            db.session.commit()
            flash("Senha alterada com sucesso!")
            return redirect(url_for('login'))
    return render_template("reset_password_form.html", email=email)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Adicione aqui as rotas de encomendas, financeiro, etc. conforme seu código original

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)