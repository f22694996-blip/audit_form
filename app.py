import streamlit as st
import pandas as pd

# 讓網頁變寬，方便顯示完整的長表格
st.set_page_config(layout="wide") 
st.title("稽核檢查自動化表單 (專業進化版)")

# --- 1. 初始化資料 (Session State) ---
if 'sites' not in st.session_state:
    st.session_state.sites = {
        '建築': ['惠國101', '合銘新店'],
        '土木': ['C211', 'C214'],
        '機電': ['劍潭多目標大樓']
    }
if 'inspection_items' not in st.session_state:
    st.session_state.inspection_items = ['管制標籤', '高度2M以下', '金屬繫材確實延伸', '跨坐勿站立頂板']

# 紀錄每個選項的暫存區
if 'results' not in st.session_state:
    st.session_state.results = {}

# 清空本月紀錄的執行動作
def reset_form():
    st.session_state.results = {}
    st.success("已清空所有填寫紀錄，可以開始新的月份了！")

# --- 2. 建立雙分頁系統 ---
tab1, tab2 = st.tabs(["📝 表單填寫與產出", "⚙️ 後台設定區 (增刪排序)"])

# === 第二頁：後台設定區 (解決需求 1 & 4) ===
with tab2:
    st.header("⚙️ 系統設定")
    st.write("在這裡你可以自由修改文字、勾選左側的框框來刪除，或是點擊左側邊緣上下拖曳來【排列順序】。")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. 檢查項目管理")
        # 使用動態表格來管理檢查項目
        df_items = pd.DataFrame({"檢查項目": st.session_state.inspection_items})
        edited_items = st.data_editor(df_items, num_rows="dynamic", use_container_width=True, key="editor_items")
        # 即時更新記憶庫，並自動過濾掉空白的項目
        st.session_state.inspection_items = [item for item in edited_items["檢查項目"].tolist() if str(item).strip() != ""]

    with col2:
        st.subheader("2. 工地清單管理")
        for cat in ['建築', '土木', '機電']:
            st.markdown(f"**【{cat}】**")
            df_sites = pd.DataFrame({f"{cat}工地": st.session_state.sites[cat]})
            edited_sites = st.data_editor(df_sites, num_rows="dynamic", use_container_width=True, key=f"editor_{cat}")
            st.session_state.sites[cat] = [site for site in edited_sites[f"{cat}工地"].tolist() if str(site).strip() != ""]

# === 第一頁：表單填寫區 (解決需求 2) ===
with tab1:
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.header("📝 稽核檢查填寫")
    with col_btn:
        # 一鍵刷新按鈕
        st.button("🔄 一鍵清空本月紀錄", on_click=reset_form, use_container_width=True)

    st.write("請針對各工地的項目直接點選 ○、X 或 NA。")

    for cat, site_list in st.session_state.sites.items():
        if site_list:
            st.subheader(f"【{cat}】")
            for site in site_list:
                st.markdown(f"**工地：{site}**")
                
                # 防呆機制：如果沒有檢查項目就先跳過
                if not st.session_state.inspection_items:
                    st.warning("請先至「後台設定區」新增檢查項目。")
                    continue
                
                cols = st.columns(len(st.session_state.inspection_items))
                
                for i, item in enumerate(st.session_state.inspection_items):
                    key = f"{site}_{item}"
                    if key not in st.session_state.results:
                        st.session_state.results[key] = '○'
                    
                    st.session_state.results[key] = cols[i].radio(
                        item, 
                        ['○', 'X', 'NA'], 
                        key=f"radio_{key}",
                        index=['○', 'X', 'NA'].index(st.session_state.results[key])
                    )
                st.divider()

    # --- 底部：可編輯的互動式全覽表 ---
    st.header("📊 完整全覽報表")
    
    report_data = []
    for cat, site_list in st.session_state.sites.items():
        for site in site_list:
            x_items = []
            
            base_row = {"工程類別": cat, "工地名稱": site}
            for item in st.session_state.inspection_items:
                val = st.session_state.results.get(f"{site}_{item}", '○') # 如果找不到紀錄預設給圈
                base_row[item] = val
                if val == 'X':
                    x_items.append(item)
            
            if not x_items:
                row = base_row.copy()
                row["缺失工地"] = ""
                row["缺失項目"] = ""
                row["缺失描述"] = ""
                row["改善情形"] = ""
                report_data.append(row)
            else:
                for x_item in x_items:
                    row = base_row.copy()
                    row["缺失工地"] = site
                    row["缺失項目"] = x_item
                    row["缺失描述"] = "" 
                    row["改善情形"] = "" 
                    report_data.append(row)

    if report_data:
        df = pd.DataFrame(report_data)
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=["工程類別", "工地名稱", "缺失工地", "缺失項目"] + st.session_state.inspection_items
        )
        
        csv_data = edited_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載完整稽核表 (CSV格式)",
            data=csv_data,
            file_name="完整稽核報表.csv",
            mime="text/csv"
        )