from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import secrets

app = Flask(__name__)

# Configuração do banco de dados
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'lc_sistemas_corporativo'
}

app.secret_key = secrets.token_hex(16)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']



        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            # Verificar se o usuário e senha existem no banco de dados
            cursor.execute("SELECT * FROM usuario WHERE login = %s AND senha = %s", (login, senha))
            usuario = cursor.fetchone()

            if usuario:
                # Se encontrado, armazena o ID do usuário na sessão
                session['user_id'] = usuario['id']
                session['user_name'] = usuario['nome']
                return redirect(url_for('home'))
            else:
                # Se não encontrado, exibe mensagem de erro
                error = "Credenciais inválidas. Tente novamente."
                return render_template('login.html', error=error)

        except Exception as e:
            return f"Erro ao conectar ao banco de dados: {e}"
        finally:
            cursor.close()
            connection.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Remove o usuário da sessão
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    # Verifica se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total_clientes FROM cliente where ativo=1")
        total_clientes = cursor.fetchone()["total_clientes"]

    except Exception as e:
        return f"Erro ao conectar ao banco de dados: {e}"
    finally:
        cursor.close()
        connection.close()

    return render_template('home.html', total_clientes=total_clientes)


# Página de clientes
@app.route('/clientes', methods=['GET'])
def buscar_cliente():
    # Verifica se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))

    nome = request.args.get('nome')
    cnpj = request.args.get('cnpj')
    page = int(request.args.get('page', 1))
    limit = 10
    offset = (page - 1) * limit

    query = "SELECT * FROM cliente"
    filters = []

    if nome:
        filters.append(f"nome LIKE '%{nome}%'")
    if cnpj:
        filters.append(f"cpf_cnpj LIKE '%{cnpj}%'")

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += f" LIMIT {limit} OFFSET {offset}"

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        cursor.execute(query)
        clientes = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM cliente")
        total_clientes = cursor.fetchone()['COUNT(*)']

    except Exception as e:
        return f"Erro ao conectar ao banco de dados: {e}"
    finally:
        cursor.close()
        connection.close()

    total_paginas = (total_clientes // limit) + (1 if total_clientes % limit > 0 else 0)

    return render_template('clientes.html', clientes=clientes, page=page, total_paginas=total_paginas)

# Rota de detalhes do cliente
@app.route('/cliente/<int:id_cliente>', methods=['GET'])
def detalhes_cliente(id_cliente):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT c.*, cc.nome as cidade
            FROM cliente c 
            INNER JOIN cidades cc ON cc.id = c.id_cidade 
            WHERE c.id = %s
        """, (id_cliente,))
        cliente = cursor.fetchone()

        cursor.execute("SELECT * FROM receber WHERE id_cliente = %s", (id_cliente,))
        parcelas = cursor.fetchall()

    except Exception as e:
        return f"Erro ao conectar ao banco de dados: {e}"
    finally:
        cursor.close()
        connection.close()

    if not cliente:
        return "Cliente não encontrado."

    return render_template('detalhes_cliente.html', cliente=cliente, parcelas=parcelas)


@app.route('/atendimentos', methods=['GET', 'POST'])
def atendimentos():
    # Verifica se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        id_cliente = request.form['id_cliente']
        id_usuario = request.form['id_usuario']
        data = request.form['data']
        id_servico = request.form['id_servico']
        observacao = request.form['observacao']

        # Conectando ao banco de dados
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            # Inserir o atendimento no banco de dados
            cursor.execute("""
                INSERT INTO atendimentos (id_cliente, id_usuario, data, id_servico, observacao)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_cliente, id_usuario, data, id_servico, observacao))
            connection.commit()
            return redirect('/atendimentos')  # Redireciona de volta para a página de atendimentos

        except Exception as e:
            return f"Erro ao registrar o atendimento: {e}"
        finally:
            cursor.close()
            connection.close()

    # Caso GET: Exibir o formulário
    try:
        # Conectar ao banco para obter os clientes e usuários
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # Obter todos os clientes
        cursor.execute("SELECT id, nome FROM cliente")
        clientes = cursor.fetchall()

        # Obter todos os usuários
        cursor.execute("SELECT id, nome FROM usuario")
        usuarios = cursor.fetchall()

        # Obter todos os serviços disponíveis
        cursor.execute("SELECT id, nome FROM produto")
        servicos = cursor.fetchall()

    except Exception as e:
        return f"Erro ao conectar ao banco de dados: {e}"
    finally:
        cursor.close()
        connection.close()

    return render_template('atendimentos.html', clientes=clientes, usuarios=usuarios, servicos=servicos)


@app.route('/historico', methods=['GET', 'POST'])
def historico_atendimentos():
    # Verifica se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))


    # Filtros
    cliente_id = request.args.get('id_cliente')  # ID do cliente para filtro
    data_inicio = request.args.get('data_inicio')  # Data de início para filtro
    data_fim = request.args.get('data_fim')  # Data de fim para filtro
    status = request.args.get('status')  # Status de ativo ou inativo

    # Monta a query com filtros
    query = """
        SELECT a.*, c.nome AS cliente_nome, u.nome AS usuario_nome, p.nome AS servico_nome 
        FROM atendimentos a
        INNER JOIN cliente c ON a.id_cliente = c.id 
        INNER JOIN usuario u ON a.id_usuario = u.id 
        INNER JOIN produto p ON a.id_servico = p.id
        WHERE a.ativo = 1  """  # Filtro padrão para ativos

    # Adiciona filtro de status, se o usuário escolheu
    if status is not None:
        query = query.replace("WHERE a.ativo = 1", f"WHERE a.ativo = {status}")

    filters = []

    if cliente_id:
        filters.append(f"a.id_cliente = {cliente_id}")
    if data_inicio and data_fim:
        filters.append(f"a.data BETWEEN '{data_inicio}' AND '{data_fim}'")

    # Adiciona outros filtros à consulta
    if filters:
        query += " AND " + " AND ".join(filters)

    # Limita o número de resultados
    query += " LIMIT 15"  # Limitar a 15 atendimentos

    try:
        # Conexão com o banco de dados
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # Executa a consulta com os filtros
        cursor.execute(query)
        atendimentos = cursor.fetchall()

        # Consulta todos os clientes para preencher o filtro
        cursor.execute("SELECT id, nome FROM cliente")
        clientes = cursor.fetchall()

    except Exception as e:
        return f"Erro ao conectar ao banco de dados: {e}"
    finally:
        cursor.close()
        connection.close()

    return render_template('historico_atendimentos.html', atendimentos=atendimentos, clientes=clientes)


@app.route('/inutilizar_atendimento/<int:id_atendimento>', methods=['POST'])
def inutilizar_atendimento(id_atendimento):

    # Verifica se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))


    # Verifica se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        # Conexão com o banco de dados
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Atualiza o atendimento para inativo
        cursor.execute("UPDATE atendimentos SET ativo = 0 WHERE id = %s", (id_atendimento,))
        connection.commit()

        # Redireciona para a página de histórico
        return redirect('/historico')

    except Exception as e:
        return f"Erro ao atualizar o atendimento: {e}"
    finally:
        cursor.close()
        connection.close()

@app.route('/dashboard')
def dashboard():
    # Verifica se o usuário está logado
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Conexão com o banco de dados
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta para contar os atendimentos ativos
        cursor.execute("SELECT COUNT(*) FROM atendimentos WHERE ativo = 1")
        total_atendimentos_ativos = cursor.fetchone()[0]

        # Consulta para contar os clientes (caso precise)
        cursor.execute("SELECT COUNT(*) FROM cliente")
        total_clientes = cursor.fetchone()[0]

    except Exception as e:
        return f"Erro ao conectar ao banco de dados: {e}"
    finally:
        cursor.close()
        connection.close()

    # Passando os dados para o template
    return render_template('dashboard.html', total_atendimentos_ativos=total_atendimentos_ativos, total_clientes=total_clientes)



if __name__ == '__main__':
    app.run(debug=True)
