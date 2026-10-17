# -*- coding: utf-8 -*-
"""
Light for Youth - Caixa de Reclamações
Associação Jovem Visionário para a Promoção do Desenvolvimento Local
"""
import json
import os
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent


def carregar_env():
    """Lê o ficheiro .env (sem precisar de bibliotecas extra)."""
    env = BASE_DIR / ".env"
    if not env.exists():
        return
    for linha in env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


carregar_env()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mude-esta-chave")

CATEGORIAS = [
    "Ensino / Aulas",
    "Formador / Atendimento",
    "Pagamentos / Mensalidades",
    "Horários",
    "Instalações / Equipamentos",
    "Sugestão",
    "Outro",
]

ARQUIVO_BACKUP = BASE_DIR / "reclamacoes_recebidas.jsonl"
ULTIMO_ENVIO = {}  # limite simples: 1 envio por minuto por IP


def enviar_email(dados):
    """Envia a reclamação para o e-mail da escola. Devolve True se enviou."""
    usuario = os.environ.get("MAIL_USER")
    senha = os.environ.get("MAIL_PASSWORD", "").replace(" ", "")
    destino = os.environ.get("MAIL_DESTINO")
    if not (usuario and senha and destino):
        return False

    anonima = dados["tipo"] == "anonima"
    msg = EmailMessage()
    msg["Subject"] = (
        f"[Reclamação {'ANÓNIMA' if anonima else 'IDENTIFICADA'}] "
        f"{dados['categoria']} - {dados['assunto']}"
    )
    msg["From"] = usuario
    msg["To"] = destino
    if not anonima and "@" in dados.get("contacto", ""):
        msg["Reply-To"] = dados["contacto"]

    linhas = [
        "NOVA RECLAMAÇÃO - Light for Youth",
        "=" * 40,
        f"Data/Hora : {dados['data']}",
        f"Tipo      : {'Anónima' if anonima else 'Identificada'}",
        f"Categoria : {dados['categoria']}",
        f"Assunto   : {dados['assunto']}",
    ]
    if not anonima:
        linhas += [
            "",
            "DADOS DO ESTUDANTE",
            f"Nome      : {dados['nome']}",
            f"Curso     : {dados['curso']}",
            f"Horário   : {dados['horario']}",
            f"Contacto  : {dados['contacto'] or '-'}",
        ]
    linhas += ["", "MENSAGEM", "-" * 40, dados["mensagem"], ""]
    msg.set_content("\n".join(linhas))

    host = os .environ.get("SMTP_HOST" , "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT" , "587"))

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as servidor:
            servidor.login(usuario, senha)
            servidor.send_message(msg)

    else:
        with smtplib.SMTP(host , port, timeout=30) as servidor:
            servidor.starttls()
            servidor.login(usuario, senha)
            servidor.send_message(msg)
            
    return True


def guardar_backup(dados, enviado):
    """Guarda uma cópia local para nenhuma reclamação se perder."""
    registo = dict(dados)
    registo["enviado_por_email"] = enviado
    with open(ARQUIVO_BACKUP, "a", encoding="utf-8") as f:
        f.write(json.dumps(registo, ensure_ascii=False) + "\n")


@app.route("/")
def index():
    return render_template("index.html", categorias=CATEGORIAS, form={})


@app.route("/enviar", methods=["POST"])
def enviar():
    f = request.form

    # Campo escondido (anti-robôs): se vier preenchido, ignora.
    if f.get("website"):
        return redirect(url_for("obrigado"))

    ip = request.remote_addr or "?"
    agora = time.time()
    if agora - ULTIMO_ENVIO.get(ip, 0) < 60:
        flash("Aguarde um minuto antes de enviar outra reclamação.", "erro")
        return render_template("index.html", categorias=CATEGORIAS, form=f), 429

    tipo = "anonima" if f.get("tipo") == "anonima" else "identificada"
    dados = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tipo": tipo,
        "categoria": f.get("categoria", "Outro").strip()[:60],
        "assunto": f.get("assunto", "").strip()[:120],
        "mensagem": f.get("mensagem", "").strip()[:3000],
        "nome": f.get("nome", "").strip()[:100],
        "curso": f.get("curso", "").strip()[:100],
        "horario": f.get("horario", "").strip()[:60],
        "contacto": f.get("contacto", "").strip()[:100],
    }

    erros = []
    if not dados["assunto"]:
        erros.append("Escreva o assunto da reclamação.")
    if len(dados["mensagem"]) < 10:
        erros.append("A mensagem está muito curta (mínimo 10 letras).")
    if tipo == "identificada":
        if not dados["nome"]:
            erros.append("Escreva o seu nome.")
        if not dados["curso"]:
            erros.append("Escreva o seu curso.")
        if not dados["horario"]:
            erros.append("Indique o seu horário.")
    else:
        # Anónima: não guardamos nenhum dado pessoal
        dados.update(nome="", curso="", horario="", contacto="")

    if erros:
        for e in erros:
            flash(e, "erro")
        return render_template("index.html", categorias=CATEGORIAS, form=f), 400

    try:
        enviado = enviar_email(dados)
    except Exception as exc:  # falha de rede, palavra-passe errada, etc.
        print("Erro ao enviar e-mail:", exc)
        enviado = False

    guardar_backup(dados, enviado)
    ULTIMO_ENVIO[ip] = agora
    session["enviado"] = enviado
    return redirect(url_for("obrigado"))


@app.route("/obrigado")
def obrigado():
    return render_template("obrigado.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
