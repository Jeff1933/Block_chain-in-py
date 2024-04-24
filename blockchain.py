import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request, render_template
import requests

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        # 创建创世区块
        self.new_block(previous_hash=1, proof=100)
    
    def valid_chain(self, chain):
        """
        判断给定的区块链是否有效
        :param chain: <list> 区块链
        :return: <bool> 如果有效返回True，否则返回False
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # 检查区块的哈希是否正确
            if block['previous_hash'] != self.hash(last_block):
                return False

            # 检查工作量证明是否正确
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        这是我们的共识算法，它通过用网络中最长的链替换我们的链来解决冲突。
        :return: <bool> 如果我们的链被替换返回True，否则返回False
        """

        neighbours = self.nodes
        new_chain = None

        # 我们只寻找比我们链更长的链
        max_length = len(self.chain)

        # 从网络中的所有节点获取并验证链
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # 检查链的长度是否更长且链是否有效
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # 如果我们发现了一条新的、有效的链，就替换我们的链
        if new_chain:
            self.chain = new_chain
            return True

        return False
    
    def register_node(self, address):
        """
        将新节点添加到节点列表中
        :param address: <str> 节点的地址。例如：'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
    
    
    def new_block(self, proof, previous_hash=None):
        # 创建一个新的区块并将其添加到链中
        """
        在区块链中创建一个新的区块
        :param proof: <int> 工作量证明算法给出的证明
        :param previous_hash: (可选) <str> 上一个区块的哈希值
        :return: <dict> 新的区块
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # 重置当前交易列表
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, category, text):
        # 将新的交易添加到交易列表中
        """
        创建一个新的交易以便放入下一个挖掘的区块中
        :param sender: 发送者的地址
        :param recipient: 接收者的地址
        :param amount: 金额
        :return: 将包含此交易的区块的索引
        """
        
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'category': category,
            'text': text,
        })
        
        return self.last_block['index'] + 1

    def proof_of_work(self, last_proof):
        """
        简单的工作量证明算法：
         - 找到一个数p'，使得hash(pp')的前4位为0，其中p是上一个p'
         - p是上一个证明，p'是新的证明
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof
    
    @staticmethod
    def valid_proof(last_proof, proof):
        """
        验证工作量证明：hash(last_proof, proof)的前4位是否为0？
        :param last_proof: <int> 上一个证明
        :param proof: <int> 当前证明
        :return: <bool> 如果正确返回True，否则返回False
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    
    @staticmethod
    def hash(block):
        # 对一个区块进行哈希运算
        """
        创建一个区块的SHA-256哈希值
        :param block: <dict> 区块
        :return: <str>
        """

        # 我们必须确保字典是有序的，否则哈希值会不一致
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # 返回链中的最后一个区块
        return self.chain[-1]
    

# 实例化节点
app = Flask(__name__)

# 为此节点生成一个全局唯一的地址
node_identifier = str(uuid4()).replace('-', '')

# 实例化区块链
blockchain = Blockchain()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/mine', methods=['GET'])
def mine():
    # 运行工作量证明算法以获取下一个证明...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 我们必须获得找到证明的奖励。
    # 发送者为"0"表示此节点挖掘了一个新的币。
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        category='WEB3',
        text='Talk what you want'
    )

    # 通过将其添加到链中来创建新的区块
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "新的区块已经生成",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200
  
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # 检查POST数据中是否包含所需的字段
    required = ['sender', 'recipient', 'category', 'text']
    if not all(k in values for k in required):
        return '缺少字段', 400

    # 创建一个新的交易
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['category'], values['text'])

    response = {'message': f'交易将被添加到区块 {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "错误：请提供有效的节点列表", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': '新的节点已添加',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': '我们的链已被替换',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': '我们的链是权威的',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
