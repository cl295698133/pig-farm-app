import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# ------------------- 配置与数据 -------------------
st.set_page_config(page_title="猪场管家", page_icon="🐷", layout="centered", initial_sidebar_state="collapsed")

DATA_FILE = 'pig_data_mobile.csv'

def init_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=['BatchID', 'CurrentBarn', 'BirthDate', 'StartWeight', 'CurrentCount', 'Stage'])
        df.to_csv(DATA_FILE, index=False)
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 体重估算模型
def calculate_weight(age_days, stage):
    if age_days <= 21:
        return round(1.5 + (5.5 / 21) * age_days, 1)
    elif 22 <= age_days <= 70:
        return round(7 + (23 / 48) * (age_days - 21), 1)
    else:
        return round(115 / (1 + 10 * (2.718 ** (-0.03 * (age_days - 70)))), 1)

# ------------------- 界面开始 -------------------
st.title("🐷 猪场生产管家")

# 加载数据
df = init_data()

# 手机端：用底部标签页替代侧边栏
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 概览", "➕ 操作", "✏️ 校正", "📤 导出", "⚙️ 设置"])

# ------------------- 1. 概览页 -------------------
with tab1:
    st.subheader("实时存栏")
    
    # 手机端垂直展示各栋舍
    st.write("**🏠 产房 (1-6栋)**")
    for barn in [f"产房{i}" for i in range(1,7)]:
        cnt = df[df['CurrentBarn'] == barn]['CurrentCount'].sum()
        st.info(f"{barn}: {cnt} 头")
        
    st.write("**🏡 保育舍 (1-3栋)**")
    for barn in [f"保育{i}" for i in range(1,4)]:
        cnt = df[df['CurrentBarn'] == barn]['CurrentCount'].sum()
        st.info(f"{barn}: {cnt} 头")
        
    st.write("**🏭 育肥舍 (1-3栋)**")
    for barn in [f"育肥{i}" for i in range(1,4)]:
        cnt = df[df['CurrentBarn'] == barn]['CurrentCount'].sum()
        st.info(f"{barn}: {cnt} 头")

    # 批次详情
    st.subheader("批次详情")
    if not df.empty:
        df['TodayAge'] = (datetime.now() - pd.to_datetime(df['BirthDate'])).dt.days
        df['EstWeight(kg)'] = df.apply(lambda x: calculate_weight(x['TodayAge'], x['Stage']), axis=1)
        st.dataframe(df[['BatchID', 'CurrentBarn', 'TodayAge', 'EstWeight(kg)', 'CurrentCount']], use_container_width=True)
    else:
        st.write("暂无数据")

# ------------------- 2. 操作页 -------------------
with tab2:
    st.subheader("生产操作")
    action = st.radio("选择操作", ["断奶", "转群", "死亡", "售卖"], horizontal=True)
    
    # 1. 断奶
    if action == "断奶":
        with st.form("wean_form"):
            batch_id = st.text_input("批次号")
            from_barn = st.selectbox("来源产房", [f"产房{i}" for i in range(1,7)])
            to_barn = st.selectbox("转入保育舍", [f"保育{i}" for i in range(1,4)])
            birth_date = st.date_input("出生日期", datetime.now() - timedelta(days=21))
            count = st.number_input("头数", min_value=0, step=1)
            submitted = st.form_submit_button("✅ 确认断奶", use_container_width=True)
            if submitted:
                new_row = {'BatchID': batch_id, 'CurrentBarn': to_barn, 'BirthDate': birth_date, 'StartWeight': 7.0, 'CurrentCount': count, 'Stage': '保育期'}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                st.success("操作成功！")

    # 2. 转群
    elif action == "转群":
        nursery_batches = df[df['Stage'] == '保育期']['BatchID'].tolist()
        if nursery_batches:
            batch_id = st.selectbox("选择批次", nursery_batches)
            to_barn = st.selectbox("转入育肥舍", [f"育肥{i}" for i in range(1,4)])
            if st.button("✅ 确认转群", use_container_width=True):
                df.loc[df['BatchID'] == batch_id, 'CurrentBarn'] = to_barn
                df.loc[df['BatchID'] == batch_id, 'Stage'] = '育肥期'
                save_data(df)
                st.success("转群成功！")
        else:
            st.warning("暂无保育猪")

    # 3. 死亡
    elif action == "死亡":
        barn_type = st.selectbox("栋舍类型", ["产房", "保育舍", "育肥舍"])
        barns = [f"{barn_type}{i}" for i in range(1, 4 if barn_type != "产房" else 7)]
        selected_barn = st.selectbox("选择栋舍", barns)
        barn_batches = df[df['CurrentBarn'] == selected_barn]['BatchID'].tolist()
        if barn_batches:
            batch_id = st.selectbox("批次", barn_batches)
            death_cnt = st.number_input("死亡头数", min_value=0, step=1)
            if st.button("✅ 记录死亡", use_container_width=True):
                current = df.loc[df['BatchID'] == batch_id, 'CurrentCount'].values[0]
                df.loc[df['BatchID'] == batch_id, 'CurrentCount'] = current - death_cnt
                save_data(df)
                st.success("记录成功！")

    # 4. 售卖
    elif action == "售卖":
        fatten_batches = df[df['Stage'] == '育肥期']['BatchID'].tolist()
        if fatten_batches:
            batch_id = st.selectbox("批次", fatten_batches)
            sell_cnt = st.number_input("售卖头数", min_value=0, step=1)
            if st.button("✅ 确认售卖", use_container_width=True):
                current = df.loc[df['BatchID'] == batch_id, 'CurrentCount'].values[0]
                df.loc[df['BatchID'] == batch_id, 'CurrentCount'] = current - sell_cnt
                df = df[df['CurrentCount'] > 0]
                save_data(df)
                st.success("售卖成功！")

# ------------------- 3. 数据校正 -------------------
with tab3:
    st.subheader("数据校正")
    if not df.empty:
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if st.button("💾 保存修改", use_container_width=True):
            save_data(edited_df)
            st.success("已保存！")

# ------------------- 4. 导出 -------------------
with tab4:
    st.subheader("导出数据")
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下载CSV文件", data=csv, file_name=f"猪场数据_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv', use_container_width=True)

# ------------------- 5. 设置 -------------------
with tab5:
    st.subheader("系统设置")
    if st.button("🗑️ 清除所有数据", use_container_width=True, type="primary"):
        st.warning("请再次确认")
        if st.button("确认清除 (不可恢复)", use_container_width=True):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            st.success("数据已重置")