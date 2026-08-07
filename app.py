import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date, timedelta

st.set_page_config(page_title="DiDi Central Data & Reporting Framework", layout="wide")

# ==========================================
# 1. Historical Mock Data Generation
# ==========================================
@st.cache_data
def load_initial_data():
    np.random.seed(42)
    end_date = pd.to_datetime('today')
    start_date = end_date - pd.Timedelta(days=365)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    platforms = ['Meta Ads', 'Quoll Email', 'App Promo Zone']
    tiers = ['10% Off', '20% Off', '50% Off']

    data = []
    for d in date_range:
        for _ in range(np.random.randint(1, 4)):
            plat = np.random.choice(platforms)
            tier = np.random.choice(tiers)
            clicks = np.random.randint(500, 5000)
            
            if tier == '10% Off':
                redeemed = int(clicks * np.random.uniform(0.1, 0.3))
            elif tier == '20% Off':
                redeemed = int(clicks * np.random.uniform(0.3, 0.6))
            else:
                redeemed = int(clicks * np.random.uniform(0.6, 0.8))
                
            trips = int(redeemed * np.random.uniform(0.4, 0.9))
            
            data.append({
                'Date': d,
                'Platform': plat,
                'Voucher_Tier': tier,
                'Clicks': clicks,
                'Redeemed_Vouchers': redeemed,
                'Actual_Trips': trips
            })
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date'])
    return df

if 'db' not in st.session_state:
    st.session_state.db = load_initial_data()

# ==========================================
# 2. UI Layout
# ==========================================
st.title("🚗 DiDi Central Data & Reporting Framework")

tab1, tab2 = st.tabs(["📝 1. Data Entry Portal", "📊 2. Report Generator"])

# TAB 1: DATA ENTRY
with tab1:
    st.subheader("Input manual metrics to feed the reporting database")
    col1, col2 = st.columns(2)
    
    with col1:
        in_date = st.date_input("Date", date.today())
        in_plat = st.selectbox("Platform", ['Meta Ads', 'Quoll Email', 'App Promo Zone'])
        in_tier = st.selectbox("Voucher Tier", ['10% Off', '20% Off', '50% Off'])
        
    with col2:
        in_clicks = st.number_input("Total Clicks / Opens", min_value=0, value=1000)
        in_red = st.number_input("Vouchers Redeemed", min_value=0, value=450)
        in_trips = st.number_input("Actual Trips", min_value=0, value=300)
        
    if st.button("Submit Data", type="primary"):
        new_row = pd.DataFrame([{
            'Date': pd.to_datetime(in_date),
            'Platform': in_plat,
            'Voucher_Tier': in_tier,
            'Clicks': int(in_clicks),
            'Redeemed_Vouchers': int(in_red),
            'Actual_Trips': int(in_trips)
        }])
        st.session_state.db = pd.concat([st.session_state.db, new_row], ignore_index=True)
        st.success(f"✅ Success! Data for {in_date} added to the database.")
        st.dataframe(st.session_state.db.tail(5))

# TAB 2: REPORT GENERATOR
with tab2:
    st.subheader("Generate automated reports based on database")
    
    # 這裡加入你想要的 Custom Date Range 功能
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        report_type = st.radio("Select Time Scale", ["Daily", "Weekly", "Monthly", "Yearly", "Custom Date Range"])
    with col_r2:
        custom_start = st.date_input("Start Date (for Custom Range)", date.today() - timedelta(days=30))
    with col_r3:
        custom_end = st.date_input("End Date (for Custom Range)", date.today())
        
    if st.button("Generate Report", type="primary"):
        df = st.session_state.db.copy()
        
        # 過濾自定義時間
        if report_type == "Custom Date Range":
            df = df[(df['Date'] >= pd.to_datetime(custom_start)) & (df['Date'] <= pd.to_datetime(custom_end))]
            
        if df.empty:
            st.warning("⚠️ No data available for this period. Try adjusting your date range.")
        else:
            # 聚合資料
            if report_type == "Daily":
                df['Time_Period'] = df['Date'].dt.date.astype(str)
            elif report_type == "Weekly":
                df['Time_Period'] = df['Date'].dt.strftime('%Y-W%V')
            elif report_type == "Monthly":
                df['Time_Period'] = df['Date'].dt.strftime('%Y-%m')
            elif report_type == "Yearly":
                df['Time_Period'] = df['Date'].dt.year.astype(str)
            else: # Custom 預設以日為單位顯示趨勢
                df['Time_Period'] = df['Date'].dt.date.astype(str)

            agg_time = df.groupby('Time_Period')[['Clicks', 'Redeemed_Vouchers', 'Actual_Trips']].sum().reset_index()
            agg_time = agg_time.sort_values('Time_Period')
            
            # 顯示你原本的 KPI 總結
            total_red = agg_time['Redeemed_Vouchers'].sum()
            total_trp = agg_time['Actual_Trips'].sum()
            conv_rate = (total_trp / total_red * 100) if total_red > 0 else 0
            
            st.markdown(f"### 📊 **Total Redeemed:** {total_red:,} | **Total Trips:** {total_trp:,} | **Conversion:** {conv_rate:.1f}%")
            
            # 顯示雙圖表
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                fig_trend = px.line(
                    agg_time, x='Time_Period', y=['Redeemed_Vouchers', 'Actual_Trips'],
                    markers=True, title="Performance Trend",
                    color_discrete_sequence=["#999999", "#FF5A00"]
                )
                fig_trend.update_layout(template="plotly_white", xaxis_title="Time Period", yaxis_title="Count", legend_title_text='Metrics')
                st.plotly_chart(fig_trend, use_container_width=True)
                
            with col_chart2:
                agg_plat = df.groupby('Platform')[['Redeemed_Vouchers', 'Actual_Trips']].sum().reset_index()
                fig_plat = px.bar(
                    agg_plat, x='Platform', y=['Redeemed_Vouchers', 'Actual_Trips'],
                    barmode='group', title="Platform Summary",
                    color_discrete_sequence=["#CCCCCC", "#FF5A00"]
                )
                fig_plat.update_layout(template="plotly_white", yaxis_title="Count", legend_title_text='Metrics')
                st.plotly_chart(fig_plat, use_container_width=True)
