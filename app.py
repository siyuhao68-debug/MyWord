import streamlit as st
import pandas as pd
import requests
import hashlib
import time
import random
from io import BytesIO

# ================= 🔧 填入你的有道 API 密钥 =================
# 注册有道智云(ai.youdao.com) 文本翻译服务后获取
YOUDAO_APP_KEY = st.secrets["YOUDAO_APP_KEY"] 
YOUDAO_APP_SECRET = st.secrets["YOUDAO_APP_SECRET"]
# =========================================================

st.set_page_config(page_title="背单词助手", page_icon="⭐")
st.title("⭐ 背单词小助手")
st.write("输入英文或中文，按回车或点击查询！")

# 初始化后台仓库
if "word_list" not in st.session_state:
    st.session_state.word_list = []

# 🧠 定义有道翻译的函数（包含签名加密逻辑）
def fetch_translation(query):
    if YOUDAO_APP_KEY == "YOUR_APP_KEY":
        st.warning("⚠️ 请先在代码中配置你的 YOUDAO_APP_KEY 和 APP_SECRET！")
        return None
    
    url = "https://openapi.youdao.com/api"
    salt = str(random.randint(1, 65536))
    curtime = str(int(time.time()))
    
    # 签名算法：sign = sha256(appKey + input(query) + salt + curtime + appSecret)
    # 针对长文本有道的特殊处理
    input_str = query
    if len(input_str) > 20:
        input_str = input_str[0:10] + str(len(input_str)) + input_str[-10:]
        
    sign_str = YOUDAO_APP_KEY + input_str + salt + curtime + YOUDAO_APP_SECRET
    sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
    
    # 构建请求参数
    params = {
        'q': query,
        'from': 'auto',
        'to': 'auto',
        'appKey': YOUDAO_APP_KEY,
        'salt': salt,
        'sign': sign,
        'signType': 'v3',
        'curtime': curtime,
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json() # 解析返回的 JSON 数据
        
        if data.get("errorCode") == "0":
            # 提取翻译结果
            translation = data.get("translation", [""])[0]
            
            # 提取词性和详细释义（如果有的话）
            explains = ""
            basic = data.get("basic")
            if basic and "explains" in basic:
                explains = " | ".join(basic["explains"])
                
            # 如果有详细释义就用详细的，没有就用普通翻译结果
            final_meaning = explains if explains else translation
            return final_meaning
        else:
            st.error(f"API 报错，错误码: {data.get('errorCode')}。请检查密钥或账户余额。")
            return None
    except Exception as e:
        st.error(f"网络请求失败: {e}")
        return None

# 📥 界面输入部分
search_query = st.text_input("🔍 输入你想查询/记录的单词或中文（输完敲回车）：")

# 临时存储查到的结果
if search_query:
    with st.spinner("正在安全连接有道服务器..."):
        translated_result = fetch_translation(search_query)
    
    if translated_result:
        st.info(f"💡 自动查询结果：{translated_result}")
        
        # 让用户补充例句（可选）
        example = st.text_area("💡 添加自定义例句（可选）：", key="example_input")
        
        # 确认添加按钮
        if st.button("确认将此单词加入 Excel 本"):
            # 自动判断输入的类型是英文还是中文，简单分流
            is_english = search_query.isascii()
            new_data = {
                "单词/原文": search_query if is_english else translated_result,
                "中文释义": translated_result if is_english else search_query,
                "例句": example
            }
            st.session_state.word_list.append(new_data)
            st.success(f"已成功写入仓库！")

# 📊 展现与导出表格
if st.session_state.word_list:
    st.write("---")
    st.subheader("📊 我的单词本")
    df = pd.DataFrame(st.session_state.word_list)
    st.dataframe(df)
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='单词库')
    
    st.download_button(
        label="📥 导出为 Excel",
        data=buffer.getvalue(),
        file_name="网安记忆本.xlsx",
        mime="application/vnd.ms-excel"
    )
