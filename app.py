from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)


# --- FUNÇÕES DE APOIO (Lidam com os arquivos de dados) ---

def carregar_dados(arquivo):
    """Lê o arquivo JSON. Se não existir ou estiver corrompido, retorna uma lista vazia."""
    if not os.path.exists(arquivo):
        return []
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def salvar_dados(arquivo, dados):
    """Salva a lista no arquivo JSON de forma organizada."""
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


# --- ROTAS DO SISTEMA ---

# 1. PÁGINA DE VENDAS (HOME)
@app.route("/", methods=["GET", "POST"])
def vendas():
    vendas_lista = carregar_dados("vendas.json")

    if request.method == "POST":
        nova_venda = {
            "cliente": request.form.get("cliente"),
            "produto": request.form.get("produto"),
            "valor": float(request.form.get("valor") or 0),
            "data": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        vendas_lista.append(nova_venda)
        salvar_dados("vendas.json", vendas_lista)
        return redirect(url_for('vendas'))

    total = sum(v.get("valor", 0) for v in vendas_lista)
    return render_template("vendas.html", vendas=vendas_lista, total=round(total, 2))


@app.route("/excluir_venda/<int:indice>", methods=["POST"])
def excluir_venda(indice):
    vendas_lista = carregar_dados("vendas.json")
    if 0 <= indice < len(vendas_lista):
        vendas_lista.pop(indice)
        salvar_dados("vendas.json", vendas_lista)
    return redirect(url_for('vendas'))


# 2. PÁGINA DE ENCOMENDAS (PEDIDOS)
@app.route("/encomendas", methods=["GET", "POST"])
def encomendas():
    encomendas_lista = carregar_dados("encomendas.json")

    if request.method == "POST":
        nova_encomenda = {
            "cliente": request.form.get("cliente"),
            "item": request.form.get("item"),
            "prazo": request.form.get("prazo")
        }
        encomendas_lista.append(nova_encomenda)
        salvar_dados("encomendas.json", encomendas_lista)
        return redirect(url_for('encomendas'))

    return render_template("encomendas.html", encomendas=encomendas_lista)


@app.route("/excluir_encomenda/<int:indice>", methods=["POST"])
def excluir_encomenda(indice):
    encomendas_lista = carregar_dados("encomendas.json")
    if 0 <= indice < len(encomendas_lista):
        encomendas_lista.pop(indice)
        salvar_dados("encomendas.json", encomendas_lista)
    return redirect(url_for('encomendas'))


# 3. PÁGINA FINANCEIRA (LUCRO)
@app.route("/financeiro", methods=["GET", "POST"])
def financeiro():
    gastos_lista = carregar_dados("gastos.json")
    vendas_lista = carregar_dados("vendas.json")

    if request.method == "POST":
        novo_gasto = {
            "item": request.form.get("item"),
            "valor": float(request.form.get("valor") or 0),
            "data": datetime.now().strftime("%d/%m/%Y")
        }
        gastos_lista.append(novo_gasto)
        salvar_dados("gastos.json", gastos_lista)
        return redirect(url_for('financeiro'))

    # Cálculos seguros (evitam erro se a lista estiver vazia ou com dados ruins)
    total_vendas = sum(float(v.get("valor", 0)) for v in vendas_lista)
    total_gastos = sum(float(g.get("valor", 0)) for g in gastos_lista)
    lucro_real = total_vendas - total_gastos

    return render_template("financeiro.html",
                           gastos=gastos_lista,
                           total_vendas=round(total_vendas, 2),
                           total_gastos=round(total_gastos, 2),
                           lucro=round(lucro_real, 2))


# 4. PÁGINA DA CALCULADORA
@app.route("/calculadora")
def calculadora():
    return render_template("calculadora.html")


# 5. PÁGINA DE AJUDA
@app.route("/ajuda")
def ajuda():
    return render_template("ajuda.html")

@app.route("/excluir_gasto/<int:indice>", methods=["POST"])
def excluir_gasto(indice):
    gastos_lista = carregar_dados("gastos.json")
    if 0 <= indice < len(gastos_lista):
        gastos_lista.pop(indice)
        salvar_dados("gastos.json", gastos_lista)
    return redirect(url_for('financeiro'))


# --- INICIALIZAÇÃO ---

if __name__ == "__main__":
    app.run(debug=True)