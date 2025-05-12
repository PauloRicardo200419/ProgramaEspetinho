from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

db = SQLAlchemy()

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


