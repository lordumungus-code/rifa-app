import sqlite3
import os

DATABASE = 'rifa.db'

def get_db_connection():
    """Cria uma conexão com o banco de dados"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias e números de 1 a 100"""
    conn = get_db_connection()
    
    # Criar tabela se não existir
    conn.execute('''
        CREATE TABLE IF NOT EXISTS numeros (
            numero INTEGER PRIMARY KEY,
            tipo_fralda TEXT NOT NULL,
            bonus TEXT NOT NULL,
            comprador TEXT,
            pago BOOLEAN DEFAULT 0
        )
    ''')
    
    # Verificar se já existem números
    existing = conn.execute('SELECT COUNT(*) FROM numeros').fetchone()[0]
    
    if existing == 0:
        # Definir os tipos de fralda e bônus para cada faixa
        # RN: 1-10, P: 11-30, M: 31-60, G: 61-100
        for i in range(1, 101):
            if i <= 10:
                tipo_fralda = 'RN'
                bonus = 'Lenço umedecido'
            elif i <= 30:
                tipo_fralda = 'P'
                bonus = 'Lenço umedecido'
            elif i <= 60:
                tipo_fralda = 'M'
                bonus = 'Pomada de assadura'
            else:
                tipo_fralda = 'G'
                bonus = 'Roquinha'
            
            conn.execute('''
                INSERT INTO numeros (numero, tipo_fralda, bonus, comprador, pago)
                VALUES (?, ?, ?, ?, ?)
            ''', (i, tipo_fralda, bonus, None, 0))
        
        conn.commit()
        print("Banco de dados populado com números de 1 a 100")
    
    conn.close()