import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe, get_as_dataframe

st.set_page_config(layout="wide") 
st.title("☁️ 稽核檢查自動化表單 (雲端協同作戰版)")

# --- 1. 雲端連線設定 ---
@st.cache_resource
def init_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    key_dict = json.loads(st.secrets["json_key"])
    creds = Credentials.from_service_account_info(key_dict, scopes=scope)
    return gspread.authorize(creds)

try:
    client = init_connection()
    # 👇 居米，請在這裡貼上你的_GOOGLE_SHEET_ID
    SHEET_ID = "1FDchd2MQ1KyUzcNkDM44YnDbpJ6_dBBmSIPoNqv1-tI" 
    sh = client.open_by_key(SHEET_ID)
    record_sheet = sh.worksheet("Records")
except Exception as e:
    st.error(f"❌ 連線失敗！請檢查 Secrets 設定或是 SHEET_ID 是否正確。錯誤細節：{e}")
    st.stop()

# --- 2. 初始化資料 ---
if 'sites' not in st.session_state:
    st.session_state.sites = {'建築': ['惠國101', '合銘新店'], '土木': ['C211', 'C214'], '機電': ['劍潭多目標大樓']}
if 'inspection_items' not in st.session_state:
    st.session_state.inspection_items = ['管制標籤', '高度2M以下', '金屬繫材確實延伸', '跨坐勿站立頂板']
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'reset_key' not in st.session_state:
    st.session_state.reset_key = 0

def reset_form():
    st.session_state.results = {}
    st.session_state.reset_key += 1
    st.success("✨ 已成功清空本機畫面紀錄！")

def clean_and_unique(input_list):
    cleaned = [str(x).strip() for x in input_list if pd.notna(x) and str(x).strip() != ""]
    return list(dict.fromkeys(cleaned))

tab1, tab2 = st.tabs(["📝 表單填寫", "⚙️ 後台設定"])

# === 第二頁：後台設定 ===
with tab2:
    st.header("⚙️ 系統設定")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. 檢查項目")
        df_i = pd.DataFrame({"檢查項目": st.session_state.inspection_items})
        ed_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True, key="ed_items")
        st.session_state.inspection_items = clean_and_unique(ed_i["檢查項目"].tolist())
    with c2:
        st.subheader("2. 工地清單")
        for cat in ['建築', '土木', '機電']:
            df_s = pd.DataFrame({f"{cat}工地": st.session_state.sites[cat]})
            ed_s = st.data_editor(df_s, num_rows="dynamic", use_container_width=True, key=f"ed_{cat}")
            st.session_state.sites[cat] = clean_and_unique(ed_s[f"{cat}工地"].tolist())

# === 第一頁：表單填寫 ===
with tab1:
    col_t, col_b = st.columns([4, 1])
    col_t.header("📝 稽核檢查填寫")
    col_b.button("🔄 清空畫面重新填寫", on_click=reset_form, use_container_width=True)

    for cat, site_list in st.session_state.sites.items():
        if site_list:
            st.subheader(f"【{cat}】")
            for site in site_list:
                st.markdown(f"#### 🏗️ 工地：{site}")
                if not st.session_state.inspection_items:
                    continue
                
                item_cols = st.columns(2) 
                for i, item in enumerate(st.session_state.inspection_items):
                    key = f"{site}_{item}"
                    if key not in st.session_state.results: st.session_state.results[key] = None
                    cur = st.session_state.results[key]
                    idx = ['○', 'X', 'NA'].index(cur) if cur in ['○', 'X', 'NA'] else None
                    u_key = f"r_{key}_{st.session_state.reset_key}"
                    
                    with item_cols[i % 2]:
                        st.session_state.results[key] = st.radio(
                            f"📌 {item}", 
                            ['○', 'X', 'NA'], 
                            key=u_key, 
                            index=idx, 
                            horizontal=True
                        )
                st.divider()

    st.header("📊 完整全覽報表與雲端同步")
    rep = []
    for cat, s_list in st.session_state.sites.items():
        for s in s_list:
            x_items = []
            row_base = {"工程類別": cat, "工地名稱": s}
            for it in st.session_state.inspection_items:
                v = st.session_state.results.get(f"{s}_{it}")
                row_base[it] = v if v else ""
                if v == 'X': x_items.append(it)
            if not x_items:
                r = row_base.copy()
                r.update({"缺失工地":"", "缺失項目":"", "缺失描述":"", "改善情形":""})
                rep.append(r)
            else:
                for xi in x_items:
                    r = row_base.copy()
                    r.update({"缺失工地":s, "缺失項目":xi, "缺失描述":"", "改善情形":""})
                    rep.append(r)
                    
    if rep:
        df_final = pd.DataFrame(rep)
        ed_final = st.data_editor(df_final, use_container_width=True, hide_index=True, disabled=list(df_final.columns[:-2]))
        
        st.write("填寫完畢後，你可以選擇下載檔案，或是直接同步到 Google 雲端讓團隊共用。")
        col_dl, col_sync = st.columns(2)
        with col_dl:
            csv = ed_final.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 1. 下載目前畫面稽核表", data=csv, file_name="稽核報表.csv", mime="text/csv", use_container_width=True)
            
        with col_sync:
            if st.button("☁️ 2. 智能合併同步至 Google 雲端", use_container_width=True):
                with st.spinner('正在與雲端資料智能比對合併中...'):
                    try:
                        # 1. 下載最新雲端資料
                        try:
                            cloud_df = get
