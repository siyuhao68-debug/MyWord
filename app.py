import streamlit as st
import pandas as pd
import requests
import hashlib
import time
import random
import json
from io import BytesIO
from streamlit_local_storage import LocalStorage

# ================= 🔧 自动读取 Streamlit 里的有道 API 密钥 =================
YOUDAO_APP_KEY = st.secrets["YOUDAO_APP_KEY"] 
YOUDAO_APP_SECRET = st.secrets["YOUDAO_APP_SECRET"]
# =========================================================================

st.set_page_config(page_title="背单词助手", page_icon="⭐")
st.title("⭐ 背单词助手")
st.write("输入英文或中文，系统自动查询并【永久保存】在你的当前设备中！")

# 🔒 初始化浏览器本地缓存大管家
local_storage = LocalStorage()

# 从手机/电脑的浏览器缓存中加载已经保存的单词
stored_words_raw = local_storage.getItem("my_permanent_words")
if stored_words_raw:
    try:
        # 浏览器里存的是字符串，我们需要反序列化为 Python 列表
        st.session_state.word_list = json.loads(stored_words_raw)
    except:
        st.session_state.word_list = []
else:
    st.session_state.word_list = []

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
search_query = st.text_input("🔍 输入你想查询/记录的单词或中文（输完敲回车）：")

if search_query:
    with st.spinner("正在安全连接有道服务器..."):
        translated_result = fetch_translation(search_query)
    
    if translated_result:
        st.info(f"💡 自动查询结果：{translated_result}")
        example = st.text_area("💡 添加自定义例句（可选）：", key="example_input")
        
        if st.button("确认将此单词加入持久化仓库"):
            is_english = search_query.isascii()
            new_data = {
                "单词/原文": search_query if is_english else translated_result,
                "中文释义": translated_result if is_english else search_query,
                "例句": example
            }
            # 把新单词加进列表
            st.session_state.word_list.append(new_data)
            
            # 💾 核心步骤：将最新的列表转成字符串，强制写入浏览器的本地保险箱
            local_storage.setItem("my_permanent_words", json.dumps(st.session_state.word_list))
            
            st.success(f"已成功写入本地持久化仓库！网页刷新也不会丢了！")
            st.rerun() # 刷新页面展示新数据

# 📊 展现与导出表格
if st.session_state.word_list:
    st.write("---")
    st.subheader("📊 我的永久单词本")
    df = pd.DataFrame(st.session_state.word_list)
    st.dataframe(df)
    
    # 增加一个清空水池的按钮（防止垃圾数据太多）
    if st.button("🚨 清空所有本地记录"):
        local_storage.setItem("my_permanent_words", "[]")
        st.success("本地缓存已安全擦除！")
        st.rerun()
        
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='单词库')
    
    st.download_button(label="📥 导出为 Excel", data=buffer.getvalue(), file_name="网安记忆本.xlsx", mime="application/vnd.ms-excel")
