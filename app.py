from flask import Flask, render_template, request, redirect
import json
from datetime import datetime

app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def vendas():

    try:
        with open("vendas.json", "r") as f:
            vendas = json.load(f)
    except Exception:   # 👈 corrigido
        vendas = []     # 👈 corrigido

    if request.method == "POST":

        cliente = request.form["cliente"]
        produto = request.form["produto"]
        valor = float(request.form["valor"])

        venda = {
            "cliente": cliente,
            "produto": produto,
            "valor": valor,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        vendas.append(venda)  # 👉 adiciona na lista

        with open("vendas.json", "w") as f:
            json.dump(vendas, f, indent=4)  # 👉 salva no arquivo

        return redirect("/")  # 👉 recarrega página
    total = sum(v["valor"] for v in vendas)
    return render_template("vendas.html", vendas=vendas, total=total)

@app.route("/excluir_venda/<int:indice>")
def excluir_venda(indice):

    try:
        with open("vendas.json", "r") as f:
            vendas = json.load(f)
    except Exception:
        vendas = []

    if 0 <= indice < len(vendas):
        vendas.pop(indice)

    with open("vendas.json", "w") as f:
        json.dump(vendas, f, indent=4)

    return redirect("/")

@app.route("/encomendas", methods=["GET", "POST"])
def encomendas():

    try:
        with open("encomendas.json", "r") as f:
            encomendas = json.load(f)
    except Exception:
        encomendas = []

    if request.method == "POST":

        cliente = request.form["cliente"]
        produto = request.form["produto"]
        descricao = request.form["descricao"]

        encomenda = {
            "cliente": cliente,
            "produto": produto,
            "descricao": descricao,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        encomendas.append(encomenda)

        with open("encomendas.json", "w") as f:
            json.dump(encomendas, f, indent=4)

        return redirect("/encomendas")

    return render_template("encomendas.html", encomendas=encomendas)

@app.route("/excluir_encomenda/<int:indice>")


def excluir_encomenda(indice):

    try:
        with open("encomendas.json", "r") as f:
            encomendas = json.load(f)
    except Exception:
        encomendas = []

    if 0 <= indice < len(encomendas):
        encomendas.pop(indice)

    with open("encomendas.json", "w") as f:
        json.dump(encomendas, f, indent=4)

    return redirect("/encomendas")

if __name__ == "__main__":
    app.run(debug=True)