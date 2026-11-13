# 🥖 Padaria Santo Pani — Gestão de Perecíveis e Combate ao Desperdício (ODS 12)

Aplicação web (MVP) desenvolvida para apoiar a gestão diária de produção e sobras de alimentos perecíveis na **Padaria Santo Pani** (Bairro Socorro, Pindamonhangaba – SP), substituindo controles empíricos por registros estruturados e alertas preditivos de desperdício.

---

## 🎯 Problema e Alinhamento Socioambiental (ODS 12)
O estabelecimento enfrentava perdas recorrentes de produtos de panificação devido ao planejamento baseado apenas na intuição. Este projeto está diretamente alinhado à **Meta 12.3 dos Objetivos de Desenvolvimento Sustentável (ODS 12 — Consumo e Produção Responsáveis)** da ONU, fornecendo indicadores claros para reduzir o desperdício de alimentos na cadeia produtiva local.

---

## 🛠️ Tecnologias e Arquitetura
* **Arquitetura:** Monolítica em camadas (padrão MVC).
* **Back-end:** Python 3 com microframework **Flask**.
* **Banco de Dados e ORM:** **SQLite** com **SQLAlchemy** (consultas parametrizadas).
* **Front-end:** HTML5, CSS3 e JavaScript responsivo (Mobile-First).

---

## 🔒 Segurança e Acessibilidade
* **Segurança (OWASP Top 10):** Autenticação com hashing robusto de senhas (sem armazenamento em texto limpo), validação de entradas no servidor e prevenção contra SQL Injection (SQLi) e Cross-Site Scripting (XSS).
* **Acessibilidade (WCAG):** Contraste mínimo de 4.5:1, áreas de toque de no mínimo 44x44px para uso ágil em dispositivos móveis na retaguarda, rótulos persistentes e alertas redundantes (combinação de cores, ícones e mensagens textuais).

---

## 📱 Funcionalidades Principais (Fluxo do MVP)
1. **Autenticação Segura (Tela 1):** Controle de acesso restrito a operadores e gestores da padaria.
2. **Registro de Produção e Sobras (Tela 2):** Lançamento diário da quantidade produzida e excedente por item perecível, com bloqueio de inconsistências (sobra maior que produção).
3. **Painel de Alertas e Resultados (Tela 3):** Cálculo automático da taxa de desperdício, emissão de alertas de prioridade e sugestões práticas de ajuste para a próxima fornada.

---

## 🚀 Como Executar Localmente

```bash
# 1. Clone o repositório
git clone [https://github.com/seu-usuario/padaria-santo-pani-mvp.git](https://github.com/seu-usuario/padaria-santo-pani-mvp.git)

# 2. Acesse a pasta do projeto
cd padaria-santo-pani-mvp

# 3. Crie e ative um ambiente virtual
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/macOS:
source venv/bin/activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Execute a aplicação
python app.py
