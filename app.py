from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import pytz
from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = os.path.join('static', 'uploads')

# Defina o fuso horário para o horário de Brasília
timezone = pytz.timezone('America/Sao_Paulo')

# Obtém a data e hora atual com o fuso horário correto
datetime.now(timezone)


app = Flask(__name__)
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'laucher1'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, default=0)
    imagem = db.Column(db.String(255))
    itens_venda = db.relationship('ItemVenda', back_populates='produto')

class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))
    total = db.Column(db.Float, nullable=False)
    observacao = db.Column(db.Text)  # A coluna 'observacao' agora é parte do modelo
    itens = db.relationship('ItemVenda', back_populates='venda')

class ItemVenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('venda.id'))
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'))
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    venda = db.relationship('Venda', back_populates='itens')
    produto = db.relationship('Produto', back_populates='itens_venda')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/produtos', methods=['GET', 'POST'])
def produtos():
    if request.method == 'POST':
        nome = request.form['nome']
        preco = request.form['preco']
        estoque = request.form['estoque']
        imagem = request.files.get('imagem')

        imagem_nome = None
        if imagem and imagem.filename != '':
            imagem_nome = secure_filename(imagem.filename)
            imagem.save(os.path.join(UPLOAD_FOLDER, imagem_nome))

        novo_produto = Produto(nome=nome, preco=preco, estoque=estoque, imagem=imagem_nome)
        db.session.add(novo_produto)
        db.session.commit()
        return redirect(url_for('produtos'))

    produtos = Produto.query.all()
    return render_template('produtos.html', produtos=produtos)

#Editar produto 

@app.route('/editar_produto/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    produto = Produto.query.get(id)

    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.preco = float(request.form['preco'])
        produto.estoque = int(request.form['estoque'])

        if 'imagem' in request.files:
            imagem = request.files['imagem']
            if imagem.filename != '':
                filename = secure_filename(imagem.filename)
                caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                imagem.save(caminho)
                produto.imagem = filename

        db.session.commit()
        return redirect(url_for('produtos'))
    
    return render_template('editar_produto.html', produto=produto)

#Adicionar estoque 

@app.route('/adicionar_estoque/<int:id>', methods=['GET', 'POST'])
def adicionar_estoque(id):
    produto = Produto.query.get(id)

    if request.method == 'POST':
        quantidade_adicional = int(request.form['quantidade'])
        produto.estoque += quantidade_adicional
        db.session.commit()
        return redirect(url_for('produtos'))
    
    return render_template('adicionar_estoque.html', produto=produto)

#Delete produto 

@app.route('/deletar_produto/<int:id>', methods=['POST'])
def deletar_produto(id):
    produto = Produto.query.get(id)
    db.session.delete(produto)
    db.session.commit()
    return redirect(url_for('produtos'))

#Venda

@app.route('/venda', methods=['GET', 'POST'])
def venda():
    if 'carrinho' not in session:
        session['carrinho'] = []

    if request.method == 'POST':
        # Remover produto
        for item in session['carrinho']:
            if f"remover_{item['produto_id']}" in request.form:
                produto = Produto.query.get(item['produto_id'])
                produto.estoque += item['quantidade']  # Reverte a quantidade no estoque
                db.session.commit()  # Atualiza o estoque no banco
                session['carrinho'].remove(item)  # Remove o item do carrinho
                session.modified = True
                break

        # Atualizar quantidades
        for item in session['carrinho']:
            quantidade_key = f"quantidade_{item['produto_id']}"
            if quantidade_key in request.form:
                nova_quantidade = int(request.form[quantidade_key])
                produto = Produto.query.get(item['produto_id'])

                # Atualiza o estoque: primeiro, reverte a quantidade anterior
                produto.estoque += item['quantidade']  # Reverte o estoque do item anterior
                produto.estoque -= nova_quantidade  # Atualiza com a nova quantidade
                db.session.commit()  # Atualiza no banco de dados

                # Atualiza a quantidade no carrinho
                item['quantidade'] = nova_quantidade
                session.modified = True

        # Capturar a observação
        observacao = request.form.get('observacao', '')  # Captura a observação ou usa uma string vazia
        session['observacao'] = observacao  # Armazenar a observação na sessão

        # Adicionar novo produto
        if 'produto_id' in request.form:
            produto_id = int(request.form['produto_id'])
            quantidade = int(request.form['quantidade'])
            produto = Produto.query.get(produto_id)

            # Verifica se há estoque suficiente
            if produto.estoque < quantidade:
                flash(f"Estoque insuficiente para {produto.nome}. Disponível: {produto.estoque}", 'danger')
                return redirect(url_for('venda'))

            # Verifica se o produto já está no carrinho
            for item in session['carrinho']:
                if item['produto_id'] == produto_id:
                    item['quantidade'] += quantidade
                    produto.estoque -= quantidade  # Atualiza o estoque ao adicionar no carrinho
                    db.session.commit()  # Atualiza o estoque no banco
                    session.modified = True
                    return redirect(url_for('venda'))

            # Adiciona item ao carrinho
            session['carrinho'].append({'produto_id': produto_id, 'quantidade': quantidade})
            produto.estoque -= quantidade  # Atualiza o estoque ao adicionar no carrinho
            db.session.commit()  # Atualiza o estoque no banco
            session.modified = True

    carrinho = []
    total = 0

    # Calcula o total e exibe os produtos no carrinho
    for item in session['carrinho']:
        produto = Produto.query.get(item['produto_id'])
        imagem = produto.imagem if produto.imagem else 'sem-imagem.png'  # Define uma imagem padrão caso não haja imagem do produto
        caminho_imagem = url_for('static', filename=f'uploads/{imagem}')
        
        carrinho.append({
            'produto': produto,
            'quantidade': item['quantidade'],
            'imagem': caminho_imagem  # Adiciona o caminho da imagem
        })
        total += produto.preco * item['quantidade']

    produtos = Produto.query.all()

    # Passa a observação para o template
    return render_template('venda.html', produtos=produtos, carrinho=carrinho, total=total, observacao=session.get('observacao', ''))





@app.route('/finalizar', methods=['POST'])
def finalizar():
    carrinho = session.get('carrinho', [])
    total = 0
    nova_venda = Venda(total=0)

    # Verificação de estoque antes de registrar a venda
    for item in carrinho:
        produto = Produto.query.get(item['produto_id'])
        quantidade = item['quantidade']

        # Verifica se há estoque suficiente para cada item
        if produto.estoque < quantidade:
            # Flash a mensagem de erro e redireciona para a página de venda
            flash(f"Estoque insuficiente para {produto.nome}. Disponível: {produto.estoque}", "error")
            return redirect(url_for('venda'))

        total += produto.preco * quantidade

    # Cria a venda e atualiza o estoque
    db.session.add(nova_venda)
    db.session.commit()

    for item in carrinho:
        produto = Produto.query.get(item['produto_id'])
        quantidade = item['quantidade']

        # Atualiza o estoque do produto
        produto.estoque -= quantidade

        # Adiciona o item na venda
        db.session.add(ItemVenda(venda_id=nova_venda.id, produto_id=produto.id, quantidade=quantidade, preco_unitario=produto.preco))

    # Atualiza o total da venda
    nova_venda.total = total
    db.session.commit()

    # Limpa o carrinho após a venda
    session.pop('carrinho')

    return redirect(url_for('historico'))

@app.route('/historico')
def historico():
    vendas = Venda.query.order_by(Venda.data.desc()).all()
    return render_template('historico.html', vendas=vendas)

@app.route('/venda/<int:id>')
def detalhes_venda(id):
    venda = Venda.query.get_or_404(id)
    itens = ItemVenda.query.filter_by(venda_id=id).all()

    # Recupera a observação diretamente do objeto venda, se existir no banco
    observacao = venda.observacao if hasattr(venda, 'observacao') else None

    return render_template('detalhes_venda.html', venda=venda, itens=itens, observacao=observacao)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)