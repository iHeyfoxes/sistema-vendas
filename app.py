from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
# O Render fornece a URL em 'DATABASE_URL'.
# Se rodar localmente e não encontrar a variável, ele cria um arquivo 'amigurumi.db' (SQLite)
uri = os.environ.get("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///amigurumi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS (Tabelas do Banco) ---

class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    produto = db.Column(db.String(100))
    valor = db.Column(db.Float, default=0.0)
    data = db.Column(db.String(20), default=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))

class Encomenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    item = db.Column(db.String(100))
    prazo = db.Column(db.String(50))

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, default=0.0)
    data = db.Column(db.String(20), default=lambda: datetime.now().strftime("%d/%m/%Y"))

# Cria as tabelas no banco de dados automaticamente se elas não existirem
with app.app_context():
    db.create_all()

# --- ROTAS DO SISTEMA ---

# 1. PÁGINA DE VENDAS (HOME)
@app.route("/", methods=["GET", "POST"])
def vendas():
    if request.method == "POST":
        nova_venda = Venda(
            cliente=request.form.get("cliente"),
            produto=request.form.get("produto"),
            valor=float(request.form.get("valor") or 0)
        )
        db.session.add(nova_venda)
        db.session.commit()
        return redirect(url_for('vendas'))

    vendas_lista = Venda.query.order_by(Venda.id.desc()).all()
    total = sum(v.valor for v in vendas_lista)
    return render_template("vendas.html", vendas=vendas_lista, total=round(total, 2))

@app.route("/excluir_venda/<int:id>", methods=["POST"])
def excluir_venda(id):
    venda = Venda.query.get(id)
    if venda:
        db.session.delete(venda)
        db.session.commit()
    return redirect(url_for('vendas'))


# 2. PÁGINA DE ENCOMENDAS (PEDIDOS)
@app.route("/encomendas", methods=["GET", "POST"])
def encomendas():
    if request.method == "POST":
        nova_encomenda = Encomenda(
            cliente=request.form.get("cliente"),
            item=request.form.get("item"),
            prazo=request.form.get("prazo")
        )
        db.session.add(nova_encomenda)
        db.session.commit()
        return redirect(url_for('encomendas'))

    encomendas_lista = Encomenda.query.all()
    return render_template("encomendas.html", encomendas=encomendas_lista)

@app.route("/excluir_encomenda/<int:id>", methods=["POST"])
def excluir_encomenda(id):
    encomenda = Encomenda.query.get(id)
    if encomenda:
        db.session.delete(encomenda)
        db.session.commit()
    return redirect(url_for('encomendas'))


# 3. PÁGINA FINANCEIRA (LUCRO)
@app.route("/financeiro", methods=["GET", "POST"])
def financeiro():
    if request.method == "POST":
        novo_gasto = Gasto(
            item=request.form.get("item"),
            valor=float(request.form.get("valor") or 0)
        )
        db.session.add(novo_gasto)
        db.session.commit()
        return redirect(url_for('financeiro'))

    gastos_lista = Gasto.query.order_by(Gasto.id.desc()).all()
    vendas_lista = Venda.query.all()

    total_vendas = sum(v.valor for v in vendas_lista)
    total_gastos = sum(g.valor for g in gastos_lista)
    lucro_real = total_vendas - total_gastos

    return render_template("financeiro.html",
                           gastos=gastos_lista,
                           total_vendas=round(total_vendas, 2),
                           total_gastos=round(total_gastos, 2),
                           lucro=round(lucro_real, 2))

@app.route("/excluir_gasto/<int:id>", methods=["POST"])
def excluir_gasto(id):
    gasto = Gasto.query.get(id)
    if gasto:
        db.session.delete(gasto)
        db.session.commit()
    return redirect(url_for('financeiro'))


# 4. PÁGINA DA CALCULADORA
@app.route("/calculadora")
def calculadora():
    return render_template("calculadora.html")


# 5. PÁGINA DE AJUDA
@app.route("/ajuda")
def ajuda():
    return render_template("ajuda.html")


if __name__ == "__main__":
    app.run(debug=True)