from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'chave-secreta-de-teste'

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
uri = os.environ.get("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///amigurumi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- CONFIGURAÇÃO DO LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- MODELOS (Tabelas do Banco) ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # Relações: liga o usuário aos seus dados
    vendas = db.relationship('Venda', backref='dono', lazy=True)
    encomendas = db.relationship('Encomenda', backref='dono', lazy=True)
    gastos = db.relationship('Gasto', backref='dono', lazy=True)


class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    produto = db.Column(db.String(100))
    valor = db.Column(db.Float, default=0.0)
    data = db.Column(db.String(20), default=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Chave estrangeira


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


# Criar o banco
with app.app_context():
    db.create_all()


# --- ROTAS DE AUTENTICAÇÃO ---

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
        password = request.form.get("password")

        if User.query.filter_by(username=username).first():
            flash("Este usuário já existe.")
            return redirect(url_for('cadastro'))

        hashed_password = generate_password_hash(password)
        novo_usuario = User(username=username, password=hashed_password)
        db.session.add(novo_usuario)
        db.session.commit()
        flash("Cadastro realizado! Agora faça login.")
        return redirect(url_for('login'))
    return render_template("cadastro.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# --- ROTAS DO SISTEMA (PROTEGIDAS) ---

@app.route("/", methods=["GET", "POST"])
@login_required
def vendas():
    if request.method == "POST":
        nova_venda = Venda(
            cliente=request.form.get("cliente"),
            produto=request.form.get("produto"),
            valor=float(request.form.get("valor") or 0),
            user_id=current_user.id  # Salva quem é o dono da venda
        )
        db.session.add(nova_venda)
        db.session.commit()
        return redirect(url_for('vendas'))

    # Filtra apenas as vendas do usuário logado
    vendas_lista = Venda.query.filter_by(user_id=current_user.id).order_by(Venda.id.desc()).all()
    total = sum(v.valor for v in vendas_lista)
    return render_template("vendas.html", vendas=vendas_lista, total=round(total, 2))


@app.route("/excluir_venda/<int:id>", methods=["POST"])
@login_required
def excluir_venda(id):
    venda = db.session.get(Venda, id)
    if venda and venda.user_id == current_user.id:  # Só exclui se for o dono
        db.session.delete(venda)
        db.session.commit()
    return redirect(url_for('vendas'))


@app.route("/encomendas", methods=["GET", "POST"])
@login_required
def encomendas():
    if request.method == "POST":
        nova_encomenda = Encomenda(
            cliente=request.form.get("cliente"),
            item=request.form.get("item"),
            prazo=request.form.get("prazo"),
            user_id=current_user.id
        )
        db.session.add(nova_encomenda)
        db.session.commit()
        return redirect(url_for('encomendas'))

    encomendas_lista = Encomenda.query.filter_by(user_id=current_user.id).all()
    return render_template("encomendas.html", encomendas=encomendas_lista)


@app.route("/excluir_encomenda/<int:id>", methods=["POST"])
@login_required
def excluir_encomenda(id):
    encomenda = db.session.get(Encomenda, id)
    if encomenda and encomenda.user_id == current_user.id:
        db.session.delete(encomenda)
        db.session.commit()
    return redirect(url_for('encomendas'))


@app.route("/financeiro", methods=["GET", "POST"])
@login_required
def financeiro():
    if request.method == "POST":
        novo_gasto = Gasto(
            item=request.form.get("item"),
            valor=float(request.form.get("valor") or 0),
            user_id=current_user.id
        )
        db.session.add(novo_gasto)
        db.session.commit()
        return redirect(url_for('financeiro'))

    gastos_lista = Gasto.query.filter_by(user_id=current_user.id).order_by(Gasto.id.desc()).all()
    vendas_lista = Venda.query.filter_by(user_id=current_user.id).all()

    total_vendas = sum(v.valor for v in vendas_lista)
    total_gastos = sum(g.valor for g in gastos_lista)
    lucro_real = total_vendas - total_gastos

    return render_template("financeiro.html",
                           gastos=gastos_lista,
                           total_vendas=round(total_vendas, 2),
                           total_gastos=round(total_gastos, 2),
                           lucro=round(lucro_real, 2))


@app.route("/excluir_gasto/<int:id>", methods=["POST"])
@login_required
def excluir_gasto(id):
    gasto = db.session.get(Gasto, id)
    if gasto and gasto.user_id == current_user.id:
        db.session.delete(gasto)
        db.session.commit()
    return redirect(url_for('financeiro'))


@app.route("/calculadora")
@login_required
def calculadora():
    return render_template("calculadora.html")


@app.route("/ajuda")
@login_required
def ajuda():
    return render_template("ajuda.html")

@app.route("/precos")
@login_required
def precos():
    # Aqui você pode depois criar uma tabela no banco,
    # por enquanto ele apenas abrirá a página.
    return render_template("precos.html")


if __name__ == "__main__":
    app.run(debug=True)