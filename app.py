from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_mail import Mail, Message

# --- 1. CRIAÇÃO DO APP (DEVE SER O PRIMEIRO) ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'chave-secreta-de-teste'

# --- 2. CONFIGURAÇÃO DO SERVIDOR DE E-MAIL (BLINDADO) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'kngb1981@gmail.com'
# IMPORTANTE: Garanta que a senha abaixo não tenha espaços
app.config['MAIL_PASSWORD'] = 'upkoiemrutfhlpof'
app.config['MAIL_DEFAULT_SENDER'] = 'kngb1981@gmail.com'

# --- 3. CONFIGURAÇÃO DO BANCO DE DADOS ---
uri = os.environ.get("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///novo_banco_pro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 4. INICIALIZAÇÃO DAS EXTENSÕES ---
db = SQLAlchemy(app)
mail = Mail(app)  # Agora o Mail sabe quem é o app

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- 5. MODELOS (Tabelas do Banco) ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    # ADICIONADO: Campo email essencial para a recuperação de senha
    email = db.Column(db.String(150), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)

    vendas = db.relationship('Venda', backref='dono', lazy=True)
    encomendas = db.relationship('Encomenda', backref='dono', lazy=True)
    gastos = db.relationship('Gasto', backref='dono', lazy=True)
    receitas = db.relationship('Receita', backref='dono', lazy=True)


# (Classes Venda, Encomenda e Gasto permanecem iguais)
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


# Criar o banco
with app.app_context():
    db.create_all()


# --- 6. ROTAS DE AUTENTICAÇÃO ---

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
        email = request.form.get("email")  # Captura o e-mail novo
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


# --- AS OUTRAS ROTAS CONTINUAM IGUAIS ABAIXO ---
# (Vendas, Encomendas, Financeiro, Perfil, Esqueci-Senha, Resetar-Senha)
# ... mantenha o restante do seu código exatamente como você mandou ...

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/", methods=["GET", "POST"])
@login_required
def vendas():
    if request.method == "POST":
        nova_venda = Venda(
            cliente=request.form.get("cliente"),
            produto=request.form.get("produto"),
            valor=float(request.form.get("valor") or 0),
            user_id=current_user.id
        )
        db.session.add(nova_venda)
        db.session.commit()
        return redirect(url_for('vendas'))
    vendas_lista = Venda.query.filter_by(user_id=current_user.id).order_by(Venda.id.desc()).all()
    total = sum(v.valor for v in vendas_lista)
    return render_template("vendas.html", vendas=vendas_lista, total=round(total, 2))


@app.route("/excluir_venda/<int:id>", methods=["POST"])
@login_required
def excluir_venda(id):
    venda = db.session.get(Venda, id)
    if venda and venda.user_id == current_user.id:
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
    return render_template("financeiro.html", gastos=gastos_lista, total_vendas=round(total_vendas, 2),
                           total_gastos=round(total_gastos, 2), lucro=round(lucro_real, 2))


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
    return render_template("precos.html")


@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        senha_atual = request.form.get("senha_atual")
        nova_senha = request.form.get("nova_senha")
        if check_password_hash(current_user.password, senha_atual):
            current_user.password = generate_password_hash(nova_senha)
            db.session.commit()
            flash("Senha atualizada com sucesso!")
            return redirect(url_for('vendas'))
        else:
            flash("Senha atual incorreta. Tente novamente.")
    return render_template("perfil.html")


@app.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        email_digitado = request.form.get("email")
        print(f"DEBUG: O e-mail digitado foi: {email_digitado}")  # Aparece no terminal

        user = User.query.filter_by(email=email_digitado).first()

        if user:
            print(f"DEBUG: Usuário encontrado: {user.username}")
            try:
                msg = Message("Recuperação de Senha", recipients=[email_digitado])
                link = url_for('resetar_senha', email=email_digitado, _external=True)
                msg.body = f"Olá {user.username}, clique no link para resetar sua senha: {link}"

                mail.send(msg)
                print("DEBUG: E-mail enviado com sucesso!")
                flash("E-mail enviado! Verifique sua caixa de entrada.")
                return redirect(url_for('login'))
            except Exception as e:
                print(f"DEBUG ERRO DE ENVIO: {e}")
                flash(f"Erro técnico ao enviar: {str(e)}")
                return redirect(url_for('esqueci_senha'))
        else:
            print("DEBUG: E-mail não encontrado no banco de dados.")
            flash("E-mail não cadastrado.")
            return redirect(url_for('esqueci_senha'))

    return render_template("esqueci_senha.html")


@app.route("/resetar-senha/<email>", methods=["GET", "POST"])
def resetar_senha(email):
    if request.method == "POST":
        nova_senha = request.form.get("nova_senha")
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(nova_senha)
            db.session.commit()
            flash("Senha alterada!")
            return redirect(url_for('login'))
    return render_template("reset_password_form.html", email=email)

@app.route("/receitas", methods=["GET", "POST"])
@login_required
def receitas():

    if request.method == "POST":
        nova_receita = Receita(
            nome=request.form.get("nome"),
            link=request.form.get("link"),
            user_id=current_user.id
        )

        db.session.add(nova_receita)
        db.session.commit()

        return redirect(url_for('receitas'))

    receitas_lista = Receita.query\
        .filter_by(user_id=current_user.id)\
        .order_by(Receita.id.desc())\
        .all()

    return render_template("receitas.html", receitas=receitas_lista)


@app.route("/excluir_receita/<int:id>", methods=["POST"])
@login_required
def excluir_receita(id):

    receita = db.session.get(Receita, id)

    if receita and receita.user_id == current_user.id:
        db.session.delete(receita)
        db.session.commit()

    return redirect(url_for('receitas'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)