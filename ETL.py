import streamlit as st
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# 创建streamlit应用程序
st.title('Blockchain Explorer')

plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

def fetch_blockchain():
    response = requests.get('http://127.0.0.1:5000/chain')
    if response.status_code == 200:
        return response.json()['chain']
    return None

# 初始化session_state
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = None
if 'df' not in st.session_state:
    st.session_state.df = None
if 'button_clicked' not in st.session_state:
    st.session_state.button_clicked = False

# 添加一个按钮，当点击时，发送GET请求到区块链的127.0.0.1/chain
if st.button('Fetch Blockchain'):
    st.session_state.blockchain = fetch_blockchain()
    st.session_state.button_clicked = True

if st.session_state.button_clicked:
    # 在streamlit上显示返回的整条区块链
    st.write(st.session_state.blockchain)

    # 提取区块链中每个块的transactions中的'category'和'text'
    categories = []
    texts = []
    for block in st.session_state.blockchain[1:]:
        categories.append(block['transactions'][0]['category'])
        texts.append(block['transactions'][0]['text'])

    # 使用pandas和seaborn库对'category'和'text'进行可视化
    st.session_state.df = pd.DataFrame({'Category': categories, 'Text': texts})

    st.write(st.session_state.df)

    if st.button('Show Category Count'):
        fig, ax = plt.subplots()
        sns.countplot(x='Category', data=st.session_state.df, ax=ax)
        st.pyplot(fig)

    if st.button('Show Texts by Category'):
        for category in st.session_state.df['Category'].unique():
            st.subheader(category)
            st.write(st.session_state.df[st.session_state.df['Category'] == category]['Text'].values)
