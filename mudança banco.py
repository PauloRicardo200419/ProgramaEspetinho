import sqlite3

# Conectando ao banco de dados
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Verifica se a tabela 'venda' existe
cursor.execute("PRAGMA table_info(venda);")
columns = cursor.fetchall()
column_names = [column[1] for column in columns]

# Se a coluna 'observacao' não existir, adiciona
if 'observacao' not in column_names:
    cursor.execute("ALTER TABLE venda ADD COLUMN observacao TEXT;")
    conn.commit()

# Fechar a conexão
conn.close()

print("Coluna 'observacao' adicionada com sucesso, se não existia!")
