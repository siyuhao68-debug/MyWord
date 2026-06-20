import streamlit as st
import pandas as pd
import requests
import hashlib
import time
import random
import json
import os
from io import BytesIO

# ================= 🔧 自动读取 Streamlit 里的有道 API 密钥 =================
YOUDAO_APP_KEY = st.secrets["YOUDAO_APP_KEY"] 
YOUDAO_APP_SECRET = st.secrets["YOUDAO_APP_SECRET"]
# =========================================================================

st.set_page_config(page_title="背单词助手", page_icon="⭐")
st.title("⭐ 背单词助手")
st.write("单词将永久存入【JSON文件数据库】中！")

# 📂 定义服务器本地文件数据库的路径
DB_FILE = "words_json_db.json"

# 🛠️ 核心函数 1：从 JSON 文件中读取数据
def load_data_from_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"读取数据库失败: {e}")
            return []
    return []

# 🛠️ 核心函数 2：将数据安全写入 JSON 文件
def save_data_to_db(data_list):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            # ensure_ascii=False 保证中文不会变成乱码
            json.dump(data_list, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"写入数据库失败: {e}")
        return False

# 🔄 初始化加载：每次刷新网页，直接去硬盘文件里捞数据
if "word_list" not in st.session_state:
    st.session_state.word_list = load_data_from_db()

# 🧠 定义有道翻译的函数（保持不变）
def fetch_translation(query):
    url = "https://openapi.youdao.com/api"
    salt = str(random.randint(1, 65536))
    curtime = str(int(time.time()))
    input_str = query if len(query) <= 20 else query[0:10] + str(len(query)) + query[-10:]
    sign_str = YOUDAO_APP_KEY + input_str + salt + curtime + YOUDAO_APP_SECRET
    sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
    
    params = {'q': query, 'from': 'auto', 'to': 'auto', 'appKey': YOUDAO_APP_KEY, 'salt': salt, 'sign': sign, 'signType': 'v3', 'curtime': curtime}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("errorCode") == "0":
            translation = data.get("translation", [""])[0]
            explains = " | ".join(data.get("basic", {}).get("explains", []))
            return explains if explains else translation
        return None
    except:
        return None

# 📥 界面输入
search_query = st.text_input("🔍 输入你想查询的单词或中文（输完敲回车）：")

if search_query:
    with st.spinner("正在安全连接有道服务器..."):
        translated_result = fetch_translation(search_query)
    
    if translated_result:
        st.info(f"💡 自动查询结果：{translated_result}")
        example = st.text_area("💡 添加自定义例句（可选）：", key="example_input")
        
        if st.button("确认将此单词加入永久文件数据库"):
            is_english = search_query.isascii()
            new_data = {
                "单词/原文": search_query if is_english else translated_result,
                "中文释义": translated_result if is_english else search_query,
                "例句": example
            }
            
            # 先读出最新的，防冲突
            current_list = load_data_from_db()
            current_list.append(new_data)
            
            # 💾 核心落盘操作：强行写入硬盘文件
            if save_data_to_db(current_list):
                st.session_state.word_list = current_list
                st.success(f"已成功落盘！数据已写入服务器安全区。")
                st.rerun()

# 📊 展现与导出表格
if st.session_state.word_list:
    st.write("---")
    st.subheader("📊 我的永久单词本")
    df = pd.DataFrame(st.session_state.word_list)
    st.dataframe(df)
    
    # 💥 一键擦除数据库文件数据
    if st.button("🚨 销毁并清空云端数据库"):
        if save_data_to_db([]):
            st.session_state.word_list = []
            st.success("数据已彻底粉碎性擦除！")
            st.rerun()
        
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='单词库')
    
    st.download_button(label="📥 导出为 Excel", data=buffer.getvalue(), file_name="网安记忆本.xlsx", mime="application/vnd.ms-excel")
