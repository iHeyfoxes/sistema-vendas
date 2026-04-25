from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

# --- APP ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'chave-secreta-de-teste'

# --- EMAIL ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'kngb1981@gmail.com'
app.config['MAIL_PASSWORD'] = 'bpvkeblociyejyku'
app.config['MAIL_DEFAULT_SENDER'] = 'kngb1981@gmail.com'

# --- BANCO ---
uri = os.environ.get("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///novo_banco_pro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
mail = Mail(app)

# 🔐 TOKEN
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# --- LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- MODELOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)

    vendas = db.relationship('Venda', backref='dono', lazy=True)
    encomendas = db.relationship('Encomenda', backref='dono', lazy=True)
    gastos = db.relationship('Gasto', backref='dono', lazy=True)
    receitas = db.relationship('Receita', backref='dono', lazy=True)


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


class Receita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    link = db.Column(db.String(300))
    data = db.Column(db.String(20), default=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


with app.app_context():
    db.create_all()


# --- AUTH ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and check_password_hash(user.password, request.form.get("password")):
            login_user(user)
            return redirect(url_for('vendas'))
        flash("Usuário ou senha inválidos.")
    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        if User.query.filter_by(username=request.form.get("username")).first():
            flash("Usuário já existe.")
            return redirect(url_for('cadastro'))

        user = User(
            username=request.form.get("username"),
            email=request.form.get("email"),
            password=generate_password_hash(request.form.get("password"))
        )
        db.session.add(user)
        db.session.commit()

        flash("Cadastro realizado!")
        return redirect(url_for('login'))

    return render_template("cadastro.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# --- ESQUECI SENHA (COM TOKEN) ---
@app.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            token = serializer.dumps(email, salt='senha-reset')
            link = url_for('resetar_senha', token=token, _external=True)

            msg = Message("Recuperação de Senha", recipients=[email])
            msg.body = f"Clique no link para redefinir sua senha:\n{link}"
            mail.send(msg)

        flash("Se o e-mail existir, você receberá um link 📩")
        return redirect(url_for('login'))

    return render_template("esqueci_senha.html")


# --- RESET COM TOKEN ---
@app.route("/resetar-senha/<token>", methods=["GET", "POST"])
def resetar_senha(token):
    try:
        email = serializer.loads(token, salt='senha-reset', max_age=3600)
    except:
        flash("Link inválido ou expirado.")
        return redirect(url_for('login'))

    if request.method == "POST":
        nova = request.form.get("nova_senha")
        confirmar = request.form.get("confirmar_senha")

        if len(nova) < 6:
            flash("Mínimo 6 caracteres")
            return redirect(request.url)

        if nova != confirmar:
            flash("Senhas não coincidem")
            return redirect(request.url)

        user = User.query.filter_by(email=email).first()
        user.password = generate_password_hash(nova)
        db.session.commit()

        flash("Senha alterada com sucesso!")
        return redirect(url_for('login'))

    return render_template("reset_password_form.html")


# --- RECEITAS ---
@app.route("/receitas", methods=["GET", "POST"])
@login_required
def receitas():
    if request.method == "POST":
        receita = Receita(
            nome=request.form.get("nome"),
            link=request.form.get("link"),
            user_id=current_user.id
        )
        db.session.add(receita)
        db.session.commit()
        return redirect(url_for('receitas'))

    lista = Receita.query.filter_by(user_id=current_user.id).order_by(Receita.id.desc()).all()
    return render_template("receitas.html", receitas=lista)


@app.route("/excluir_receita/<int:id>", methods=["POST"])
@login_required
def excluir_receita(id):
    receita = db.session.get(Receita, id)
    if receita and receita.user_id == current_user.id:
        db.session.delete(receita)
        db.session.commit()
    return redirect(url_for('receitas'))


# --- HOME ---
@app.route("/")
@login_required
def vendas():
    return render_template("vendas.html")


if __name__ == "__main__":
    app.run(debug=True)