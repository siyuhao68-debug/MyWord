import streamlit as st
import pandas as pd
import requests
import hashlib
import time
import random
import json
import base64
from io import BytesIO

# ================= 🔧 自动读取 Streamlit 里的所有安全密钥 =================
YOUDAO_APP_KEY = st.secrets["YOUDAO_APP_KEY"] 
YOUDAO_APP_SECRET = st.secrets["YOUDAO_APP_SECRET"]

GH_TOKEN = st.secrets["GH_TOKEN"]
GH_REPO = st.secrets["GH_REPO"]
# =========================================================================

st.set_page_config(page_title="GitOps网安版背单词助手", page_icon="🛡️")
st.title("🛡️ 网安版背单词小助手")
st.write("✨ 当前状态：已联结 GitHub API 数据库！数据直接托管至云端代码仓库，永不丢失。")

# 📂 我们要把单词存在仓库里的哪个文件
DB_FILE_IN_REPO = "words_db.json"

# 🛠️ 核心函数 1：利用 GitHub API 远程读取文件
def load_data_from_github():
    url = f"https://api.github.com/repositories/YOUR_REPO_ID/contents/{DB_FILE_IN_REPO}" # 备用：可以直接用仓库名
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{DB_FILE_IN_REPO}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        file_json = response.json()
        # GitHub 返回的内容是 Base64 加密的，网安必学：我们需要解码它
        content_base64 = file_json["content"]
        content_str = base64.b64decode(content_base64).decode("utf-8")
        # 返回数据和这封文件的 sha 标识（更新文件时必须带上旧的 sha）
        return json.loads(content_str), file_json["sha"]
    else:
        # 如果文件还不存在，返回空列表和 None
        return [], None

# 🛠️ 核心函数 2：利用 GitHub API 远程提交文件（Commit）
def save_data_to_github(data_list, sha=None):
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{DB_FILE_IN_REPO}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 将 Python 列表转成规整的 json 字符串
    content_str = json.dumps(data_list, ensure_ascii=False, indent=4)
    # 网安实践：将字符串编码为 Base64 格式发送给 GitHub
    content_base64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": "🔄 手机端同步更新单词数据库 [Streamlit API]",
        "content": content_base64
    }
    if sha:
        payload["sha"] = sha  # 如果是更新已有文件，必须证明你看过旧文件
        
    response = requests.put(url, headers=headers, json=payload)
    return response.status_code in [200, 201]

# 🔄 初始化加载：利用网络请求直接去 GitHub 捞数据
if "word_list" not in st.session_state:
    with st.spinner("正在安全同步公网 GitHub 数据库..."):
        words, file_sha = load_data_from_github()
        st.session_state.word_list = words
        st.session_state.file_sha = file_sha

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
        
        if st.button("确认将此单词远程同步到 GitHub"):
            is_english = search_query.isascii()
            new_data = {
                "单词/原文": search_query if is_english else translated_result,
                "中文释义": translated_result if is_english else search_query,
                "例句": example
            }
            
            # 为了防止冲突，先上 GitHub 捞一把最新的
            current_list, current_sha = load_data_from_github()
            current_list.append(new_data)
            
            # 💾 核心落盘：强行推送到 GitHub 仓库
            with st.spinner("正在安全签名并向 GitHub 提交 Commit..."):
                if save_data_to_github(current_list, current_sha):
                    st.session_state.word_list = current_list
                    # 重新抓取最新 sha
                    _, next_sha = load_data_from_github()
                    st.session_state.file_sha = next_sha
                    st.success(f"🎉 完美的网络同步！Commit 成功，数据已安全存入 GitHub 仓库。")
                    st.rerun()
                else:
                    st.error("同步失败，请检查密钥权限。")

# 📊 展现与导出表格
if st.session_state.word_list:
    st.write("---")
    st.subheader("📊 我的云端单词本 (GitHub 实时托管)")
    df = pd.DataFrame(st.session_state.word_list)
    st.dataframe(df)
    
    # 一键擦除
    if st.button("🚨 彻底重置云端 GitHub 数据库"):
        _, current_sha = load_data_from_github()
        if save_data_to_github([], current_sha):
            st.session_state.word_list = []
            st.success("云端数据已彻底重置为初始空状态！")
            st.rerun()
        
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='单词库')
    
    st.download_button(label="📥 导出为 Excel", data=buffer.getvalue(), file_name="网安云端记忆本.xlsx", mime="application/vnd.ms-excel")
