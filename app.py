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
st.caption("Interactive Prototype for ISYS3303 BIT Project")

tab1, tab2 = st.tabs(["📝 Data Entry Portal", "📊 Report Generator"])

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
        
    if st.button("Submit Data to Database", type="primary"):
        new_row = pd.DataFrame([{
            'Date': pd.to_datetime(in_date),
            'Platform': in_plat,
            'Voucher_Tier': in_tier,
            'Clicks': int(in_clicks),
            'Redeemed_Vouchers': int(in_red),
            'Actual_Trips': int(in_trips)
        }])
        st.session_state.db = pd.concat([st.session_state.db, new_row], ignore_index=True)
        st.success(f"Data for {in_date} successfully added!")
        st.dataframe(st.session_state.db.tail(5))

# TAB 2: REPORT GENERATOR
with tab2:
    st.subheader("Generate automated reports based on database")
    report_type = st.radio("Select Report Type", ["Daily", "Weekly", "Monthly", "Yearly"], horizontal=True)
    
    df = st.session_state.db.copy()
    
    if report_type == "Daily":
        df['Time_Period'] = df['Date'].dt.date.astype(str)
    elif report_type == "Weekly":
        df['Time_Period'] = df['Date'].dt.strftime('%Y-W%V')
    elif report_type == "Monthly":
        df['Time_Period'] = df['Date'].dt.strftime('%Y-%m')
    elif report_type == "Yearly":
        df['Time_Period'] = df['Date'].dt.year.astype(str)

    agg = df.groupby('Time_Period')[['Clicks', 'Redeemed_Vouchers', 'Actual_Trips']].sum().reset_index()
    
    total_red = agg['Redeemed_Vouchers'].sum()
    total_trp = agg['Actual_Trips'].sum()
    conv = (total_trp / total_red * 100) if total_red > 0 else 0
    
    # KPI Cards
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Redeemed Vouchers", f"{total_red:,}")
    m2.metric("Total Actual Trips", f"{total_trp:,}")
    m3.metric("Conversion Rate", f"{conv:.1f}%")
    
    # Trend Chart
    fig_trend = px.line(
        agg, x='Time_Period', y=['Redeemed_Vouchers', 'Actual_Trips'],
        title=f"{report_type} Performance Trend",
        color_discrete_sequence=["#999999", "#FF5A00"]
    )
    st.plotly_chart(fig_trend, use_container_width=True)
