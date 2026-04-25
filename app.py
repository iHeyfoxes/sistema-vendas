from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'chave-secreta-de-teste'

# EMAIL
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'kngb1981@gmail.com'
app.config['MAIL_PASSWORD'] = 'SUA_SENHA_AQUI'
app.config['MAIL_DEFAULT_SENDER'] = 'kngb1981@gmail.com'

# BANCO
uri = os.environ.get("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///novo_banco_pro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# MODELOS
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))


class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100))
    produto = db.Column(db.String(100))
    valor = db.Column(db.Float)
    data = db.Column(db.String(20), default=lambda: datetime.now().strftime("%d/%m/%Y"))
    user_id = db.Column(db.Integer)


class Encomenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100))
    item = db.Column(db.String(100))
    prazo = db.Column(db.String(50))
    user_id = db.Column(db.Integer)


class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(100))
    valor = db.Column(db.Float)
    user_id = db.Column(db.Integer)


class Receita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150))
    link = db.Column(db.String(300))
    user_id = db.Column(db.Integer)


with app.app_context():
    db.create_all()


# AUTH
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and check_password_hash(user.password, request.form.get("password")):
            login_user(user)
            return redirect(url_for("vendas"))
        flash("Login inválido")
    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        user = User(
            username=request.form.get("username"),
            email=request.form.get("email"),
            password=generate_password_hash(request.form.get("password"))
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("cadastro.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# VENDAS
@app.route("/", methods=["GET", "POST"])
@login_required
def vendas():
    if request.method == "POST":
        db.session.add(Venda(
            cliente=request.form.get("cliente"),
            produto=request.form.get("produto"),
            valor=float(request.form.get("valor") or 0),
            user_id=current_user.id
        ))
        db.session.commit()
        return redirect("/")

    vendas = Venda.query.filter_by(user_id=current_user.id).all()
    total = sum(v.valor for v in vendas)
    return render_template("vendas.html", vendas=vendas, total=total)


# ENCOMENDAS
@app.route("/encomendas", methods=["GET", "POST"])
@login_required
def encomendas():
    if request.method == "POST":
        db.session.add(Encomenda(
            cliente=request.form.get("cliente"),
            item=request.form.get("item"),
            prazo=request.form.get("prazo"),
            user_id=current_user.id
        ))
        db.session.commit()
        return redirect("/encomendas")

    encomendas = Encomenda.query.filter_by(user_id=current_user.id).all()
    return render_template("encomendas.html", encomendas=encomendas)


# FINANCEIRO
@app.route("/financeiro", methods=["GET", "POST"])
@login_required
def financeiro():
    if request.method == "POST":
        db.session.add(Gasto(
            item=request.form.get("item"),
            valor=float(request.form.get("valor") or 0),
            user_id=current_user.id
        ))
        db.session.commit()
        return redirect("/financeiro")

    gastos = Gasto.query.filter_by(user_id=current_user.id).all()
    vendas = Venda.query.filter_by(user_id=current_user.id).all()

    total_vendas = sum(v.valor for v in vendas)
    total_gastos = sum(g.valor for g in gastos)

    return render_template("financeiro.html",
                           gastos=gastos,
                           total_vendas=total_vendas,
                           total_gastos=total_gastos,
                           lucro=total_vendas - total_gastos
                           )


# RECEITAS
@app.route("/receitas", methods=["GET", "POST"])
@login_required
def receitas():
    if request.method == "POST":
        db.session.add(Receita(
            nome=request.form.get("nome"),
            link=request.form.get("link"),
            user_id=current_user.id
        ))
        db.session.commit()
        return redirect("/receitas")

    receitas = Receita.query.filter_by(user_id=current_user.id).all()
    return render_template("receitas.html", receitas=receitas)


@app.route("/excluir_receita/<int:id>", methods=["POST"])
@login_required
def excluir_receita(id):
    r = db.session.get(Receita, id)
    if r and r.user_id == current_user.id:
        db.session.delete(r)
        db.session.commit()
    return redirect("/receitas")


# OUTRAS
@app.route("/precos")
@login_required
def precos():
    return render_template("precos.html")


@app.route("/calculadora")
@login_required
def calculadora():
    return render_template("calculadora.html")


@app.route("/perfil")
@login_required
def perfil():
    return render_template("perfil.html")


# RESET SENHA
@app.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            msg = Message("Recuperação", recipients=[email])
            link = url_for("resetar_senha", email=email, _external=True)
            msg.body = f"Clique para resetar: {link}"
            mail.send(msg)

        flash("Se o e-mail existir, você receberá instruções.")
        return redirect("/login")

    return render_template("esqueci_senha.html")


@app.route("/resetar-senha/<email>", methods=["GET", "POST"])
def resetar_senha(email):
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
        if user:
            user.password = generate_password_hash(nova)
            db.session.commit()
            flash("Senha alterada")
            return redirect("/login")

    return render_template("reset_password_form.html")


# RUN
if __name__ == "__main__":
    app.run(debug=True)