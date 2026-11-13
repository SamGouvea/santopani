"""Padaria Santo Pani - MVP de controle de sobras (ODS 12, Meta 12.3).
Arquitetura monolítica em camadas: Modelos (SQLAlchemy) / Rotas-Controle (Flask) / Visões (Jinja2).
"""
import os
import secrets
from datetime import date, timedelta
from functools import wraps
from urllib.parse import urlparse

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),  # defina SECRET_KEY em produção
    SQLALCHEMY_DATABASE_URI="sqlite:///santo_pani.db",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",  # use 1 com HTTPS
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
db = SQLAlchemy(app)

# Limiares de desperdício (% de sobra sobre a produção)
LIMIAR_ALTO, LIMIAR_MODERADO = 50, 25
MAX_UNIDADES = 100000


# ----------------------------- MODELOS -----------------------------
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)  # scrypt/PBKDF2 com salt (Werkzeug)
    papel = db.Column(db.String(20), nullable=False, default="operador")


class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)


class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False, index=True)
    produzido = db.Column(db.Integer, nullable=False)
    sobra = db.Column(db.Integer, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    produto = db.relationship("Produto")

    __table_args__ = (db.CheckConstraint("sobra >= 0 AND sobra <= produzido", name="ck_sobra"),)

    @property
    def percentual(self):
        return round(self.sobra * 100 / self.produzido) if self.produzido else 0


# ----------------------------- SERVIÇOS -----------------------------
def gerar_alerta(percentual, produto):
    """Alerta preditivo simples baseado no percentual de sobra."""
    if percentual >= LIMIAR_ALTO:
        return {"nivel": "alto", "icone": "⚠️",
                "texto": f"ALERTA DE ALTO DESPERDÍCIO: {produto} com {percentual}% de sobra",
                "acao": "Reduzir produção em 30% amanhã"}
    if percentual >= LIMIAR_MODERADO:
        return {"nivel": "moderado", "icone": "⚠️",
                "texto": f"Atenção: {produto} com {percentual}% de sobra",
                "acao": "Reduzir produção em 15% amanhã"}
    return {"nivel": "baixo", "icone": "✓",
            "texto": f"Desperdício sob controle: {produto} com {percentual}% de sobra",
            "acao": "Manter a produção atual"}


def init_db():
    db.create_all()
    if not Produto.query.first():
        db.session.add_all([Produto(nome=n) for n in
                            ("Pão Francês", "Bolo de Fubá", "Pão de Queijo", "Broa de Milho", "Sonho")])
    if not Usuario.query.first():
        # Credenciais iniciais: ALTERE via variáveis de ambiente antes de usar de verdade.
        user = os.environ.get("ADMIN_USER", "gestor")
        pwd = os.environ.get("ADMIN_PASSWORD", "Troque-Esta-Senha-123")
        db.session.add(Usuario(nome=user, senha_hash=generate_password_hash(pwd), papel="gestor"))
    db.session.commit()


# ----------------------------- SEGURANÇA -----------------------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def proteger_csrf():
    if request.method == "POST":
        enviado = request.form.get("_csrf", "")
        if not secrets.compare_digest(enviado, session.get("_csrf", "")):
            abort(400, "Token CSRF inválido.")


@app.after_request
def cabecalhos(resp):
    resp.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Cache-Control"] = "no-store" if "usuario_id" in session else resp.headers.get("Cache-Control", "")
    return resp


def login_obrigatorio(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "usuario_id" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)
    return wrapper


def destino_seguro(alvo):
    """Evita open redirect: só aceita caminhos internos."""
    if alvo and not urlparse(alvo).netloc and alvo.startswith("/") and not alvo.startswith("//"):
        return alvo
    return url_for("registro")


# ----------------------------- ROTAS (TELAS) -----------------------------
# Hash fictício para manter tempo de resposta similar quando o usuário não existe
_HASH_FALSO = generate_password_hash("senha-inexistente")


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():  # TELA 1
    erro = None
    if request.method == "POST":
        nome = request.form.get("usuario", "").strip()[:50]
        senha = request.form.get("senha", "")[:128]
        u = Usuario.query.filter_by(nome=nome).first()  # consulta parametrizada pelo ORM
        ok = check_password_hash(u.senha_hash if u else _HASH_FALSO, senha)
        if u and ok:
            session.clear()  # previne fixação de sessão
            session.permanent = True
            session["usuario_id"], session["usuario_nome"] = u.id, u.nome
            return redirect(destino_seguro(request.args.get("next")))
        erro = "Utilizador ou palavra-passe incorretos."
    return render_template("login.html", erro=erro)


@app.route("/sair", methods=["POST"])
def sair():
    session.clear()
    return redirect(url_for("login"))


@app.route("/registro", methods=["GET", "POST"])
@login_obrigatorio
def registro():  # TELA 2
    produtos = Produto.query.order_by(Produto.nome).all()
    erros, valores = {}, {"data": date.today().isoformat(), "produto": "", "produzido": "", "sobra": ""}
    if request.method == "POST":
        valores.update(data=request.form.get("data", ""), produto=request.form.get("produto", ""),
                       produzido=request.form.get("produzido", ""), sobra=request.form.get("sobra", ""))
        try:
            data = date.fromisoformat(valores["data"])
            if data > date.today():
                erros["data"] = "A data não pode ser futura."
        except ValueError:
            data = None
            erros["data"] = "Informe uma data válida."

        prod = None
        if valores["produto"].isdigit():
            prod = db.session.get(Produto, int(valores["produto"]))
        if not prod:
            erros["produto"] = "Selecione um tipo de produto."

        def inteiro(campo, rotulo):
            v = valores[campo].strip()
            if not v.isdigit() or int(v) > MAX_UNIDADES:
                erros[campo] = f"{rotulo}: informe um número inteiro entre 0 e {MAX_UNIDADES}."
                return None
            return int(v)

        produzido, sobra = inteiro("produzido", "Quantidade produzida"), inteiro("sobra", "Quantidade sobrante")
        if produzido == 0:
            erros["produzido"] = "A quantidade produzida deve ser maior que zero."
        if produzido is not None and sobra is not None and sobra > produzido and "sobra" not in erros:
            erros["sobra"] = "A sobra não pode exceder a quantidade produzida."

        if not erros:
            r = Registro(data=data, produto_id=prod.id, produzido=produzido, sobra=sobra,
                         usuario_id=session["usuario_id"])
            db.session.add(r)
            db.session.commit()
            return redirect(url_for("painel", registro_id=r.id))
    return render_template("registro.html", produtos=produtos, erros=erros, v=valores,
                           hoje=date.today().isoformat())


@app.route("/painel/<int:registro_id>")
@login_obrigatorio
def painel(registro_id):  # TELA 3
    r = db.get_or_404(Registro, registro_id)
    return render_template("painel.html", r=r, alerta=gerar_alerta(r.percentual, r.produto.nome))


@app.route("/painel/preditivo")
@login_obrigatorio
def preditivo():
    desde = date.today() - timedelta(days=7)
    linhas = (db.session.query(Produto.nome, func.sum(Registro.produzido), func.sum(Registro.sobra))
              .join(Registro).filter(Registro.data >= desde).group_by(Produto.id).all())
    dados = []
    for nome, prod, sobra in linhas:
        pct = round(sobra * 100 / prod) if prod else 0
        dados.append({"nome": nome, "produzido": prod, "sobra": sobra, "pct": pct,
                      "alerta": gerar_alerta(pct, nome)})
    dados.sort(key=lambda d: -d["pct"])
    return render_template("preditivo.html", dados=dados)


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=False)  # nunca use debug=True em produção
