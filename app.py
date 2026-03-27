import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

st.set_page_config(layout="wide") 

# --- 0. 系統急救站 ---
with st.sidebar:
    st.header("🛠️ 系統維護")
    if st.button("🚨 強制重置系統"):
        st.session_state.clear()
        st.cache_resource.clear()
        st.rerun()

st.title("☁️ 稽核檢查自動化表單 (雲端協同版)")

# --- 1. 雲端連線 ---
@st.cache_resource
def init_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    key_dict = json.loads(st.secrets["json_key"])
    creds = Credentials.from_service_account_info(key_dict, scopes=scope)
    client = gspread.authorize(creds)
    # 👇 居米，請在這裡貼上你的_GOOGLE_SHEET_ID
    SHEET_ID = "1FDchd2MQ1KyUzcNkDM44YnDbpJ6_dBBmSIPoNqv1-tI" 
    sh = client.open_by_key(SHEET_ID)
    return sh.worksheet("Records"), sh.worksheet("Settings")

try:
    record_sheet, setting_sheet = init_connection()
except Exception as e:
    st.error(f"❌ 連線失敗！錯誤細節：{e}")
    st.stop()

# --- 2. 載入設定 (🔧 升級原生字典引擎，再也不吃資料) ---
def load_settings():
    try:
        data = setting_sheet.get_all_records()
        if data:
            df_set = pd.DataFrame(data)
            if "檢查項目" in df_set.columns:
                st.session_state.inspection_items = [str(x) for x in df_set["檢查項目"] if str(x).strip()]
            for cat in ['建築', '土木', '機電']:
                if cat in df_set.columns:
                    st.session_state.sites[cat] = [str(x) for x in df_set[cat] if str(x).strip()]
    except: pass

# --- 3. 初始化 ---
if 'sites' not in st.session_state:
    st.session_state.sites = {'建築': [], '土木': [], '機電': []}
    st.session_state.inspection_items = ['管制標籤', '高度2M以下', '金屬繫材確實延伸', '跨坐勿站立頂板']
    load_settings() 

if 'results' not in st.session_state: st.session_state.results = {}
if 'last_sync_results' not in st.session_state: st.session_state.last_sync_results = {}
if 'last_sync_texts' not in st.session_state: st.session_state.last_sync_texts = {}
if 'reset_key' not in st.session_state: st.session_state.reset_key = 0
if 'sync_success' not in st.session_state: st.session_state.sync_success = False

def reset_form():
    st.session_state.results = {}
    st.session_state.last_sync_results = {}
    st.session_state.last_sync_texts = {}
    st.session_state.reset_key += 1
    st.success("✨ 已清空本機畫面紀錄！")

def clean_ls(lst):
    return list(dict.fromkeys([str(x).strip() for x in lst if pd.notna(x) and str(x).strip()]))

tab1, tab2 = st.tabs(["📝 表單填寫", "⚙️ 後台設定"])

# === 第二頁：後台設定 ===
with tab2:
    st.header("⚙️ 系統設定")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. 檢查項目")
        df_i = pd.DataFrame({"檢查項目": st.session_state.inspection_items})
        ed_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True, key="ed_items")
        
    with c2:
        st.subheader("2. 工地清單")
        site_tabs = st.tabs(['🏗️ 建築', '🛣️ 土木', '⚡ 機電'])
        editors = {} 
        for idx, cat in enumerate(['建築', '土木', '機電']):
            with site_tabs[idx]:
                df_s = pd.DataFrame({f"{cat}工地": st.session_state.sites[cat]})
                editors[cat] = st.data_editor(df_s, num_rows="dynamic", use_container_width=True, key=f"ed_{cat}")
            
    if st.button("💾 將以上設定儲存至雲端", use_container_width=True):
        with st.spinner('寫入雲端中...'):
            try:
                st.session_state.inspection_items = clean_ls(ed_i["檢查項目"].tolist())
                for cat in ['建築', '土木', '機電']:
                    st.session_state.sites[cat] = clean_ls(editors[cat][f"{cat}工地"].tolist())
                    
                dict_series = {"檢查項目": pd.Series(st.session_state.inspection_items)}
                for c in ['建築', '土木', '機電']: dict_series[c] = pd.Series(st.session_state.sites[c])
                setting_sheet.clear()
                set_with_dataframe(setting_sheet, pd.DataFrame(dict_series), include_column_header=True)
                st.success("✅ 設定已永久儲存！")
            except Exception as e: st.error(f"儲存失敗: {e}")
            
    st.divider()
    st.subheader("🗑️ 雲端資料庫管理 (測試專用)")
    if st.button("🧨 徹底清空雲端填寫紀錄"):
        with st.spinner("正在清除雲端資料庫..."):
            try:
                record_sheet.clear()
                st.success("✅ 雲端資料庫已徹底清空！請切換到『表單填寫』點擊『🔄 清空畫面重新填寫』即可開始全新紀錄！")
