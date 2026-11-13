"""Testes automatizados (unitários e de integração) - Padaria Santo Pani.
Rodar na raiz do projeto:  python -m pytest -v --cov=app --cov-report=term-missing
"""
import os
import re
from datetime import date, timedelta

# Banco em memória para os testes. Deve vir ANTES de importar o app.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ADMIN_USER"] = "gestor"
os.environ["ADMIN_PASSWORD"] = "senha-de-teste-123"

import pytest
from app import Produto, Registro, app, db, destino_seguro, gerar_alerta

USUARIO, SENHA = "gestor", "senha-de-teste-123"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def token(html):
    return re.search(r'name="_csrf" value="(\w+)"', html).group(1)


def logar(client, usuario=USUARIO, senha=SENHA, next_url=""):
    html = client.get("/login").get_data(as_text=True)
    return client.post(f"/login{next_url}", data={"_csrf": token(html), "usuario": usuario, "senha": senha})


def produto_id(nome="Bolo de Fubá"):
    with app.app_context():
        return Produto.query.filter_by(nome=nome).first().id


def registrar(client, produzido, sobra, produto=None, data=None):
    html = client.get("/registro").get_data(as_text=True)
    return client.post("/registro", data={
        "_csrf": token(html), "data": data or date.today().isoformat(),
        "produto": str(produto or produto_id()), "produzido": produzido, "sobra": sobra})


# ---------------- UNITÁRIOS ----------------
@pytest.mark.parametrize("pct,nivel", [(65, "alto"), (50, "alto"), (33, "moderado"), (25, "moderado"), (5, "baixo")])
def test_gerar_alerta_niveis(pct, nivel):
    assert gerar_alerta(pct, "Bolo de Fubá")["nivel"] == nivel


def test_alerta_alto_texto_e_acao():
    a = gerar_alerta(65, "Bolo de Fubá")
    assert "ALERTA DE ALTO DESPERDÍCIO: Bolo de Fubá com 65% de sobra" in a["texto"]
    assert a["acao"] == "Reduzir produção em 30% amanhã"


def test_percentual_do_registro():
    assert Registro(produzido=20, sobra=13).percentual == 65
    assert Registro(produzido=0, sobra=0).percentual == 0


@pytest.mark.parametrize("alvo,esperado", [("/registro", "/registro"), ("//evil.com", "/registro"),
                                           ("https://evil.com", "/registro"), (None, "/registro")])
def test_destino_seguro_bloqueia_open_redirect(alvo, esperado):
    with app.test_request_context():
        assert destino_seguro(alvo) == esperado


# ---------------- INTEGRAÇÃO: autenticação e segurança ----------------
def test_login_pagina_carrega(client):
    r = client.get("/")
    assert r.status_code == 200 and "Iniciar Sessão" in r.get_data(as_text=True)


def test_login_senha_errada(client):
    r = logar(client, senha="errada")
    assert r.status_code == 200 and "incorretos" in r.get_data(as_text=True)


def test_login_usuario_inexistente(client):
    assert "incorretos" in logar(client, usuario="ninguem").get_data(as_text=True)


def test_login_correto_redireciona(client):
    r = logar(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/registro")


def test_login_nao_permite_open_redirect(client):
    r = logar(client, next_url="?next=//evil.com")
    assert "evil.com" not in r.headers["Location"]


def test_rotas_protegidas_exigem_login(client):
    for rota in ("/registro", "/painel/1", "/painel/preditivo"):
        r = client.get(rota)
        assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_post_sem_csrf_e_rejeitado(client):
    assert client.post("/login", data={"usuario": USUARIO, "senha": SENHA}).status_code == 400


def test_logout_encerra_sessao(client):
    logar(client)
    html = client.get("/registro").get_data(as_text=True)
    client.post("/sair", data={"_csrf": token(html)})
    assert client.get("/registro").status_code == 302


def test_cabecalhos_de_seguranca(client):
    h = client.get("/login").headers
    assert "default-src 'self'" in h["Content-Security-Policy"]
    assert h["X-Content-Type-Options"] == "nosniff"


# ---------------- INTEGRAÇÃO: registro, painel e persistência ----------------
def test_registro_valido_persiste_e_gera_alerta(client):
    logar(client)
    r = registrar(client, 20, 13)
    assert r.status_code == 302 and "/painel/" in r.headers["Location"]
    corpo = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Registro salvo com sucesso" in corpo
    assert "ALERTA DE ALTO DESPERDÍCIO: Bolo de Fubá com 65% de sobra" in corpo
    assert "Reduzir produção em 30% amanhã" in corpo
    with app.app_context():
        assert Registro.query.count() >= 1


def test_sobra_maior_que_producao_e_bloqueada(client):
    logar(client)
    with app.app_context():
        antes = Registro.query.count()
    r = registrar(client, 10, 20)
    assert r.status_code == 200 and "não pode exceder" in r.get_data(as_text=True)
    with app.app_context():
        assert Registro.query.count() == antes


@pytest.mark.parametrize("produzido,sobra", [("abc", "1"), ("10", "-1"), ("0", "0"), ("", ""), ("999999", "1")])
def test_numeros_invalidos(client, produzido, sobra):
    logar(client)
    r = registrar(client, produzido, sobra)
    assert r.status_code == 200 and "erro" in r.get_data(as_text=True)


def test_data_futura_e_invalida(client):
    logar(client)
    r = registrar(client, 10, 1, data=(date.today() + timedelta(days=2)).isoformat())
    assert "não pode ser futura" in r.get_data(as_text=True)
    assert "data válida" in registrar(client, 10, 1, data="xx").get_data(as_text=True)


def test_produto_invalido(client):
    logar(client)
    assert "Selecione um tipo" in registrar(client, 10, 1, produto="9999").get_data(as_text=True)


def test_painel_inexistente_da_404(client):
    logar(client)
    assert client.get("/painel/99999").status_code == 404

def test_painel_preditivo(client):
    logar(client)
    registrar(client, 100, 5, produto=produto_id("Pão Francês"))
    corpo = client.get("/painel/preditivo").get_data(as_text=True)
    assert "Painel preditivo" in corpo and "Pão Francês" in corpo