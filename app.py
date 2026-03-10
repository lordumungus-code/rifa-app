import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave-secreta-temporaria')

# Credenciais fixas (você pode alterar)
ADMIN_USERNAME = "papai"
ADMIN_PASSWORD = "mamae123"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    conn = get_db_connection()
    numeros = conn.execute('SELECT * FROM numeros ORDER BY numero').fetchall()
    conn.close()
    
    # Organizar números por faixa
    faixas = {
        'P': {'numeros': [], 'descricao': 'Fralda P + Lenço umedecido', 'faixa': '1-30'},
        'M': {'numeros': [], 'descricao': 'Fralda M + Pomada de assadura', 'faixa': '31-70'},
        'G': {'numeros': [], 'descricao': 'Fralda G + Roquinha', 'faixa': '71-100'}
    }
    
    for num in numeros:
        # Não passamos a informação de pago para o template público
        numero_dict = {
            'numero': num['numero'],
            'tipo_fralda': num['tipo_fralda'],
            'bonus': num['bonus'],
            'comprador': num['comprador']
        }
        
        if num['numero'] <= 30:
            faixas['P']['numeros'].append(numero_dict)
        elif num['numero'] <= 70:
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

if __name__ == '__main__':
    # Em produção, use a porta definida pela variável de ambiente PORT
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)