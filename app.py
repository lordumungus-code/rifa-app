import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort
from functools import wraps
from database import get_db_connection, init_db
import logging
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave-secreta-temporaria')

# Credenciais fixas (você pode alterar)
ADMIN_USERNAME = "isis"
ADMIN_PASSWORD = "grego123"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ⚠️ NOVO ENDPOINT TEMPORÁRIO PARA DOWNLOAD DO BANCO ⚠️
@app.route('/admin/backup-banco')
@login_required  # Protegido por login para não expor publicamente
def backup_banco():
    """
    Endpoint temporário para baixar o arquivo do banco SQLite.
    APÓS USAR, REMOVA ESTE CÓDIGO OU COMENTE ESTA PARTE!
    """
    try:
        # Primeiro, precisamos descobrir onde o banco está
        # Tentativa 1: Verificar se existe uma variável de ambiente com o caminho
        db_path = os.environ.get('DATABASE_PATH', None)
        
        # Tentativa 2: Se não tiver variável, vamos inspecionar a conexão
        if not db_path or not os.path.exists(db_path):
            # Abre uma conexão temporária para descobrir o caminho
            conn = sqlite3.connect(':memory:')  # Conexão temporária
            try:
                # Tenta obter o caminho do banco de dados principal
                # Isso funciona em SQLite, mas requer uma conexão real
                conn.close()
                
                # Faz uma conexão real para descobrir o caminho
                temp_conn = get_db_connection()
                # Pega o cursor e obtém informações da conexão
                cursor = temp_conn.cursor()
                # SQLite não tem comando direto, então vamos tentar caminhos comuns
                temp_conn.close()
                
                # Caminhos prováveis baseados no seu código
                possiveis_caminhos = [
                    'database.db',
                    'instance/database.db',
                    '/var/data/database.db',
                    './database.db',
                    'app.db'
                ]
                
                for caminho in possiveis_caminhos:
                    if os.path.exists(caminho):
                        db_path = caminho
                        break
                        
                if not db_path:
                    # Último recurso: procura qualquer arquivo .db no diretório
                    arquivos = [f for f in os.listdir('.') if f.endswith('.db')]
                    if arquivos:
                        db_path = arquivos[0]
            except Exception as e:
                logging.error(f"Erro ao procurar banco: {e}")
                # Fallback para caminho padrão
                db_path = 'database.db'
        
        # Verifica se o arquivo existe
        if not os.path.exists(db_path):
            # Tenta um caminho absoluto baseado no diretório atual
            db_path = os.path.join(os.path.dirname(__file__), 'database.db')
            
        if not os.path.exists(db_path):
            abort(404, description=f"Arquivo do banco não encontrado. Caminhos tentados: {db_path}")
        
        # Verifica se é realmente um arquivo SQLite
        try:
            test_conn = sqlite3.connect(db_path)
            test_conn.close()
        except:
            abort(500, description="Arquivo encontrado mas não é um banco SQLite válido")
        
        # Log para debug
        app.logger.info(f"Baixando banco de dados de: {db_path}")
        
        # Envia o arquivo para download com um nome que inclui data
        from datetime import datetime
        data_atual = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_download = f'backup_banco_{data_atual}.db'
        
        return send_file(
            db_path,
            as_attachment=True,
            download_name=nome_download,
            mimetype='application/x-sqlite3'
        )
        
    except Exception as e:
        app.logger.error(f"Erro ao fazer backup: {str(e)}")
        abort(500, description=f"Erro ao gerar backup: {str(e)}")

# ⚠️ ENDPOINT ALTERNATIVO: Backup via SQL Dump (opcional)
@app.route('/admin/backup-sql')
@login_required
def backup_sql():
    """
    Endpoint alternativo que gera um arquivo .sql com todos os dados
    Útil se o arquivo .db estiver corrompido ou inacessível
    """
    try:
        conn = get_db_connection()
        
        # Gera o dump SQL manualmente
        dump_sql = []
        
        # Obtém todas as tabelas
        tabelas = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        
        for tabela in tabelas:
            nome_tabela = tabela['name']
            
            # Pula tabelas do sistema SQLite
            if nome_tabela.startswith('sqlite_'):
                continue
            
            # Obtém o schema da tabela
            schema = conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{nome_tabela}'"
            ).fetchone()
            
            if schema and schema['sql']:
                dump_sql.append(f"-- Tabela: {nome_tabela}")
                dump_sql.append(f"{schema['sql']};")
                dump_sql.append("")
                
                # Obtém todos os dados da tabela
                dados = conn.execute(f"SELECT * FROM {nome_tabela}").fetchall()
                
                if dados:
                    colunas = [description[0] for description in conn.execute(f"SELECT * FROM {nome_tabela} LIMIT 0").description]
                    
                    for linha in dados:
                        valores = []
                        for valor in linha:
                            if valor is None:
                                valores.append("NULL")
                            elif isinstance(valor, (int, float)):
                                valores.append(str(valor))
                            else:
                                # Escapa aspas simples
                                valor_str = str(valor).replace("'", "''")
                                valores.append(f"'{valor_str}'")
                        
                        dump_sql.append(
                            f"INSERT INTO {nome_tabela} ({', '.join(colunas)}) "
                            f"VALUES ({', '.join(valores)});"
                        )
                    
                    dump_sql.append("")
        
        conn.close()
        
        # Cria o arquivo de texto com o dump
        from io import StringIO
        from datetime import datetime
        
        dump_texto = "\n".join(dump_sql)
        
        data_atual = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_download = f'backup_sql_{data_atual}.sql'
        
        # Cria um arquivo em memória
        from flask import make_response
        
        response = make_response(dump_texto)
        response.headers["Content-Disposition"] = f"attachment; filename={nome_download}"
        response.headers["Content-type"] = "text/plain"
        
        return response
        
    except Exception as e:
        app.logger.error(f"Erro ao gerar dump SQL: {str(e)}")
        abort(500, description=f"Erro ao gerar dump SQL: {str(e)}")

@app.route('/')
def index():
    conn = get_db_connection()
    numeros = conn.execute('SELECT * FROM numeros ORDER BY numero').fetchall()
    conn.close()
    
    # Organizar números por faixa - AGORA COM 4 FAIXAS
    faixas = {
        'RN': {'numeros': [], 'descricao': 'Fralda RN', 'faixa': '1-10'},
        'P': {'numeros': [], 'descricao': 'Fralda P', 'faixa': '11-30'},
        'M': {'numeros': [], 'descricao': 'Fralda M', 'faixa': '31-60'},
        'G': {'numeros': [], 'descricao': 'Fralda G', 'faixa': '61-100'}
    }
    
    for num in numeros:
        numero_dict = {
            'numero': num['numero'],
            'tipo_fralda': num['tipo_fralda'],
            'bonus': num['bonus'],
            'comprador': num['comprador']
        }
        
        if num['numero'] <= 10:
            faixas['RN']['numeros'].append(numero_dict)
        elif num['numero'] <= 30:
            faixas['P']['numeros'].append(numero_dict)
        elif num['numero'] <= 60:
            faixas['M']['numeros'].append(numero_dict)
        else:
            faixas['G']['numeros'].append(numero_dict)
    
    return render_template('index.html', faixas=faixas)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Credenciais inválidas!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    conn = get_db_connection()
    numeros = conn.execute('SELECT * FROM numeros ORDER BY numero').fetchall()
    
    # Estatísticas
    total_numeros = conn.execute('SELECT COUNT(*) FROM numeros').fetchone()[0]
    total_vendidos = conn.execute('SELECT COUNT(*) FROM numeros WHERE comprador IS NOT NULL').fetchone()[0]
    total_pagos = conn.execute('SELECT COUNT(*) FROM numeros WHERE pago = 1').fetchone()[0]
    total_pendentes = conn.execute('SELECT COUNT(*) FROM numeros WHERE comprador IS NOT NULL AND pago = 0').fetchone()[0]
    
    conn.close()
    
    return render_template('admin.html', 
                         numeros=numeros,
                         total_numeros=total_numeros,
                         total_vendidos=total_vendidos,
                         total_pagos=total_pagos,
                         total_pendentes=total_pendentes)

@app.route('/admin/comprar/<int:numero>', methods=['POST'])
@login_required
def comprar_numero(numero):
    comprador = request.form['comprador']
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE numeros 
        SET comprador = ?, pago = 0 
        WHERE numero = ? AND comprador IS NULL
    ''', (comprador, numero))
    conn.commit()
    conn.close()
    
    flash(f'Número {numero} reservado para {comprador}!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/pagar/<int:numero>', methods=['POST'])
@login_required
def pagar_numero(numero):
    conn = get_db_connection()
    conn.execute('UPDATE numeros SET pago = 1 WHERE numero = ?', (numero,))
    conn.commit()
    conn.close()
    
    flash(f'Número {numero} marcado como pago!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/cancelar/<int:numero>', methods=['POST'])
@login_required
def cancelar_compra(numero):
    conn = get_db_connection()
    conn.execute('UPDATE numeros SET comprador = NULL, pago = 0 WHERE numero = ?', (numero,))
    conn.commit()
    conn.close()
    
    flash(f'Compra do número {numero} cancelada!', 'success')
    return redirect(url_for('admin'))

# Inicializa o banco de dados ao iniciar a aplicação
try:
    init_db()
    print("Banco de dados inicializado com sucesso!")
except Exception as e:
    print(f"Erro ao inicializar banco de dados: {e}")

# (OPCIONAL) Adicione um link no template admin.html
# Se quiser, pode adicionar um botão no admin.html para facilitar o download

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)