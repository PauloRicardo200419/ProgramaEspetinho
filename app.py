from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify,send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import pytz
from werkzeug.utils import secure_filename
import os
import pandas as pd
from io import BytesIO  # Certifique-se de importar BytesIO
from sqlalchemy import exc  # Importe para tratar exceções do banco


UPLOAD_FOLDER = os.path.join('static', 'uploads')

# Defina o fuso horário para o horário de Brasília
timezone = pytz.timezone('America/Sao_Paulo')

# Obtém a data e hora atual com o fuso horário correto
datetime.now(timezone)


app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Cria o diretório de uploads se ele não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.secret_key = 'laucher1'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    imagem = db.Column(db.String(255))
    itens_venda = db.relationship('ItemVenda', back_populates='produto')

    @property
    def estoque_dinamico(self):
        """
        Calcula o estoque disponível com base nos insumos associados.
        Retorna o menor número de produtos que podem ser feitos com os insumos disponíveis.
        """
        if not self.insumos_associados:
            return 0  # Retorna 0 se não houver insumos associados

        estoque_possivel = float('inf')  # Começa com um valor muito alto
        for produto_insumo in self.insumos_associados:
            insumo = produto_insumo.insumo
            if insumo.quantidade > 0:
                # Calcula quantos produtos podem ser feitos com o insumo disponível
                estoque_com_insumo = insumo.quantidade // produto_insumo.quantidade_necessaria
                estoque_possivel = min(estoque_possivel, estoque_com_insumo)
            else:
                return 0  # Se algum insumo estiver zerado, o estoque é 0

        return int(estoque_possivel)

class Insumo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    unidade = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    custo = db.Column(db.Float, nullable=False)

class ProdutoInsumo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumo.id'), nullable=False)
    quantidade_necessaria = db.Column(db.Float, nullable=False)

    produto = db.relationship('Produto', backref=db.backref('insumos_associados', cascade='all, delete-orphan'))
    insumo = db.relationship('Insumo', backref=db.backref('produtos_usando', cascade='all, delete-orphan'))



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
        nome = request.form.get('nome')
        preco = request.form.get('preco')
        imagem = request.files.get('imagem')

        # Salvar a imagem no diretório de uploads
        imagem_nome = None
        if imagem:
            imagem_nome = secure_filename(imagem.filename)
            imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_nome))

        # Criar o novo produto
        novo_produto = Produto(
            nome=nome,
            preco=float(preco),
            imagem=imagem_nome
        )
        db.session.add(novo_produto)
        db.session.flush()  # Garante que o ID do produto esteja disponível

        # Adicionar insumos associados
        insumos_associados_form = request.form.getlist('insumo_id[]')
        quantidades = request.form.getlist('quantidade_necessaria[]')

        for i in range(len(insumos_associados_form)):
            if insumos_associados_form[i] and quantidades[i]:
                insumo_id = int(insumos_associados_form[i])
                quantidade_necessaria = float(quantidades[i])
                produto_insumo = ProdutoInsumo(produto_id=novo_produto.id, insumo_id=insumo_id, quantidade_necessaria=quantidade_necessaria)
                db.session.add(produto_insumo)

        db.session.commit()

        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('produtos'))

    produtos = Produto.query.all()
    insumos = Insumo.query.all()
    return render_template('produtos.html', produtos=produtos, insumos=insumos)




#Editar produto 

@app.route('/produto/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    produto = Produto.query.get_or_404(id)
    insumos = Insumo.query.all()
    insumos_associados = ProdutoInsumo.query.filter_by(produto_id=produto.id).all()

    if request.method == 'POST':
        nome = request.form['nome']
        preco = request.form['preco']
        imagem = request.files.get('imagem')

        # Atualizar as informações do produto
        produto.nome = nome
        produto.preco = float(preco)

        # Atualizar a imagem, se fornecida
        if imagem:
            imagem_nome = secure_filename(imagem.filename)
            imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_nome))
            produto.imagem = imagem_nome

        # Atualizar ou adicionar os insumos associados
        insumos_associados_form = request.form.getlist('insumo_id[]')
        quantidades = request.form.getlist('quantidade_necessaria[]')

        for i in range(len(insumos_associados_form)):
            if insumos_associados_form[i] and quantidades[i]:  # Verifica se os valores não estão vazios
                insumo_id = int(insumos_associados_form[i])
                quantidade_necessaria = float(quantidades[i])

                # Verifica se a associação já existe
                assoc = ProdutoInsumo.query.filter_by(produto_id=produto.id, insumo_id=insumo_id).first()
                if assoc:
                    assoc.quantidade_necessaria = quantidade_necessaria  # Atualiza a quantidade
                else:
                    # Cria uma nova associação
                    produto_insumo = ProdutoInsumo(produto_id=produto.id, insumo_id=insumo_id, quantidade_necessaria=quantidade_necessaria)
                    db.session.add(produto_insumo)

        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('editar_produto', id=produto.id))

    return render_template('editar_produto.html', produto=produto, insumos=insumos, insumos_associados=insumos_associados)

@app.route('/remover_insumo/<int:id>', methods=['POST'])
def remover_insumo(id):
    print(f"ID recebido para remoção: {id}")  # Log para depuração
    try:
        assoc = ProdutoInsumo.query.get_or_404(id)
        produto_id = assoc.produto_id
        db.session.delete(assoc)
        db.session.commit()
        flash('Insumo removido com sucesso!', 'success')
        return redirect(url_for('editar_produto', id=produto_id))
    except Exception as e:
        print(f"Erro ao remover insumo: {e}")  # Log do erro
        flash(f'Erro ao remover insumo: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('produtos'))






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

@app.route('/insumos', methods=['GET', 'POST'])
def insumos():
    if request.method == 'POST':
        nome = request.form['nome']
        unidade = request.form['unidade']
        quantidade = request.form['quantidade']  # <- Alterado para 'quantidade'
        custo = request.form['custo']

        # Aqui você pode salvar no banco de dados
        novo_insumo = Insumo(nome=nome, unidade=unidade, quantidade=quantidade, custo=custo)  # <- Alterado para 'quantidade'
        db.session.add(novo_insumo)
        db.session.commit()

        return redirect(url_for('insumos'))

    insumos = Insumo.query.all()
    return render_template('insumos.html', insumos=insumos)




@app.route('/editar_insumo/<int:id>', methods=['GET', 'POST'])
def editar_insumo(id):
    insumo = Insumo.query.get(id)

    if request.method == 'POST':
        insumo.nome = request.form['nome']
        insumo.quantidade = int(request.form['quantidade'])
        insumo.unidade = request.form['unidade']
        db.session.commit()
        return redirect(url_for('insumos'))
    
    return render_template('editar_insumo.html', insumo=insumo)


@app.route('/adicionar_estoque_insumo/<int:id>', methods=['GET', 'POST'])
def adicionar_estoque_insumo(id):
    insumo = Insumo.query.get(id)

    if request.method == 'POST':
        adicional = int(request.form['quantidade'])
        insumo.quantidade += adicional
        db.session.commit()
        return redirect(url_for('insumos'))
    
    return render_template('adicionar_estoque_insumo.html', insumo=insumo)


@app.route('/deletar_insumo/<int:id>', methods=['POST'])
def deletar_insumo(id):
    insumo = Insumo.query.get(id)
    db.session.delete(insumo)
    db.session.commit()
    return redirect(url_for('insumos'))

@app.route('/produto_insumo', methods=['GET', 'POST'])
def produto_insumo():
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        insumo_id = request.form['insumo_id']
        quantidade = request.form['quantidade']
        nova_assoc = ProdutoInsumo(produto_id=produto_id, insumo_id=insumo_id, quantidade_necessaria=quantidade)
        db.session.add(nova_assoc)
        db.session.commit()
        return redirect(url_for('produto_insumo'))

    associacoes = ProdutoInsumo.query.all()
    produtos = Produto.query.all()
    insumos = Insumo.query.all()
    return render_template('produto_insumo.html', associacoes=associacoes, produtos=produtos, insumos=insumos)

@app.route('/deletar_associacao/<int:id>', methods=['POST'])
def deletar_associacao(id):
    assoc = ProdutoInsumo.query.get_or_404(id)
    db.session.delete(assoc)
    db.session.commit()
    return redirect(url_for('produto_insumo'))

@app.route('/api/search_insumos', methods=['GET'])
def search_insumos():
    query = request.args.get('query', '')
    if query:
        # Pesquisa no banco de dados pelo nome do insumo
        insumos = Insumo.query.filter(Insumo.nome.ilike(f'%{query}%')).all()
        # Retorna os insumos encontrados em formato JSON
        return jsonify([{'id': insumo.id, 'nome': insumo.nome} for insumo in insumos])
    return jsonify([])



#Venda

@app.route('/venda', methods=['GET', 'POST'])
def venda():
    produtos = Produto.query.all()
    carrinho_exibicao = []
    total = 0

    for item in session.get('carrinho', []):
        produto_id = item['produto_id']
        produto = Produto.query.get(produto_id)
        if produto:
            imagem = produto.imagem if produto.imagem else 'sem-imagem.png'
            caminho_imagem = url_for('static', filename=f'uploads/{imagem}')
            carrinho_exibicao.append({
                'produto': produto,
                'quantidade': item['quantidade'],
                'imagem': caminho_imagem
            })
            total += produto.preco * item['quantidade']

    return render_template(
        'venda.html',
        produtos=produtos,
        carrinho=carrinho_exibicao,
        total=total,
        estoque_reservado=session.get('estoque_reservado', {})
    )


@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    produto_id = request.form.get('produto_id')
    quantidade = request.form.get('quantidade')

    if not produto_id or not quantidade:
        flash('Produto ou quantidade inválida.', 'danger')
        return redirect(url_for('venda'))

    try:
        produto_id = int(produto_id)
        quantidade = int(quantidade)
    except ValueError:
        flash('Produto ou quantidade inválida.', 'danger')
        return redirect(url_for('venda'))

    if quantidade <= 0:
        flash('A quantidade deve ser maior que zero.', 'warning')
        return redirect(url_for('venda'))

    produto = Produto.query.get(produto_id)
    if not produto:
        flash('Produto não encontrado.', 'danger')
        return redirect(url_for('venda'))

    estoque_disponivel = produto.estoque_dinamico - session.get('estoque_reservado', {}).get(produto_id, 0)
    if quantidade > estoque_disponivel:
        flash(f'Estoque insuficiente para {produto.nome}.', 'danger')
        return redirect(url_for('venda'))

    # Adicionar ao carrinho
    carrinho = session.get('carrinho', [])
    for item in carrinho:
        if item['produto_id'] == produto_id:
            item['quantidade'] += quantidade
            break
    else:
        carrinho.append({'produto_id': produto_id, 'quantidade': quantidade})

    # Atualizar o estoque reservado
    estoque_reservado = session.get('estoque_reservado', {})
    estoque_reservado[produto_id] = estoque_reservado.get(produto_id, 0) + quantidade

    session['carrinho'] = carrinho
    session['estoque_reservado'] = estoque_reservado
    session.modified = True

    flash(f'{quantidade} unidade(s) de {produto.nome} adicionada(s) ao carrinho.', 'success')
    return redirect(url_for('venda'))


@app.route('/remover_item', methods=['POST'])
def remover_item():
    produto_id = request.form.get('produto_id')
    if not produto_id:
        flash('ID do produto não fornecido.', 'danger')
        return redirect(url_for('venda'))

    produto_id = int(produto_id)
    carrinho = session.get('carrinho', [])

    # Remove o item do carrinho
    session['carrinho'] = [item for item in carrinho if item['produto_id'] != produto_id]

    # Atualiza o estoque reservado
    estoque_reservado = session.get('estoque_reservado', {})
    if produto_id in estoque_reservado:
        del estoque_reservado[produto_id]
    session['estoque_reservado'] = estoque_reservado

    session.modified = True
    flash('Item removido do carrinho.', 'success')
    return redirect(url_for('venda'))


@app.route('/finalizar', methods=['POST'])
def finalizar():
    print("[/finalizar] Finalizando a venda...")

    carrinho = session.get('carrinho', [])
    if not carrinho:
        flash("Carrinho vazio. Adicione produtos antes de finalizar.", "warning")
        return redirect(url_for('venda'))

    total = 0
    for item in carrinho:
        produto = Produto.query.get(item['produto_id'])
        quantidade_vendida = item['quantidade']
        total += produto.preco * quantidade_vendida

        for produto_insumo in produto.insumos_associados:
            insumo = produto_insumo.insumo
            quantidade_necessaria = produto_insumo.quantidade_necessaria * quantidade_vendida
            if insumo.quantidade < quantidade_necessaria:
                flash(f"Insumo insuficiente para {produto.nome}.", "danger")
                return redirect(url_for('venda'))
            insumo.quantidade -= quantidade_necessaria

    nova_venda = Venda(total=total, observacao=request.form.get('observacao'))
    db.session.add(nova_venda)
    db.session.commit()

    session.pop('carrinho', None)
    session.pop('estoque_reservado', None)

    flash('Venda finalizada com sucesso!', 'success')
    return redirect(url_for('venda'))


@app.route('/historico')
def historico():
    # Obtenha o fuso horário de São Paulo (que é o mesmo de Franco da Rocha)
    timezone_sp = pytz.timezone('America/Sao_Paulo')
    # Obtenha a data atual no fuso horário de São Paulo
    data_atual_sp = datetime.now(timezone_sp).date().isoformat()
    vendas = Venda.query.order_by(Venda.data.desc()).all()
    return render_template('historico.html', vendas=vendas, data_atual_sp=data_atual_sp)

@app.route('/venda/<int:id>')
def detalhes_venda(id):
    venda = Venda.query.get_or_404(id)
    itens = ItemVenda.query.filter_by(venda_id=id).all()

    # Recupera a observação diretamente do objeto venda
    observacao = venda.observacao

    # Calcula o total da venda
    total = sum(item.preco_unitario * item.quantidade for item in itens)

    print(f"[/venda/{id}] Total calculado: {total}")  # Log para depuração

    return render_template('detalhes_venda.html', venda=venda, itens=itens, observacao=observacao, total=total)

def obter_vendas_do_banco(filtro_data=None):
    if filtro_data:
        # Filtra as vendas pela data
        return Venda.query.filter_by(data=filtro_data).all()
    else:
        # Retorna todas as vendas se não houver filtro
        return Venda.query.all()


@app.route('/gerar_relatorio_periodo')
def gerar_relatorio_periodo():
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    print(f"Período recebido: Início={data_inicio_str}, Fim={data_fim_str}")

    if not data_inicio_str or not data_fim_str:
        return "Por favor, forneça as datas de início e fim do período."

    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    except ValueError:
        return "Formato de data inválido."

    vendas_filtradas = Venda.query.filter(db.func.date(Venda.data) >= data_inicio,
                                            db.func.date(Venda.data) <= data_fim).order_by(Venda.data).all()
    print(f"Vendas filtradas para o período: {vendas_filtradas}")

    if not vendas_filtradas:
        return "Nenhuma venda encontrada para o período especificado."

    # Preparar os dados para o DataFrame
    dados_relatorio = []
    for venda in vendas_filtradas:
        for item in venda.itens:
            dados_relatorio.append({
                'ID Venda': venda.id,
                'Data': venda.data.strftime('%d/%m/%Y %H:%M:%S'),
                'Produto': item.produto.nome,
                'Quantidade': item.quantidade,
                'Preço Unitário': item.preco_unitario,
                'Total Item': item.quantidade * item.preco_unitario,
                'Total Venda': venda.total,
                'Observação': venda.observacao
            })

    df = pd.DataFrame(dados_relatorio)
    print("DataFrame criado para o período:")
    print(df)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Vendas', index=False)
    output.seek(0)
    print("Arquivo Excel do período gerado em memória.")

    return send_file(output, as_attachment=True, download_name="relatorio_vendas_periodo.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)