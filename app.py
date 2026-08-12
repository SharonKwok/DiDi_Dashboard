import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 設定頁面寬闊模式
st.set_page_config(page_title="DiDi Promo Dashboard", layout="wide")

# ==========================================
# 1. 模擬資料生成 (模擬 DiDi 的自動化後台數據)
# ==========================================
# 假設這是後台自動清洗好的資料，不再需要 Excel 拼湊
data = {
    'Batch_ID': ['#MEL_WKND'] * 3 + ['#SYD_RAIN'] * 3,
    'Voucher_Tier': ['10% Off', '20% Off', '50% Off', '10% Off', '20% Off', '50% Off'],
    'Clicks': [15000, 18000, 25000, 8000, 12000, 20000],
    'Redeemed': [5000, 10000, 22000, 3000, 8000, 18000],
    'Actual_Trips': [1500, 4500, 18000, 1000, 4000, 15000],
    'Avg_Usage_Per_User': [1.2, 1.8, 2.5, 1.1, 1.5, 2.1]
}
df = pd.DataFrame(data)

# ==========================================
# 2. 側邊欄設計 (Sidebar)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/DiDi_logo.svg/2560px-DiDi_logo.svg.png", width=150)
st.sidebar.title("Data Filters")
time_granularity = st.sidebar.radio("Time Granularity (時間維度):", ["Daily / Weekly (Operations)", "Monthly / YoY (Marketing)"])
selected_batch = st.sidebar.selectbox("Select Campaign Batch ID:", df['Batch_ID'].unique())

# ==========================================
# 3. 主畫面與 KPI 卡片 (Top KPIs)
# ==========================================
st.title("📊 Promotional Performance Dashboard")
st.markdown("Automated insights replacing manual Excel Batch ID calculations.")

# 篩選所選的活動資料
filtered_df = df[df['Batch_ID'] == selected_batch]
total_clicks = filtered_df['Clicks'].sum()
total_trips = filtered_df['Actual_Trips'].sum()
true_conversion = (total_trips / total_clicks) * 100
avg_usage = filtered_df['Avg_Usage_Per_User'].mean()

# 顯示 KPI 卡片
col1, col2, col3 = st.columns(3)
col1.metric("Total Actual Trips", f"{total_trips:,}")
col2.metric("True Trip Conversion Rate", f"{true_conversion:.1f}%", "Effectiveness Metric")
col3.metric("Avg Usage per Customer", f"{avg_usage:.2f}", "Habit Building Metric")

st.markdown("---")

# ==========================================
# 4. 核心圖表區 (Core Visualisations)
# ==========================================
col_left, col_right = st.columns(2)

# 圖表 A: 三階段歸因漏斗 (3-Stage Attribution Funnel)
# 背書: Rust et al. 2004 (Marketing Productivity Chain)
with col_left:
    st.subheader("1. 3-Stage Attribution Funnel")
    funnel_data = dict(
        Stage=['1. Ad Clicks (Awareness)', '2. Vouchers Redeemed (Intent)', '3. Actual Trips (Conversion)'],
        Value=[total_clicks, filtered_df['Redeemed'].sum(), total_trips]
    )
    fig_funnel = px.funnel(funnel_data, x='Value', y='Stage', title="Funnel Drop-off Analysis")
    st.plotly_chart(fig_funnel, use_container_width=True)

# 圖表 B: 解決 Batch ID 人工痛點的自動化分級圖
# 背書: 自動化處理取代 Excel 手工
with col_right:
    st.subheader("2. Voucher Tier Performance (Batch Breakdown)")
    # 計算每個 Tier 的真實轉換率
    filtered_df['Conversion_%'] = (filtered_df['Actual_Trips'] / filtered_df['Clicks']) * 100
    fig_bar = px.bar(filtered_df, x='Voucher_Tier', y='Conversion_%', color='Voucher_Tier',
                     text_auto='.1f', title="Trip Conversion Rate by Discount Tier")
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ==========================================
# 5. 情境與高峰預測區 (Contextual Peak Analysis)
# ==========================================
st.subheader("3. Peak Redemption Periods & Contextual Triggers")
st.info("💡 Insight: Redemption spikes observed during 17:00-19:00 on rainy days. (Powered by Grewal et al., 2016)")

# 模擬一個熱力圖 (星期 vs 小時)
np.random.seed(42)
heatmap_data = np.random.randint(100, 1000, size=(7, 24))
days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
fig_heat = px.imshow(heatmap_data, labels=dict(x="Hour of Day", y="Day of Week", color="Trips"),
                     x=[str(i) for i in range(24)], y=days, title="Weekly Peak Hours Heatmap")
st.plotly_chart(fig_heat, use_container_width=True)
