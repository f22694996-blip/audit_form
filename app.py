import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe, get_as_dataframe

st.set_page_config(layout="wide") 
st.title("☁️ 稽核檢查自動化表單 (雲端協同作戰版)")

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

# --- 2. 載入設定 ---
def load_settings():
    try:
        df_set = get_as_dataframe(setting_sheet).dropna(how='all').dropna(axis=1, how='all')
        if not df_set.empty:
            if "檢查項目" in df_set.columns:
                st.session_state.inspection_items = [str(x) for x in df_set["檢查項目"].dropna() if str(x).strip()]
            for cat in ['建築', '土木', '機電']:
                if cat in df_set.columns:
                    st.session_state.sites[cat] = [str(x) for x in df_set[cat].dropna() if str(x).strip()]
    except: pass

# --- 3. 初始化 ---
if 'sites' not in st.session_state:
    st.session_state.sites = {'建築': ['惠國101', '合銘新店'], '土木': ['C211', 'C214'], '機電': ['劍潭多目標大樓']}
    st.session_state.inspection_items = ['管制標籤', '高度2M以下', '金屬繫材確實延伸', '跨坐勿站立頂板']
    load_settings() 

if 'results' not in st.session_state: st.session_state.results = {}
if 'reset_key' not in st.session_state: st.session_state.reset_key = 0

def reset_form():
    st.session_state.results, st.session_state.reset_key = {}, st.session_state.reset_key + 1
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
        st.session_state.inspection_items = clean_ls(ed_i["檢查項目"].tolist())
    with c2:
        st.subheader("2. 工地清單")
        site_tabs = st.tabs(['🏗️ 建築', '🛣️ 土木', '⚡ 機電'])
        for idx, cat in enumerate(['建築', '土木', '機電']):
            with site_tabs[idx]:
                df_s = pd.DataFrame({f"{cat}工地": st.session_state.sites[cat]})
                ed_s = st.data_editor(df_s, num_rows="dynamic", use_container_width=True, key=f"ed_{cat}")
                st.session_state.sites[cat] = clean_ls(ed_s[f"{cat}工地"].tolist())
            
    if st.button("💾 將以上設定儲存至雲端", use_container_width=True):
        with st.spinner('寫入雲端中...'):
            try:
                dict_series = {"檢查項目": pd.Series(st.session_state.inspection_items)}
                for c in ['建築', '土木', '機電']: dict_series[c] = pd.Series(st.session_state.sites[c])
                setting_sheet.clear()
                set_with_dataframe(setting_sheet, pd.DataFrame(dict_series))
                st.success("✅ 設定已永久儲存！")
            except Exception as e: st.error(f"儲存失敗: {e}")

# === 第一頁：表單填寫 ===
with tab1:
    col_t, col_b = st.columns([4, 1])
    col_t.header("📝 稽核檢查填寫")
    col_b.button("🔄 清空畫面重新填寫", on_click=reset_form, use_container_width=True)

    for cat, site_list in st.session_state.sites.items():
        if site_list:
            st.subheader(f"【{cat}】")
            for site in site_list:
                if not st.session_state.inspection_items: continue
                st.markdown(f"#### 🏗️ 工地：{site}")
                item_cols = st.columns(2) 
                for i, item in enumerate(st.session_state.inspection_items):
                    key = f"{cat}_{site}_{item}"
                    if key not in st.session_state.results: st.session_state.results[key] = None
                    cur = st.session_state.results[key]
                    idx = ['○', 'X', 'NA'].index(cur) if cur in ['○', 'X', 'NA'] else None
                    with item_cols[i % 2]:
                        st.session_state.results[key] = st.radio(f"📌 {item}", ['○', 'X', 'NA'], key=f"r_{key}_{st.session_state.reset_key}", index=idx, horizontal=True)
                st.divider()

    st.header("📊 完整全覽報表與雲端同步")
    rep = []
    for cat, s_list in st.session_state.sites.items():
        for s in s_list:
            x_items, row_base = [], {"工程類別": cat, "工地名稱": s}
            for it in st.session_state.inspection_items:
                v = st.session_state.results.get(f"{cat}_{s}_{it}")
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
        ed_final = st.data_editor(pd.DataFrame(rep), use_container_width=True, hide_index=True, disabled=list(pd.DataFrame(rep).columns[:-2]))
        
        col_dl, col_sync = st.columns(2)
        with col_dl:
            st.download_button("📥 1. 下載目前畫面稽核表", ed_final.to_csv(index=False).encode('utf-8-sig'), "稽核報表.csv", "text/csv", use_container_width=True)
            
        with col_sync:
            if st.button("☁️ 2. 智能合併同步至 Google 雲端", use_container_width=True):
                with st.spinner('正在比對合併中...'):
                    try:
                        try: cloud_df = get_as_dataframe(record_sheet).dropna(how='all').dropna(axis=1, how='all')
                        except: cloud_df = pd.DataFrame()
                        
                        merged_results, text_fields = {}, {}
                        
                        # 讀取雲端
                        if not cloud_df.empty and "工地名稱" in cloud_df.columns:
                            for _, row in cloud_df.iterrows():
                                s, cat = str(row.get("工地名稱", "")).strip(), str(row.get("工程類別", "")).strip()
                                if not s or s == "nan": continue
                                for it in st.session_state.inspection_items:
                                    if it in row and pd.notna(row[it]) and str(row[it]).strip():
                                        merged_results[f"{cat}_{s}_{it}"] = str(row[it]).strip()
                                xi = str(row.get("缺失項目", "")).strip()
                                if xi and xi != "nan":
                                    desc, impr = str(row.get("缺失描述", "")).strip(), str(row.get("改善情形", "")).strip()
                                    text_fields[f"{cat}_{s}_{xi}"] = {"缺失描述": desc if desc != "nan" else "", "改善情形": impr if impr != "nan" else ""}
                                            
                        # 疊加本地
                        for k, v in st.session_state.results.items():
                            if v is not None and str(v).strip(): merged_results[k] = v
                                
                        if not ed_final.empty and "工地名稱" in ed_final.columns:
                            for _, row in ed_final.iterrows():
                                s, cat, xi = str(row.get("工地名稱", "")).strip(), str(row.get("工程類別", "")).strip(), str(row.get("缺失項目", "")).strip()
                                if s and s != "nan" and xi and xi != "nan":
                                    desc, impr = str(row.get("缺失描述", "")).strip(), str(row.get("改善情形", "")).strip()
