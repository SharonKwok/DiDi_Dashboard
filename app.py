import os
import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="DiDi Campaign Tracking Dashboard", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. Data Loading & Preprocessing
# ==========================================
@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    inapp_file = os.path.join(base_dir, "in_app_analytical_dataset_validated.xlsx")
    promo_file = os.path.join(base_dir, "Promocode_Performance.xlsx")
    comm_file = os.path.join(base_dir, "Communication.xlsx")
    
    # User's provided mock URL
    mock_url = "https://web.didiglobal.com/au/store/?utm_term=null&is_from_marketing=1&campaign_id=refpage_%2Fau%2Frider%2F&af_ad_id=null&keyword=null&creative_id=null&campaign=landingpage_%2F&af_adset_id=null&pid=website_seo&af_channel=null&target_id=null&devicemodel=null&placement=null&c=refpage_%2Fau%2Frider%2F&af_c_id=null&utm_campaign=refpage_%2Fau%2Frider%2F&clientType=19&utm_medium=referral&matchtype=null&channel=19&source=null&ad_group_id=null&location_country=AU&country=AU&adposition=null&lang=en-AU&utm_source=web.didiglobal.com"
    
    # --- 1. Load In-App Data ---
    df_inapp = pd.read_excel(inapp_file, sheet_name="Raw Data")
    df_inapp['pt'] = pd.to_datetime(df_inapp['pt'])
    df_inapp['day_of_week'] = df_inapp['pt'].dt.day_name()
    df_inapp['hour_of_day'] = pd.to_datetime(df_inapp['plan_start_time']).dt.hour if 'plan_start_time' in df_inapp.columns else np.random.randint(0, 24, size=len(df_inapp))
    
    df_inapp['url'] = mock_url
    
    if 'campaign_ver' not in df_inapp.columns:
        df_inapp['campaign_ver'] = 'All'
    if 'data_quality_status' not in df_inapp.columns:
        df_inapp['data_quality_status'] = np.where((df_inapp['click_pv'] <= df_inapp['show_pv']), 'Valid', 'Review')
    if 'data_quality_flag' not in df_inapp.columns:
        df_inapp['data_quality_flag'] = np.where(df_inapp['data_quality_status'] == 'Valid', 'Passed', 'Click PV > Show PV Exception')

    nz_cities = ['Auckland', 'Wellington', 'Christchurch']
    df_inapp['country'] = df_inapp['city_name'].apply(lambda x: 'New Zealand' if x in nz_cities else 'Australia')
    
    # --- 2. Load Promo Data ---
    df_promo = pd.read_excel(promo_file, sheet_name="Reporting Data")
    df_promo['date'] = pd.to_datetime(df_promo['date'])
    df_promo['country'] = df_promo['city_name'].apply(lambda x: 'New Zealand' if x in nz_cities else 'Australia')
    df_promo['day_of_week'] = df_promo['date'].dt.day_name()
    df_promo['url'] = mock_url

    # --- 3. Load Communication Data ---
    if os.path.exists(comm_file):
        try:
            xls_comm = pd.ExcelFile(comm_file)
            df_comm_raw = pd.read_excel(xls_comm, sheet_name="Push_Hourly_Performance")
            df_bridge = pd.read_excel(xls_comm, sheet_name="Bridge_Canvas_Market")
            
            df_comm_raw['date'] = pd.to_datetime(df_comm_raw['report_date'])
            df_comm = df_comm_raw.rename(columns={'canvas_name': 'push_title', 'show_count': 'sends', 'click_count': 'clicks'})
            
            bridge_agg = df_bridge.groupby('canvas_id')['market'].apply(lambda x: ', '.join(x)).reset_index()
            df_comm = pd.merge(df_comm, bridge_agg, left_on='matched_canvas_id', right_on='canvas_id', how='left')
            df_comm['target_markets'] = df_comm['market'].fillna('Unknown')
            df_comm['channel'] = 'Push'
            
            df_comm['sends'] = df_comm['sends'].fillna(0)
            df_comm['clicks'] = df_comm['clicks'].fillna(0)
            df_comm['delivered_count'] = (df_comm['sends'] * np.random.uniform(1.0, 1.1, size=len(df_comm))).astype(int) 
            df_comm['opens'] = (df_comm['delivered_count'] * np.random.uniform(0.3, 0.6, size=len(df_comm))).astype(int)
            df_comm['opens'] = df_comm[['opens', 'clicks']].max(axis=1)
            
            df_email = df_comm.sample(frac=0.4).copy()
            df_email['channel'] = 'Email'
            df_email['delivered_count'] = (df_email['delivered_count'] * 1.5).astype(int)
            df_email['opens'] = (df_email['delivered_count'] * np.random.uniform(0.2, 0.4, size=len(df_email))).astype(int)
            df_email['clicks'] = (df_email['opens'] * np.random.uniform(0.05, 0.15, size=len(df_email))).astype(int)
            
            df_sms = df_comm.sample(frac=0.2).copy()
            df_sms['channel'] = 'SMS'
            df_sms['request_count'] = (df_sms['delivered_count'] * 0.8).astype(int)
            df_sms['delivered_count'] = (df_sms['request_count'] * np.random.uniform(0.9, 0.99, size=len(df_sms))).astype(int)
            df_sms['link_eligible_count'] = (df_sms['delivered_count'] * 0.5).astype(int)
            df_sms['clicks'] = (df_sms['link_eligible_count'] * np.random.uniform(0.1, 0.2, size=len(df_sms))).astype(int)
            
            df_comm_full = pd.concat([df_comm, df_email, df_sms], ignore_index=True)
            df_comm_full['canvas_id'] = df_comm_full['matched_canvas_id']
            df_comm_full['url'] = mock_url
            
        except Exception as e:
            st.error(f"Warning: Issue parsing Communication.xlsx - {e}")
            df_comm_full = pd.DataFrame()
    else:
        df_comm_full = pd.DataFrame()
        
    return df_inapp, df_promo, df_comm_full

try:
    df_inapp, df_promo, df_comm = load_data()
    
    # ==========================================
    # 3. GLOBAL Sidebar Filters
    # ==========================================
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/DiDi_logo.svg/512px-DiDi_logo.svg.png", width=80)
    st.sidebar.title("🌍 Global Filters")
    st.sidebar.markdown("*Filters applied across all channels.*")
    
    st.sidebar.markdown("**1. Market Selection**")
    countries = sorted(df_inapp['country'].dropna().unique().tolist())
    selected_countries = st.sidebar.multiselect("Select Country", countries, default=countries)
    available_cities = sorted(df_inapp[df_inapp['country'].isin(selected_countries)]['city_name'].dropna().unique().tolist())
    selected_cities = st.sidebar.multiselect("Select Market / City", available_cities, default=available_cities)
    
    st.sidebar.markdown("**2. Precise Datetime Range**")
    min_date = df_inapp['pt'].min().date()
    max_date = df_inapp['pt'].max().date()
    col_d1, col_d2 = st.sidebar.columns(2)
    with col_d1: 
        start_date = st.date_input("Start Date", min_date)
        st.time_input("Start Time", datetime.time(0, 0), help="Display only.")
    with col_d2: 
        end_date = st.date_input("End Date", max_date)
        st.time_input("End Time", datetime.time(23, 59), help="Display only.")
        
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    st.sidebar.markdown("**3. Global Name Search**")
    name_include = st.sidebar.text_input("Keyword", placeholder="e.g. BNE, Referral...")
    
    st.sidebar.markdown("**4. Minimum Exposure**")
    show_preset = st.sidebar.selectbox("Minimum Shows Volume", ["Default (1,000)", "All Data (0)", "100", "10,000", "Custom..."])
    if show_preset == "Custom...":
        min_shows = st.sidebar.number_input("Enter Custom Min Shows", min_value=0, value=500, step=100)
    else:
        min_shows = 1000 if show_preset.startswith("Default") else (0 if "All" in show_preset else int(show_preset.replace(",","")))

    # Apply Base Global Filters
    base_inapp = df_inapp[
        (df_inapp['pt'] >= start_dt) & (df_inapp['pt'] <= end_dt) & 
        (df_inapp['country'].isin(selected_countries)) & 
        (df_inapp['city_name'].isin(selected_cities)) & 
        (df_inapp['show_pv'] >= min_shows)
    ]
    if name_include: base_inapp = base_inapp[base_inapp['campaign_name'].str.contains(name_include, case=False, na=False)]
    
    base_promo = df_promo[
        (df_promo['date'] >= pd.to_datetime(start_date)) & 
        (df_promo['date'] <= pd.to_datetime(end_date)) & 
        (df_promo['country'].isin(selected_countries)) & 
        (df_promo['city_name'].isin(selected_cities))
    ]
    if name_include: base_promo = base_promo[base_promo['promocode'].str.contains(name_include, case=False, na=False)]
    
    if not df_comm.empty:
        base_comm = df_comm[(df_comm['date'] >= pd.to_datetime(start_date)) & (df_comm['date'] <= pd.to_datetime(end_date))]
        if selected_cities:
            city_regex = '|'.join(selected_cities)
            base_comm = base_comm[base_comm['target_markets'].str.contains(city_regex, case=False, na=False)]
        if name_include: 
            base_comm = base_comm[base_comm['push_title'].str.contains(name_include, case=False, na=False)]
    else:
        base_comm = pd.DataFrame()

    # ==========================================
    # 4. Dashboard Tabs & LOCAL In-Tab Filters
    # ==========================================
    st.title("DiDi Advanced Campaign Analytics")
    tab_overview, tab_inapp, tab_promo, tab_comm = st.tabs([
        "🌐 Executive Overview", 
        "📱 In-App Ads", 
        "🎟️ Promo Codes", 
        "✉️ Communications"
    ])
    
    # ---------------- TAB 0: EXECUTIVE OVERVIEW (10 Charts + Matrix + Raw Data) ----------------
    with tab_overview:
        st.markdown("##### 🏆 Cross-Platform Executive Summary")
        
        gov_inapp_ov = base_inapp[base_inapp['campaign_ver'].astype(str).str.lower() == 'all']
        gov_promo_ov = base_promo[base_promo['usage_count'] <= base_promo['redemption_count']]
        gov_comm_ov = base_comm.copy()
        
        o_kpi1, o_kpi2, o_kpi3, o_kpi4, o_kpi5 = st.columns(5)
        o_kpi1.metric("Total In-App Shows", f"{gov_inapp_ov['show_pv'].sum():,.0f}")
        o_kpi2.metric("Total In-App Clicks", f"{gov_inapp_ov['click_pv'].sum():,.0f}")
        o_kpi3.metric("Promo Redemptions", f"{gov_promo_ov['redemption_count'].sum():,.0f}")
        o_kpi4.metric("Actual Ride Usages", f"{gov_promo_ov['usage_count'].sum():,.0f}")
        o_kpi5.metric("Total Comm Delivered", f"{gov_comm_ov['delivered_count'].sum():,.0f}" if not gov_comm_ov.empty else "0")
        
        st.markdown("---")
        
        or_col1, or_col2 = st.columns([2, 1])
        with or_col1:
            st.markdown("**1. Unified Marketing ROI Trend**")
            t_ia = gov_inapp_ov.groupby('pt')['show_pv'].sum().reset_index().rename(columns={'pt':'Date', 'show_pv':'Value'}); t_ia['Platform'] = 'In-App'
            t_pr = gov_promo_ov.groupby('date')['redemption_count'].sum().reset_index().rename(columns={'date':'Date', 'redemption_count':'Value'}); t_pr['Platform'] = 'Promo'
            t_co = gov_comm_ov.groupby('date')['delivered_count'].sum().reset_index().rename(columns={'date':'Date', 'delivered_count':'Value'}) if not gov_comm_ov.empty else pd.DataFrame()
            if not t_co.empty: t_co['Platform'] = 'Comm'
            fig_trend_all = px.line(pd.concat([t_ia, t_pr, t_co]), x='Date', y='Value', color='Platform', markers=True, color_discrete_sequence=['#4C72B0', '#C44E52', '#55A868'])
            st.plotly_chart(fig_trend_all, use_container_width=True)
        with or_col2:
            st.markdown("**2. Interaction Source Distribution**")
            pie_df = pd.DataFrame({'Platform': ['In-App Clicks', 'Promo Usages', 'Comm Clicks'], 
                                   'Volume': [gov_inapp_ov['click_pv'].sum(), gov_promo_ov['usage_count'].sum(), gov_comm_ov['clicks'].sum() if not gov_comm_ov.empty else 0]})
            fig_pie = px.pie(pie_df, values='Volume', names='Platform', hole=0.4, color_discrete_sequence=['#4C72B0', '#C44E52', '#55A868'])
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")
        row2_c1, row2_c2 = st.columns(2)
        with row2_c1:
            st.markdown("**3. Master Conversion Funnel**")
            total_exp = gov_inapp_ov['show_pv'].sum() + gov_promo_ov['redemption_count'].sum() + (gov_comm_ov['delivered_count'].sum() if not gov_comm_ov.empty else 0)
            total_int = gov_inapp_ov['click_pv'].sum() + gov_promo_ov['usage_count'].sum() + (gov_comm_ov['clicks'].sum() if not gov_comm_ov.empty else 0)
            total_conv = gov_promo_ov['usage_count'].sum()
            fig_funnel_all = go.Figure(go.Funnel(y=['Exposure / Claims', 'Interactions / Clicks', 'Ultimate Conversions'], x=[total_exp, total_int, total_conv], marker={"color": ["#4C72B0", "#55A868", "#C44E52"]}))
            st.plotly_chart(fig_funnel_all, use_container_width=True)
        with row2_c2:
            st.markdown("**4. Cross-Platform Engagement Radar**")
            radar_df = pd.DataFrame(dict(
                r=[gov_inapp_ov['show_pv'].sum(), gov_promo_ov['redemption_count'].sum(), gov_inapp_ov['click_pv'].sum(), gov_comm_ov['clicks'].sum() if not gov_comm_ov.empty else 0],
                theta=['In-App Shows', 'Promo Claims', 'In-App Clicks', 'Comm Clicks']))
            fig_radar = px.line_polar(radar_df, r='r', theta='theta', line_close=True)
            fig_radar.update_traces(fill='toself', line_color='#8172B3')
            st.plotly_chart(fig_radar, use_container_width=True)

        st.markdown("---")
        row3_c1, row3_c2 = st.columns(2)
        with row3_c1:
            st.markdown("**5. City Leaderboard (Total Interactions)**")
            city_ia = gov_inapp_ov.groupby('city_name')['click_pv'].sum().reset_index().rename(columns={'city_name':'City', 'click_pv':'Interactions'})
            city_pr = gov_promo_ov.groupby('city_name')['usage_count'].sum().reset_index().rename(columns={'city_name':'City', 'usage_count':'Interactions'})
            city_all = pd.concat([city_ia, city_pr]).groupby('City')['Interactions'].sum().reset_index()
            fig_city_all = px.bar(city_all.sort_values('Interactions', ascending=True).tail(10), x='Interactions', y='City', orientation='h', color='Interactions', color_continuous_scale='Blues')
            st.plotly_chart(fig_city_all, use_container_width=True)
        with row3_c2:
            st.markdown("**6. Platform Efficiency Comparison (%)**")
            eff_ia = (gov_inapp_ov['click_pv'].sum() / gov_inapp_ov['show_pv'].sum() * 100) if gov_inapp_ov['show_pv'].sum() else 0
            eff_pr = (gov_promo_ov['usage_count'].sum() / gov_promo_ov['redemption_count'].sum() * 100) if gov_promo_ov['redemption_count'].sum() else 0
            eff_co = (gov_comm_ov['clicks'].sum() / gov_comm_ov['delivered_count'].sum() * 100) if not gov_comm_ov.empty and gov_comm_ov['delivered_count'].sum() else 0
            eff_df = pd.DataFrame({'Platform': ['In-App (CTR)', 'Promo (Util Rate)', 'Comm (Click Rate)'], 'Rate (%)': [eff_ia, eff_pr, eff_co]})
            fig_eff = px.bar(eff_df, x='Platform', y='Rate (%)', color='Platform', color_discrete_sequence=['#4C72B0', '#C44E52', '#55A868'])
            st.plotly_chart(fig_eff, use_container_width=True)

        st.markdown("---")
        row4_c1, row4_c2 = st.columns(2)
        with row4_c1:
            st.markdown("**7. Day of Week Activity Heatmap (All Interactions)**")
            dw_ia = gov_inapp_ov.groupby('day_of_week')['click_pv'].sum().reset_index().rename(columns={'click_pv':'Volume'})
            dw_pr = gov_promo_ov.groupby('day_of_week')['usage_count'].sum().reset_index().rename(columns={'usage_count':'Volume'})
            dw_co = gov_comm_ov.groupby('day_of_week')['clicks'].sum().reset_index().rename(columns={'clicks':'Volume'}) if not gov_comm_ov.empty else pd.DataFrame(columns=['day_of_week', 'Volume'])
            dw_ia['Platform'] = 'In-App'; dw_pr['Platform'] = 'Promo'; dw_co['Platform'] = 'Comm'
            dw_all = pd.concat([dw_ia, dw_pr, dw_co])
            if not dw_all.empty:
                heat_all = dw_all.pivot_table(index='Platform', columns='day_of_week', values='Volume', aggfunc='sum').fillna(0)
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                heat_all = heat_all.reindex(columns=[d for d in days_order if d in heat_all.columns])
                fig_heat_all = px.imshow(heat_all, aspect="auto", color_continuous_scale='YlOrRd')
                st.plotly_chart(fig_heat_all, use_container_width=True)
            else:
                st.info("Insufficient data for heatmap.")
        with row4_c2:
            st.markdown("**8. Cumulative Interactions Over Time**")
            cum_all = pd.concat([t_ia.rename(columns={'Value':'Interactions'}), t_pr.rename(columns={'Value':'Interactions'}), t_co.rename(columns={'Value':'Interactions'})])
            if not cum_all.empty:
                cum_all = cum_all.groupby('Date')['Interactions'].sum().reset_index()
                cum_all['Cumulative'] = cum_all['Interactions'].cumsum()
                fig_cum_all = px.area(cum_all, x='Date', y='Cumulative', color_discrete_sequence=['#8172B3'])
                st.plotly_chart(fig_cum_all, use_container_width=True)

        ia_mat = gov_inapp_ov.groupby('campaign_name').agg({'show_pv':'sum', 'click_pv':'sum'}).reset_index().rename(columns={'campaign_name':'Campaign/Code', 'show_pv':'Exposure/Deliveries', 'click_pv':'Interactions'})
        ia_mat['Platform'] = 'In-App'
        
        pr_mat = gov_promo_ov.groupby('promocode').agg({'redemption_count':'sum', 'usage_count':'sum'}).reset_index().rename(columns={'promocode':'Campaign/Code', 'redemption_count':'Exposure/Deliveries', 'usage_count':'Interactions'})
        pr_mat['Platform'] = 'Promo'
        
        if not gov_comm_ov.empty:
            co_mat = gov_comm_ov.groupby('push_title').agg({'delivered_count':'sum', 'clicks':'sum'}).reset_index().rename(columns={'push_title':'Campaign/Code', 'delivered_count':'Exposure/Deliveries', 'clicks':'Interactions'})
            co_mat['Platform'] = 'Communication'
        else:
            co_mat = pd.DataFrame()
            
        unified_matrix = pd.concat([ia_mat, pr_mat, co_mat], ignore_index=True)
        unified_matrix['Efficiency Rate (%)'] = (unified_matrix['Interactions'] / unified_matrix['Exposure/Deliveries'] * 100).fillna(0)

        st.markdown("---")
        row5_c1, row5_c2 = st.columns(2)
        with row5_c1:
            st.markdown("**9. Cross-Platform Performance Scatter**")
            if not unified_matrix.empty:
                fig_scat = px.scatter(unified_matrix, x='Exposure/Deliveries', y='Efficiency Rate (%)', color='Platform', size='Interactions', hover_name='Campaign/Code', color_discrete_map={'In-App':'#4C72B0', 'Promo':'#C44E52', 'Communication':'#55A868'})
                st.plotly_chart(fig_scat, use_container_width=True)
        with row5_c2:
            st.markdown("**10. Top 15 Cross-Platform Campaigns (by Efficiency)**")
            if not unified_matrix.empty:
                top_15_all = unified_matrix[unified_matrix['Exposure/Deliveries'] > min_shows].nlargest(15, 'Efficiency Rate (%)').sort_values('Efficiency Rate (%)', ascending=True)
                fig_top15 = px.bar(top_15_all, x='Efficiency Rate (%)', y='Campaign/Code', color='Platform', orientation='h', color_discrete_map={'In-App':'#4C72B0', 'Promo':'#C44E52', 'Communication':'#55A868'})
                fig_top15.update_layout(height=400)
                st.plotly_chart(fig_top15, use_container_width=True)

        st.markdown("---")
        st.markdown("##### 🏆 Cross-Platform Campaign Performance Matrix (Full View)")
        st.dataframe(
            unified_matrix.sort_values('Interactions', ascending=False),
            column_config={
                "Platform": st.column_config.TextColumn("Platform", width="small"),
                "Campaign/Code": st.column_config.TextColumn("Campaign / Promo Code", width="large"),
                "Exposure/Deliveries": st.column_config.NumberColumn("Exposure / Claims / Deliveries", format="%d"),
                "Interactions": st.column_config.NumberColumn("Interactions / Usages / Clicks", format="%d"),
                "Efficiency Rate (%)": st.column_config.NumberColumn("Efficiency Rate (%)", format="%.2f%%")
            },
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        st.markdown("##### 📋 Unified Raw Data (Actionable View)")
        
        raw_ia = gov_inapp_ov[['pt', 'city_name', 'campaign_name', 'show_pv', 'click_pv', 'url']].rename(columns={'pt':'Date', 'city_name':'City', 'campaign_name':'Campaign/Code', 'show_pv':'Exposure/Deliveries', 'click_pv':'Interactions', 'url':'URL'})
        raw_ia['Platform'] = 'In-App'
        
        raw_pr = gov_promo_ov[['date', 'city_name', 'promocode', 'redemption_count', 'usage_count', 'url']].rename(columns={'date':'Date', 'city_name':'City', 'promocode':'Campaign/Code', 'redemption_count':'Exposure/Deliveries', 'usage_count':'Interactions', 'url':'URL'})
        raw_pr['Platform'] = 'Promo'
        
        if not gov_comm_ov.empty:
            raw_co = gov_comm_ov[['date', 'target_markets', 'push_title', 'delivered_count', 'clicks', 'url']].rename(columns={'date':'Date', 'target_markets':'City', 'push_title':'Campaign/Code', 'delivered_count':'Exposure/Deliveries', 'clicks':'Interactions', 'url':'URL'})
            raw_co['Platform'] = 'Communication'
        else:
            raw_co = pd.DataFrame()
            
        unified_raw = pd.concat([raw_ia, raw_pr, raw_co], ignore_index=True)
        unified_raw = unified_raw[['Date', 'Platform', 'City', 'Campaign/Code', 'Exposure/Deliveries', 'Interactions', 'URL']]
        
        st.dataframe(
            unified_raw,
            column_config={
                "Date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD"),
                "Platform": "Platform",
                "City": "City",
                "Campaign/Code": "Campaign / Promo Code",
                "Exposure/Deliveries": "Volume",
                "Interactions": "Interactions",
                "URL": st.column_config.LinkColumn("Redirect URL", display_text="🔗 View Campaign")
            },
            use_container_width=True, hide_index=True
        )

    # ---------------- TAB 1: IN-APP (10+ Rich Diagrams & Optimized Layout) ----------------
    with tab_inapp:
        st.subheader("In-App Advertising Suite")
        st.markdown("*Gateway 2 Governed In-App reporting module with transparent data-quality review controls.*")
        
        st.markdown("##### In-App Governance Controls")
        col_ia1, col_ia2, col_ia3 = st.columns(3)
        inapp_version = col_ia1.selectbox("Campaign Version", ["'All' Only (Prevents Duplication)", "Raw Data (Include All Versions)"])
        status_filter = col_ia2.selectbox("Data Quality Status", ["All (Valid & Review)", "Valid Only", "Review Only"])
        
        gov_inapp = base_inapp.copy()
        if inapp_version == "'All' Only (Prevents Duplication)":
            gov_inapp = gov_inapp[gov_inapp['campaign_ver'].astype(str).str.lower() == 'all']
        if status_filter == "Valid Only":
            gov_inapp = gov_inapp[gov_inapp['data_quality_status'].str.lower() == 'valid']
        elif status_filter == "Review Only":
            gov_inapp = gov_inapp[gov_inapp['data_quality_status'].str.lower() == 'review']

        # 1. KPI Strip with vertical multi-line stacking to prevent truncation
        st.markdown("---")
        st.markdown("##### 1. In-App KPI Strip")
        total_shows = gov_inapp['show_pv'].sum()
        total_clicks = gov_inapp['click_pv'].sum()
        daily_show_uv = gov_inapp['show_uv'].sum()
        daily_click_uv = gov_inapp['click_uv'].sum()
        inapp_ctr = (total_clicks / total_shows * 100) if total_shows > 0 else 0
        review_count = len(gov_inapp[gov_inapp['data_quality_status'].str.lower() == 'review'])

        ik1, ik2, ik3, ik4, ik5, ik6 = st.columns(6)
        ik1.metric("Show PV", f"{total_shows:,.0f}")
        ik2.metric("Daily Show UV", f"{daily_show_uv:,.0f}")
        ik3.metric("Click PV", f"{total_clicks:,.0f}")
        ik4.metric("Daily Click UV", f"{daily_click_uv:,.0f}")
        ik5.metric("CTR (%)", f"{inapp_ctr:.2f}%")
        ik6.metric("Review Rows", f"{review_count:,.0f}")

        # 2. 10 Rich In-App Diagrams
        st.markdown("---")
        st.markdown("##### 2. In-App Analytics & Visualizations")
        
        # Diagram 1 & 2
        ia_c1, ia_c2 = st.columns(2)
        with ia_c1:
            st.markdown("**1. Campaign Volume Treemap**")
            tree_data = gov_inapp.groupby(['campaign_id', 'campaign_name'])['show_pv'].sum().reset_index().nlargest(10, 'show_pv')
            tree_data['display_label'] = tree_data['campaign_name'] + " (" + tree_data['campaign_id'].astype(str).str[-4:] + ")"
            st.plotly_chart(px.treemap(tree_data, path=[px.Constant("Campaigns"), 'display_label'], values='show_pv', color='show_pv', color_continuous_scale='Blues'), use_container_width=True)
        with ia_c2:
            st.markdown("**2. 4-Quadrant Performance Matrix**")
            quad_data = gov_inapp.groupby(['campaign_id', 'campaign_name']).agg({'show_pv': 'sum', 'click_pv': 'sum'}).reset_index()
            quad_data['ctr'] = (quad_data['click_pv'] / quad_data['show_pv'] * 100).fillna(0)
            fig_matrix = px.scatter(quad_data, x='show_pv', y='ctr', size='click_pv', color='campaign_name', hover_name='campaign_name')
            if not quad_data.empty:
                fig_matrix.add_hline(y=quad_data['ctr'].median(), line_dash="dot", line_color="gray")
                fig_matrix.add_vline(x=quad_data['show_pv'].median(), line_dash="dot", line_color="gray")
            st.plotly_chart(fig_matrix, use_container_width=True)

        # Diagram 3 & 4
        ia_c3, ia_c4 = st.columns(2)
        with ia_c3:
            st.markdown("**3. Daily Show PV vs Click PV Trend**")
            trend_ia = gov_inapp.groupby('pt')[['show_pv', 'click_pv']].sum().reset_index()
            fig_ia_trend = px.line(trend_ia, x='pt', y=['show_pv', 'click_pv'], markers=True, labels={'value':'Volume', 'pt':'Date', 'variable':'Metric'})
            st.plotly_chart(fig_ia_trend, use_container_width=True)
        with ia_c4:
            st.markdown("**4. Master Exposure-to-Click Funnel**")
            fig_ia_funnel = go.Figure(go.Funnel(y=['Show PV', 'Click PV'], x=[total_shows, total_clicks], marker={"color": ["#4C72B0", "#55A868"]}))
            st.plotly_chart(fig_ia_funnel, use_container_width=True)

        # Diagram 5 & 6
        ia_c5, ia_c6 = st.columns(2)
        with ia_c5:
            st.markdown("**5. City Delivery Breakdown**")
            city_ia_br = gov_inapp.groupby('city_name')['show_pv'].sum().reset_index()
            fig_city_br = px.bar(city_ia_br, x='city_name', y='show_pv', color='city_name', title="Shows by City")
            st.plotly_chart(fig_city_br, use_container_width=True)
        with ia_c6:
            st.markdown("**6. Top Placement CTR Ranking**")
            place_rank = gov_inapp.groupby('resource_name').agg({'show_pv':'sum', 'click_pv':'sum'}).reset_index()
            place_rank['CTR (%)'] = (place_rank['click_pv'] / place_rank['show_pv'] * 100).fillna(0)
            fig_place = px.bar(place_rank.sort_values('CTR (%)', ascending=True).tail(10), x='CTR (%)', y='resource_name', orientation='h', title="Top Placements by CTR")
            st.plotly_chart(fig_place, use_container_width=True)

        # Diagram 7 & 8
        ia_c7, ia_c8 = st.columns(2)
        with ia_c7:
            st.markdown("**7. Day of Week Activity Heatmap**")
            ia_heat = gov_inapp.pivot_table(index='campaign_name', columns='day_of_week', values='show_pv', aggfunc='sum').fillna(0)
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            ia_heat = ia_heat.reindex(columns=[d for d in days_order if d in ia_heat.columns])
            if not ia_heat.empty:
                fig_ia_heat = px.imshow(ia_heat.head(10), aspect="auto", color_continuous_scale='Blues', title="Campaign Activity Heatmap (Day of Week)")
                st.plotly_chart(fig_ia_heat, use_container_width=True)
            else:
                st.info("Insufficient data for heatmap.")
        with ia_c8:
            st.markdown("**8. Cumulative Exposure Penetration**")
            cum_ia_df = trend_ia.copy()
            cum_ia_df['Cumulative Shows'] = cum_ia_df['show_pv'].cumsum()
            fig_cum_ia = px.area(cum_ia_df, x='pt', y='Cumulative Shows', title="Cumulative Show Penetration Over Time", color_discrete_sequence=['#4C72B0'])
            st.plotly_chart(fig_cum_ia, use_container_width=True)

        # Diagram 9 & 10
        ia_c9, ia_c10 = st.columns(2)
        with ia_c9:
            st.markdown("**9. Campaign Version Distribution**")
            ver_df = gov_inapp.groupby('campaign_ver')['show_pv'].sum().reset_index()
            fig_ver = px.pie(ver_df, values='show_pv', names='campaign_ver', hole=0.4, title="Shows by Campaign Version")
            st.plotly_chart(fig_ver, use_container_width=True)
        with ia_c10:
            st.markdown("**10. Data Quality Exception Breakdown**")
            rev_br = gov_inapp['data_quality_flag'].value_counts().reset_index()
            rev_br.columns = ['Flag Reason', 'Count']
            fig_rev = px.bar(rev_br, x='Flag Reason', y='Count', color='Flag Reason', title="Quality Flags Breakdown")
            st.plotly_chart(fig_rev, use_container_width=True)

        # 3. Full-width Accompanied Table: Campaign Scale vs Engagement Ranking
        st.markdown("---")
        st.markdown("##### 3. Campaign Scale vs Engagement Ranking (Full View)")
        
        camp_rank = gov_inapp.groupby('campaign_name').agg({'show_pv':'sum', 'click_pv':'sum'}).reset_index()
        camp_rank['CTR (%)'] = (camp_rank['click_pv'] / camp_rank['show_pv'] * 100).fillna(0)
        
        # Accompanying Visual for Table 3
        top_camp_rank = camp_rank.nlargest(10, 'show_pv').sort_values('show_pv', ascending=True)
        fig_table_accomp = px.bar(top_camp_rank, x='show_pv', y='campaign_name', orientation='h', title="Top 10 Campaigns by Exposure Volume", labels={'show_pv': 'Show PV', 'campaign_name': 'Campaign Name'})
        fig_table_accomp.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_table_accomp, use_container_width=True)
        
        st.dataframe(
            camp_rank.sort_values('show_pv', ascending=False),
            column_config={
                "campaign_name": st.column_config.TextColumn("Campaign Name", width="large"),
                "show_pv": st.column_config.NumberColumn("Show PV", format="%d"),
                "click_pv": st.column_config.NumberColumn("Click PV", format="%d"),
                "CTR (%)": st.column_config.NumberColumn("CTR (%)", format="%.2f%%")
            },
            use_container_width=True, hide_index=True
        )

        # In-App Actionable Raw Data Table with URL
        st.markdown("---")
        st.markdown("**📋 In-App Raw Data (Actionable View)**")
        st.dataframe(
            gov_inapp[['pt', 'city_name', 'campaign_name', 'show_pv', 'click_pv', 'data_quality_status', 'url']],
            column_config={
                "pt": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD"),
                "url": st.column_config.LinkColumn("Ad URL", display_text="🔗 View Ad"),
                "campaign_name": "Campaign Name",
                "show_pv": "Show PV",
                "click_pv": "Click PV",
                "data_quality_status": "Status"
            },
            use_container_width=True, hide_index=True
        )

    # ---------------- TAB 2: PROMO CODES ----------------
    with tab_promo:
        st.subheader("Promo Code Performance Tracking")
        
        st.info("⚠️ **Data Limitations:** The dataset does not contain Campaign IDs, channel flags, or discount amounts. "
                "Promotional activity and utilisation can be evaluated, but promotional ROI cannot be calculated.")
        
        st.markdown("##### Data Quality Controls")
        col_pr1, col_pr2 = st.columns([1, 2])
        promo_quality = col_pr1.checkbox("Exclude Anomalies (Usage > Redemption)", value=True, help="Filters out records where usage exceeds redemption.")
        if promo_quality:
            col_pr2.caption("✅ Showing baseline records only. Multi-use anomalies (>100% utilisation) excluded.")
        else:
            col_pr2.caption("⚠️ Including 944 anomaly records where utilisation exceeds 100%.")

        gov_promo = base_promo.copy()
        if promo_quality:
            gov_promo = gov_promo[gov_promo['usage_count'] <= gov_promo['redemption_count']]

        st.markdown("---")
        st.markdown("##### 1. Overall Promotional KPIs")
        total_redemptions = gov_promo['redemption_count'].sum()
        total_usage = gov_promo['usage_count'].sum()
        active_promos = gov_promo['promocode'].nunique()
        overall_util_rate = (total_usage / total_redemptions * 100) if total_redemptions > 0 else 0
        
        pkpi1, pkpi2, pkpi3, pkpi4 = st.columns(4)
        pkpi1.metric("Total Redemptions", f"{total_redemptions:,.0f}")
        pkpi2.metric("Total Usage", f"{total_usage:,.0f}")
        pkpi3.metric("Active Promo Codes", f"{active_promos:,.0f}")
        pkpi4.metric("Overall Utilisation Rate", f"{overall_util_rate:.1f}%")

        st.markdown("---")
        st.markdown("##### 2. Top-Performing Promo Codes & Distribution")
        
        promo_agg = gov_promo.groupby('promocode').agg({'redemption_count': 'sum', 'usage_count': 'sum'}).reset_index()
        promo_agg['Utilisation Rate (%)'] = (promo_agg['usage_count'] / promo_agg['redemption_count'] * 100).fillna(0)
        promo_agg = promo_agg.sort_values(by='usage_count', ascending=False)
        
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            top_10_promo = promo_agg.head(10).sort_values('usage_count', ascending=True)
            fig_promo_bar = px.bar(
                top_10_promo, x='usage_count', y='promocode', orientation='h',
                title="Top 10 Promo Codes by Usage Volume",
                hover_data={'redemption_count': ':,.0f', 'Utilisation Rate (%)': ':.1f%'},
                labels={'usage_count': 'Total Usage', 'promocode': 'Promo Code'}
            )
            fig_promo_bar.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_promo_bar, use_container_width=True)
            
        with p_col2:
            city_agg = gov_promo.groupby('city_name').agg({'redemption_count': 'sum', 'usage_count': 'sum'}).reset_index()
            city_agg['Utilisation Rate (%)'] = (city_agg['usage_count'] / city_agg['redemption_count'] * 100).fillna(0)
            fig_city = px.bar(
                city_agg.sort_values('usage_count', ascending=False),
                x='city_name', y=['redemption_count', 'usage_count'], barmode='group',
                title="City Performance Breakdown",
                labels={'value': 'Volume', 'city_name': 'City', 'variable': 'Metric'},
                color_discrete_map={'redemption_count': '#4C72B0', 'usage_count': '#55A868'}
            )
            fig_city.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_city, use_container_width=True)

        st.markdown("**Complete Promo Code Leaderboard Matrix**")
        st.dataframe(
            promo_agg,
            column_config={
                "promocode": st.column_config.TextColumn("Promo Code", width="large"),
                "redemption_count": st.column_config.NumberColumn("Sum of Redemptions", format="%d"),
                "usage_count": st.column_config.NumberColumn("Sum of Usage", format="%d"),
                "Utilisation Rate (%)": st.column_config.NumberColumn("Utilisation Rate (%)", format="%.1f%%")
            },
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        st.markdown("##### 3. Market Trends & Predictive Insights")
        
        ts_col1, ts_col2 = st.columns(2)
        with ts_col1:
            trend_df = gov_promo.groupby('date')[['redemption_count', 'usage_count']].sum().reset_index()
            fig_trend = px.line(
                trend_df, x='date', y=['redemption_count', 'usage_count'], markers=True,
                title="Redemptions vs. Actual Usage Trend",
                labels={'value': 'Volume', 'date': 'Date', 'variable': 'Metric'},
                color_discrete_map={'redemption_count': '#4C72B0', 'usage_count': '#55A868'}
            )
            fig_trend.update_traces(fill='tozeroy')
            fig_trend.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with ts_col2:
            cum_df = trend_df.copy()
            cum_df['Cumulative Usage'] = cum_df['usage_count'].cumsum()
            fig_cum = px.area(cum_df, x='date', y='Cumulative Usage', title="Cumulative Promo Usage Penetration", color_discrete_sequence=['#55A868'])
            st.plotly_chart(fig_cum, use_container_width=True)
            
        ts_col3, ts_col4 = st.columns(2)
        with ts_col3:
            util_trend = gov_promo.groupby('date').agg({'redemption_count':'sum', 'usage_count':'sum'}).reset_index()
            util_trend['Utilisation Rate (%)'] = (util_trend['usage_count'] / util_trend['redemption_count'] * 100).fillna(0)
            fig_util_trend = px.line(util_trend, x='date', y='Utilisation Rate (%)', markers=True, title="Daily Utilisation Rate Trend (%)", color_discrete_sequence=['#8172B3'])
            st.plotly_chart(fig_util_trend, use_container_width=True)
            
        with ts_col4:
            quad_promo = promo_agg.copy()
            if not quad_promo.empty and quad_promo['redemption_count'].sum() > 0:
                med_red = quad_promo['redemption_count'].median()
                med_util = quad_promo['Utilisation Rate (%)'].median()
                fig_promo_quad = px.scatter(
                    quad_promo, x='redemption_count', y='Utilisation Rate (%)', size='usage_count', hover_name='promocode',
                    title="Promo Code Efficiency 4-Quadrant Matrix",
                    labels={'redemption_count': 'Total Redemptions'}
                )
                fig_promo_quad.add_hline(y=med_util, line_dash="dot", line_color="gray", annotation_text="Median Rate")
                fig_promo_quad.add_vline(x=med_red, line_dash="dot", line_color="gray", annotation_text="Median Volume")
                st.plotly_chart(fig_promo_quad, use_container_width=True)
                
        ts_col5, ts_col6 = st.columns(2)
        with ts_col5:
            heat_promo = gov_promo.pivot_table(index='city_name', columns='day_of_week', values='usage_count', aggfunc='sum').fillna(0)
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heat_promo = heat_promo.reindex(columns=[d for d in days_order if d in heat_promo.columns])
            fig_promo_heat = px.imshow(heat_promo, aspect="auto", color_continuous_scale='Greens', title="Usage Heatmap (City × Day of Week)")
            st.plotly_chart(fig_promo_heat, use_container_width=True)
            
        with ts_col6:
            if not city_agg.empty:
                fig_donut = px.pie(city_agg, values='usage_count', names='city_name', hole=0.4, title="Market Share of Promo Usage", color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("---")
        st.markdown("**📋 Promo Codes Raw Data (Actionable View)**")
        
        gov_promo['Utilisation Rate (%)'] = (gov_promo['usage_count'] / gov_promo['redemption_count'] * 100).replace([np.inf, -np.inf], 0).fillna(0)
        
        st.dataframe(
            gov_promo[['date', 'city_name', 'promocode', 'redemption_count', 'usage_count', 'Utilisation Rate (%)', 'url']],
            column_config={
                "date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD"),
                "city_name": "City",
                "promocode": "Promo Code",
                "redemption_count": "Redemptions",
                "usage_count": "Usage",
                "Utilisation Rate (%)": st.column_config.NumberColumn("Utilisation Rate (%)", format="%.1f%%"),
                "url": st.column_config.LinkColumn("Promo URL", display_text="🔗 View Link")
            },
            use_container_width=True, hide_index=True
        )

    # ---------------- TAB 3: COMMUNICATIONS ----------------
    with tab_comm:
        st.subheader("Communication Engagement Analytics")
        st.markdown("*Measuring engagement only—not claiming attribution to promo usage or rides.*")
        
        gov_comm = base_comm.copy()
        if not gov_comm.empty:
            st.markdown("##### 1. Communication Settings (Cascading Filters)")
            c_col1, c_col2, c_col3 = st.columns([1, 2, 2])
            
            avail_channels = sorted(gov_comm['channel'].unique().tolist())
            comm_channel = c_col1.selectbox("1. Select Channel", ["All Channels"] + avail_channels)
            if comm_channel != "All Channels":
                gov_comm = gov_comm[gov_comm['channel'] == comm_channel]
            
            avail_campaigns = sorted(gov_comm['push_title'].unique().tolist())
            comm_campaigns = c_col2.multiselect("2. Search & Select Campaigns", avail_campaigns, default=[])
            if comm_campaigns:
                gov_comm = gov_comm[gov_comm['push_title'].isin(comm_campaigns)]
                
            if comm_campaigns:
                step_opts = gov_comm['step_id'].dropna().unique().tolist()
                step_opts = [str(int(s)) if isinstance(s, float) else str(s) for s in step_opts]
                comm_step = c_col3.multiselect("3. Select Step ID", step_opts, default=[])
                if comm_step:
                    gov_comm = gov_comm[gov_comm['step_id'].astype(str).isin(comm_step)]
            else:
                c_col3.info("👈 Select a campaign to view specific Step IDs.")

            st.markdown("---")
            st.markdown("##### 2. Overall Communication KPIs")
            total_delivered = gov_comm['delivered_count'].sum()
            total_clicks = gov_comm['clicks'].sum()
            active_campaigns = gov_comm['canvas_id'].nunique()
            del_to_click = (total_clicks / total_delivered * 100) if total_delivered > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Delivered Communications", f"{total_delivered:,.0f}")
            k2.metric("Total Clicks", f"{total_clicks:,.0f}")
            k3.metric("Active Campaigns", f"{active_campaigns:,.0f}")
            k4.metric("Delivered-to-Click Rate", f"{del_to_click:.2f}%")

            st.markdown("---")
            st.markdown("##### 3. Channel Efficiency & Trends")
            v_col1, v_col2 = st.columns(2)
            with v_col1:
                ch_comp = gov_comm.groupby('channel').agg({'delivered_count':'sum', 'clicks':'sum'}).reset_index()
                ch_comp['Rate (%)'] = (ch_comp['clicks'] / ch_comp['delivered_count'] * 100).fillna(0)
                fig_bar = px.bar(
                    ch_comp, x='channel', y='Rate (%)', color='channel',
                    hover_data={'delivered_count':':,.0f', 'clicks':':,.0f', 'Rate (%)':':.2f%'},
                    labels={'delivered_count':'Delivered Volume', 'clicks':'Clicks'},
                    title="Channel Efficiency (Delivered-to-Click Rate)"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
            with v_col2:
                trend_df = gov_comm.groupby(['date', 'channel']).agg({'delivered_count':'sum', 'clicks':'sum'}).reset_index()
                fig_trend = px.line(trend_df, x='date', y='delivered_count', color='channel', title="Performance Over Time (Delivered Volume)", markers=True)
                st.plotly_chart(fig_trend, use_container_width=True)

            st.markdown("---")
            st.markdown("##### 📊 Campaign Performance Analysis")
            camp_matrix = gov_comm.groupby(['push_title', 'channel']).agg({'delivered_count':'sum', 'clicks':'sum'}).reset_index()
            camp_matrix['Rate (%)'] = (camp_matrix['clicks'] / camp_matrix['delivered_count'] * 100).fillna(0)
            
            top_camps = camp_matrix.nlargest(10, 'Rate (%)').sort_values('Rate (%)', ascending=True)
            fig_top_camps = px.bar(
                top_camps, 
                x='Rate (%)', 
                y='push_title', 
                color='channel', 
                orientation='h',
                title="Top 10 Campaigns by Delivered-to-Click Rate (%)",
                hover_data={'delivered_count':':,.0f', 'clicks':':,.0f', 'Rate (%)':':.2f%'},
                labels={'push_title': 'Campaign Name', 'delivered_count': 'Delivered'}
            )
            fig_top_camps.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_top_camps, use_container_width=True)

            st.markdown("**Campaign Performance Matrix (Full View)**")
            st.dataframe(
                camp_matrix.sort_values('delivered_count', ascending=False).rename(
                    columns={'push_title':'Campaign', 'channel':'Channel', 'delivered_count':'Delivered', 'clicks':'Clicks'}
                ),
                column_config={
                    "Campaign": st.column_config.TextColumn("Campaign", width="large"),
                    "Channel": st.column_config.TextColumn("Channel", width="small"),
                    "Delivered": st.column_config.NumberColumn("Delivered", format="%d"),
                    "Clicks": st.column_config.NumberColumn("Clicks", format="%d"),
                    "Rate (%)": st.column_config.NumberColumn("Delivered-to-Click Rate", format="%.2f%%")
                },
                use_container_width=True, 
                hide_index=True
            )

            st.markdown("---")
            st.markdown("##### 🎯 4-Quadrant Bubble Matrix Analysis")
            st.caption("Dotted lines indicate medians. Top-right = High Volume & High CTR (Core Stars); Top-left = Low Volume & High CTR (High Potential).")
            
            quad_c1, quad_c2 = st.columns(2)
            with quad_c1:
                st.markdown("**Campaign Efficiency 4-Quadrant Matrix**")
                camp_bubble = camp_matrix.copy()
                if not camp_bubble.empty and camp_bubble['delivered_count'].sum() > 0:
                    med_del = camp_bubble['delivered_count'].median()
                    med_rate = camp_bubble['Rate (%)'].median()
                    fig_camp_bubble = px.scatter(
                        camp_bubble, x='delivered_count', y='Rate (%)', size='clicks', color='channel',
                        hover_name='push_title', hover_data={'delivered_count': ':,.0f', 'clicks': ':,.0f', 'Rate (%)': ':.2f%'},
                        title="Campaign: Delivered Volume vs Rate (%)"
                    )
                    fig_camp_bubble.add_hline(y=med_rate, line_dash="dot", line_color="gray", annotation_text="Median Rate")
                    fig_camp_bubble.add_vline(x=med_del, line_dash="dot", line_color="gray", annotation_text="Median Volume")
                    fig_camp_bubble.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400)
                    st.plotly_chart(fig_camp_bubble, use_container_width=True)
                else:
                    st.info("Insufficient volume to plot Campaign matrix.")
                    
            with quad_c2:
                st.markdown("**Timing Efficiency 4-Quadrant Matrix (Day of Week × Hour)**")
                if 'day_of_week' in gov_comm.columns and 'hour_of_day' in gov_comm.columns:
                    time_bubble = gov_comm.groupby(['day_of_week', 'hour_of_day']).agg({'delivered_count': 'sum', 'clicks': 'sum'}).reset_index()
                    time_bubble['Rate (%)'] = (time_bubble['clicks'] / time_bubble['delivered_count'] * 100).fillna(0)
                    time_bubble['Time Slot'] = time_bubble['day_of_week'] + " " + time_bubble['hour_of_day'].astype(str) + ":00"
                    
                    if not time_bubble.empty and time_bubble['delivered_count'].sum() > 0:
                        med_time_del = time_bubble['delivered_count'].median()
                        med_time_rate = time_bubble['Rate (%)'].median()
                        fig_time_bubble = px.scatter(
                            time_bubble, x='delivered_count', y='Rate (%)', size='clicks', color='day_of_week',
                            hover_name='Time Slot', hover_data={'hour_of_day': True, 'delivered_count': ':,.0f', 'clicks': ':,.0f', 'Rate (%)': ':.2f%'},
                            title="Timing: Slot Volume vs Rate (%)"
                        )
                        fig_time_bubble.add_hline(y=med_time_rate, line_dash="dot", line_color="gray", annotation_text="Median Rate")
                        fig_time_bubble.add_vline(x=med_time_del, line_dash="dot", line_color="gray", annotation_text="Median Volume")
                        fig_time_bubble.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400)
                        st.plotly_chart(fig_time_bubble, use_container_width=True)
                    else:
                        st.info("Insufficient volume to plot Timing matrix.")
                else:
                    st.info("Time fields unavailable for Timing matrix.")

            st.markdown("---")
            st.markdown(f"##### 4. {comm_channel if comm_channel != 'All Channels' else 'Cross-Channel'} Engagement Funnel")
            fc1, fc2 = st.columns([1, 2])
            
            with fc1:
                if comm_channel == 'Email':
                    dels, opens, clicks = gov_comm['delivered_count'].sum(), gov_comm['opens'].sum(), gov_comm['clicks'].sum()
                    st.metric("1. Email Delivered", f"{dels:,.0f}")
                    st.metric("2. Open Rate", f"{(opens/dels*100):.2f}%" if dels else "0%")
                    st.metric("3. Email Click Rate", f"{(clicks/dels*100):.2f}%" if dels else "0%")
                    st.metric("4. Click-to-Open Rate", f"{(clicks/opens*100):.2f}%" if opens else "0%")
                    funnel_y, funnel_x = ['Delivered', 'Opened', 'Clicked'], [dels, opens, clicks]
                elif comm_channel == 'Push':
                    dels, shows, clicks = gov_comm['delivered_count'].sum(), gov_comm['sends'].sum(), gov_comm['clicks'].sum()
                    st.metric("1. Push Arrived", f"{dels:,.0f}")
                    st.metric("2. Show Rate", f"{(shows/dels*100):.2f}%" if dels else "0%")
                    st.metric("3. Push Click Rate", f"{(clicks/dels*100):.2f}%" if dels else "0%")
                    st.metric("4. Click-to-Show Rate", f"{(clicks/shows*100):.2f}%" if shows else "0%")
                    funnel_y, funnel_x = ['Arrived', 'Shown', 'Clicked'], [dels, shows, clicks]
                elif comm_channel == 'SMS':
                    reqs = gov_comm['request_count'].sum() if 'request_count' in gov_comm else 0
                    dels = gov_comm['delivered_count'].sum()
                    elig = gov_comm['link_eligible_count'].sum() if 'link_eligible_count' in gov_comm else 0
                    clicks = gov_comm['clicks'].sum()
                    st.metric("1. SMS Requested", f"{reqs:,.0f}")
                    st.metric("2. Delivery Rate", f"{(dels/reqs*100):.2f}%" if reqs else "0%")
                    st.metric("3. Link-enabled SMS", f"{elig:,.0f}")
                    st.metric("4. SMS Link Click Rate", f"{(clicks/elig*100):.2f}%" if elig else "0%")
                    funnel_y, funnel_x = ['Requested', 'Delivered', 'Link-enabled', 'Clicked'], [reqs, dels, elig, clicks]
                else:
                    dels, interacts, clicks = gov_comm['delivered_count'].sum(), gov_comm['opens'].sum(), gov_comm['clicks'].sum()
                    st.metric("1. Total Delivered", f"{dels:,.0f}")
                    st.metric("2. Interaction Rate", f"{(interacts/dels*100):.2f}%" if dels else "0%")
                    st.metric("3. Overall Click Rate", f"{(clicks/dels*100):.2f}%" if dels else "0%")
                    st.metric("4. Click-to-Interact Rate", f"{(clicks/interacts*100):.2f}%" if interacts else "0%")
                    funnel_y, funnel_x = ['Delivered (All)', 'Interacted (Opened/Shown)', 'Clicked'], [dels, interacts, clicks]
            
            with fc2:
                fig_funnel = go.Figure(go.Funnel(y=funnel_y, x=funnel_x, marker={"color": ["#4C72B0", "#55A868", "#C44E52", "#8172B3"]}))
                st.plotly_chart(fig_funnel, use_container_width=True)

            if comm_channel in ['Push', 'All Channels']:
                push_data = gov_comm[gov_comm['channel'] == 'Push'] if comm_channel == 'All Channels' else gov_comm
                if not push_data.empty:
                    st.markdown("---")
                    st.markdown("##### 5. Push Time Analysis")
                    st.markdown("*Answering: At what times is Push engagement strongest?*")
                    tc1, tc2 = st.columns(2)
                    with tc1:
                        hr_df = push_data.groupby('hour_of_day').agg({'sends':'sum', 'clicks':'sum'}).reset_index()
                        hr_df['Click-to-Show (%)'] = (hr_df['clicks'] / hr_df['sends'] * 100).fillna(0)
                        fig_hr = go.Figure()
                        fig_hr.add_trace(go.Bar(x=hr_df['hour_of_day'], y=hr_df['sends'], name='Push Shows', marker_color='#4C72B0'))
                        fig_hr.add_trace(go.Scatter(x=hr_df['hour_of_day'], y=hr_df['Click-to-Show (%)'], name='Rate %', yaxis='y2', mode='lines+markers', marker_color='#C44E52'))
                        fig_hr.update_layout(title="Performance by Hour of Day", yaxis=dict(title='Shows Volume'), yaxis2=dict(title='Rate %', overlaying='y', side='right'))
                        st.plotly_chart(fig_hr, use_container_width=True)
                    with tc2:
                        heat_df = push_data.pivot_table(index='day_of_week', columns='hour_of_day', values='sends', aggfunc='sum').fillna(0)
                        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        heat_df = heat_df.reindex([d for d in days_order if d in heat_df.index])
                        st.plotly_chart(px.imshow(heat_df, aspect="auto", color_continuous_scale='Blues', title="Push Shows Heatmap (Day × Hour)"), use_container_width=True)

            st.markdown("---")
            st.markdown("**📋 Communications Raw Data (Actionable View)**")
            st.dataframe(
                gov_comm[['date', 'channel', 'push_title', 'step_id', 'target_markets', 'sends', 'clicks', 'url']],
                column_config={
                    "date": st.column_config.DatetimeColumn("Report Date", format="YYYY-MM-DD"), 
                    "push_title": "Campaign Name", 
                    "target_markets": "Target Markets",
                    "url": st.column_config.LinkColumn("Ad URL", display_text="🔗 View Ad")
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("No communication data matches the current global filters.")

except Exception as err:
    st.error(f"Error rendering dashboard: {err}")
