# Controle Financeiro

Sistema web em Django para controlar as finanças de uma organização: contas, categorias, lançamentos parcelados, orçamentos, dashboard com gráficos, equipe com papéis (administrador e operador) e API REST.

## Requisitos

- Python 3.10 ou mais novo
- Git

## Como abrir o projeto

Windows (PowerShell), dentro da pasta onde você quer baixar o projeto:

```powershell
git clone https://github.com/ThiagoPix/CRUD-Financeiro.git
cd CRUD-Financeiro
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Crie o arquivo `.env` com uma chave secreta nova:

```powershell
$chave = .venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(50))"
"SECRET_KEY=$chave`nDEBUG=True`nALLOWED_HOSTS=127.0.0.1,localhost" | Set-Content .env
```

Crie o banco e ligue o servidor:

```powershell
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver
```

Abra **http://127.0.0.1:8000/** no navegador.

Linux e macOS: use `python3 -m venv .venv` e troque `.venv\Scripts\python` por `.venv/bin/python`. Para o `.env`, copie o `.env.example` (`cp .env.example .env`) e preencha `SECRET_KEY` com qualquer texto longo e aleatório.

## Primeiro acesso

1. Na tela de entrada, clique em **Criar conta para a minha organização**.
2. Informe o nome da organização, um usuário e uma senha. Você entra como **administrador**.
3. Cadastre uma conta e uma categoria, depois faça o primeiro lançamento. O dashboard mostra os números e os gráficos.
4. Em **Equipe**, adicione outras pessoas como administrador ou operador.

## Papéis

- **Administrador:** faz tudo, inclusive contas, categorias, orçamentos, equipe e exportação CSV.
- **Operador:** consulta os números e cria e edita lançamentos e parcelas.

## Endereços

| Endereço | O que é |
|---|---|
| `/` | Entrada do sistema |
| `/dashboard/` | Métricas e gráficos |
| `/lancamentos/`, `/contas/`, `/categorias/`, `/orcamentos/` | Telas de cadastro |
| `/equipe/` | Equipe da organização (administrador) |
| `/api/` | API REST: `contas`, `categorias`, `lancamentos`, `orcamentos`, `parcelas`, `dashboard`, `organizacao`, `equipe`, `cadastro` |
| `/admin/` | Admin do Django (precisa de `manage.py createsuperuser`) |

## Testes

```powershell
.venv\Scripts\python manage.py test
```
