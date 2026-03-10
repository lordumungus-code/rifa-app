import os
import sqlite3

def get_db_connection():
    # Verifica se existe uma variável de ambiente com o caminho do volume
    db_path = os.environ.get('DB_PATH', 'rifa.db')
    
    # Se estiver no Railway com volume, usa o caminho do volume
    if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
        db_path = os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'rifa.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados criando as tabelas e inserindo os números"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Criar tabela de números da rifa
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS numeros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER UNIQUE,
            tipo_fralda TEXT,
            bonus TEXT,
            comprador TEXT,
            pago BOOLEAN DEFAULT 0,
            data_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inserir números de 1 a 100 se não existirem
    for i in range(1, 101):
        if i <= 30:
            tipo = "P"
            bonus = "Lenço umedecido"
        elif i <= 70:
            tipo = "M"
            bonus = "Pomada de assadura"
        else:
            tipo = "G"
            bonus = "Roquinha"
        
        cursor.execute('''
            INSERT OR IGNORE INTO numeros (numero, tipo_fralda, bonus, pago)
            VALUES (?, ?, ?, 0)
        ''', (i, tipo, bonus))
    
    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db()