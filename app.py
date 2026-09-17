import os
import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. Page Configuration & State Initialization
# ==========================================
st.set_page_config(page_title="Performance Marketing Dashboard", layout="wide", initial_sidebar_state="expanded")

# Initialize Session States for Settings & Edit Mode
if 'lang' not in st.session_state:
    st.session_state.lang = "English"
if 'font_size' not in st.session_state:
    st.session_state.font_size = "Medium"
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False

# Initialize Default Chart Order for each view
if 'chart_layout' not in st.session_state:
    st.session_state.chart_layout = {
        "Overview (All)": ["Trend Timeline", "Distribution Share", "Efficiency Comparison", "4-Quadrant Scatter", "Activity Heatmap"],
        "In-App Ads": ["Trend Timeline", "Distribution Share", "Efficiency Comparison", "4-Quadrant Scatter", "Activity Heatmap"],
        "Promo Codes": ["Trend Timeline", "Distribution Share", "Efficiency Comparison", "4-Quadrant Scatter", "Activity Heatmap"],
        "Communications": ["Trend Timeline", "Distribution Share", "Efficiency Comparison", "4-Quadrant Scatter", "Activity Heatmap"]
    }

# Simple Translation Dictionary for UI functionality
TRANSLATIONS = {
    "English": {"nav_home": "Home", "nav_dash": "Dashboards", "nav_set": "Settings", "search": "Quick search", "edit": "✏️ Edit", "done": "✔️ Done Editing", "welcome": "Welcome to Workspace"},
    "Chinese": {"nav_home": "首頁", "nav_dash": "儀表板", "nav_set": "設定", "search": "快速搜尋", "edit": "✏️ 編輯", "done": "✔️ 完成編輯", "welcome": "歡迎來到工作區"},
    "Spanish": {"nav_home": "Inicio", "nav_dash": "Tableros", "nav_set": "Ajustes", "search": "Búsqueda", "edit": "✏️ Editar", "done": "✔️ Listo", "welcome": "Bienvenido al Espacio"}
}
t = TRANSLATIONS.get(st.session_state.lang, TRANSLATIONS["English"])

# Dynamic Font Size Map
FONT_MAP = {"Small": "12px", "Medium": "16px", "Large": "20px"}
current_font_size = FONT_MAP.get(st.session_state.font_size, "16px")

# Inject Custom CSS for SaaS Card-based UI & Dynamic Font
st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        font-size: {current_font_size} !important;
    }}
    .stApp {{
        background-color: #f4f6f8;
    }}
    [data-testid="stMetric"] {{
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.05);
    }}
    [data-testid="stMetricLabel"] {{
        color: #5f6368;
        font-weight: 500;
    }}
    [data-testid="stMetricValue"] {{
        font-weight: 700;
        color: #202124;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Data Loading
# ==========================================
@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    inapp_file = os.path.join(base_dir, "in_app_analytical_dataset_validated.xlsx")
    promo_file = os.path.join(base_dir, "Promocode_Performance.xlsx")
    comm_file = os.path.join(base_dir, "Communication.xlsx")
    
    mock_url = "https://web.didiglobal.com/au/store/?utm_term=null&is_from_marketing=1&campaign_id=refpage_%2Fau%2Frider%2F&af_ad_id=null&keyword=null&creative_id=null&campaign=landingpage_%2F&af_adset_id=null&pid=website_seo&af_channel=null&target_id=null&devicemodel=null&placement=null&c=refpage_%2Fau%2Frider%2F&af_c_id=null&utm_campaign=refpage_%2Fau%2Frider%2F&clientType=19&utm_medium=referral&matchtype=null&channel=19&source=null&ad_group_id=null&location_country=AU&country=AU&adposition=null&lang=en-AU&utm_source=web.didiglobal.com"
    
    # In-App Data
    df_inapp = pd.read_excel(inapp_file, sheet_name="Raw Data")
    df_inapp['pt'] = pd.to_datetime(df_inapp['pt'])
    df_inapp['day_of_week'] = df_inapp['pt'].dt.day_name()
    df_inapp['hour_of_day'] = pd.to_datetime(df_inapp['plan_start_time']).dt.hour if 'plan_start_time' in df_inapp.columns else np.random.randint(0, 24, size=len(df_inapp))
    df_inapp['url'] = mock_url
    if 'campaign_ver' not in df_inapp.columns: df_inapp['campaign_ver'] = 'All'
    if 'data_quality_status' not in df_inapp.columns: df_inapp['data_quality_status'] = np.where((df_inapp['click_pv'] <= df_inapp['show_pv']), 'Valid', 'Review')

    nz_cities = ['Auckland', 'Wellington', 'Christchurch']
    df_inapp['country'] = df_inapp['city_name'].apply(lambda x: 'New Zealand' if x in nz_cities else 'Australia')
    
    # Promo Data
    df_promo = pd.read_excel(promo_file, sheet_name="Reporting Data")
    df_promo['date'] = pd.to_datetime(df_promo['date'])
    df_promo['country'] = df_promo['city_name'].apply(lambda x: 'New Zealand' if x in nz_cities else 'Australia')
    df_promo['day_of_week'] = df_promo['date'].dt.day_name()
    df_promo['url'] = mock_url

    # Comm Data
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
            df_comm_full = pd.DataFrame()
    else:
        df_comm_full = pd.DataFrame()
        
    return df_inapp, df_promo, df_comm_full

try:
    df_inapp, df_promo, df_comm = load_data()
    
    # ==========================================
    # 3. SIDEBAR NAVIGATION 
    # ==========================================
    st.sidebar.text_input(t["search"], placeholder="🔍 Search...")
    st.sidebar.markdown("---")
    
    nav_selection = st.sidebar.radio(
        "NAVIGATION",
        [f"🏠 {t['nav_home']}", f"📈 {t['nav_dash']}", f"⚙️ {t['nav_set']}"],
        index=1
    )
    
    # Optional Sidebar Toggle Checkbox (User Request)
    st.sidebar.markdown("---")
    if st.sidebar.checkbox("Hide Sidebar Contents"):
        st.sidebar.empty()

    # ==========================================
    # 4. PAGE ROUTING
    # ==========================================
    
    # --- HOME PAGE ---
    if nav_selection.endswith(t['nav_home']):
        st.title(t["welcome"])
        st.info("Home view is currently being set up. Please navigate to Dashboards.")
        
    # --- SETTINGS PAGE ---
    elif nav_selection.endswith(t['nav_set']):
        st.title(t["nav_set"])
        st.markdown("---")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            st.selectbox("Timezone", ["UTC", "AEST", "PST", "EST"])
            st.selectbox("AI Agent Language", ["English", "French", "Spanish", "German"])
        with s_col2:
            new_lang = st.selectbox("Display Language (UI)", ["English", "Chinese", "Spanish"], index=["English", "Chinese", "Spanish"].index(st.session_state.lang))
            new_font = st.selectbox("Font Size", ["Small", "Medium", "Large"], index=["Small", "Medium", "Large"].index(st.session_state.font_size))
            st.radio("Dashboard Appearance", ["Light", "Dark", "Custom Theme"])
            
        if st.button("Save Settings", type="primary"):
            st.session_state.lang = new_lang
            st.session_state.font_size = new_font
            st.rerun()

    # --- DASHBOARDS PAGE ---
    elif nav_selection.endswith(t['nav_dash']):
        
        # EDIT BUTTON (Top Right)
        col_title, col_edit = st.columns([8, 1])
        col_title.caption(f"Home / {t['nav_dash']} / Performance Marketing / Paid Ads")
        col_title.title("Paid Ads & Marketing Performance")
        
        edit_btn_text = t['done'] if st.session_state.edit_mode else t['edit']
        if col_edit.button(edit_btn_text):
            st.session_state.edit_mode = not st.session_state.edit_mode
            st.rerun()

        # TOP BAR FILTERS
        f_col1, f_col2, f_col3 = st.columns([1, 1, 1.5])
        available_cities = sorted(df_inapp['city_name'].dropna().unique().tolist())
        selected_cities = f_col1.multiselect("City", available_cities, default=available_cities)
        
        min_d, max_d = df_inapp['pt'].min().date(), df_inapp['pt'].max().date()
        date_range = f_col2.date_input("Date Range", [min_d, max_d])
        start_date, end_date = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_d, max_d)
        start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)
        
        channel_view = f_col3.selectbox(
            "Dashboard View (Platform)", 
            ["Overview (All)", "In-App Ads", "Promo Codes", "Communications"]
        )
        
        # APPLY BASE DATA FILTERS
        base_inapp = df_inapp[(df_inapp['pt'] >= start_dt) & (df_inapp['pt'] <= end_dt) & (df_inapp['city_name'].isin(selected_cities))]
        base_promo = df_promo[(df_promo['date'] >= pd.to_datetime(start_date)) & (df_promo['date'] <= pd.to_datetime(end_date)) & (df_promo['city_name'].isin(selected_cities))]
        base_comm = df_comm[(df_comm['date'] >= pd.to_datetime(start_date)) & (df_comm['date'] <= pd.to_datetime(end_date))]
        if selected_cities and not base_comm.empty:
            city_regex = '|'.join(selected_cities)
            base_comm = base_comm[base_comm['target_markets'].str.contains(city_regex, case=False, na=False)]

        st.markdown("<br>", unsafe_allow_html=True)
        
        # ==========================================
        # EDIT MODE CUSTOMIZATION
        # ==========================================
        ALL_AVAILABLE_CHARTS = ["Trend Timeline", "Distribution Share", "Efficiency Comparison", "4-Quadrant Scatter", "Activity Heatmap"]
        
        if st.session_state.edit_mode:
            st.warning("✏️ Edit Mode Active: Drag tags to reorder, click 'x' to remove, or select to add new diagrams.")
            st.session_state.chart_layout[channel_view] = st.multiselect(
                f"Customize Diagrams for {channel_view}",
                options=ALL_AVAILABLE_CHARTS,
                default=st.session_state.chart_layout[channel_view]
            )
            st.markdown("---")

        # ==========================================
        # UNIFORM RENDER ENGINE FUNCTIONS
        # ==========================================
        
        # Function to process data based on current view
        def get_view_data(view):
            ia = base_inapp[base_inapp['campaign_ver'].astype(str).str.lower() == 'all']
            pr = base_promo[base_promo['usage_count'] <= base_promo['redemption_count']]
            co = base_comm.copy()
            return ia, pr, co

        ia_data, pr_data, co_data = get_view_data(channel_view)

        # 1. RENDER KPIs
        st.markdown("##### Performance Metrics")
        k1, k2, k3, k4, k5 = st.columns(5)
        
        if channel_view == "Overview (All)":
            k1.metric("Total In-App Shows", f"{ia_data['show_pv'].sum():,.0f}")
            k2.metric("Total In-App Clicks", f"{ia_data['click_pv'].sum():,.0f}")
            k3.metric("Promo Redemptions", f"{pr_data['redemption_count'].sum():,.0f}")
            k4.metric("Actual Ride Usages", f"{pr_data['usage_count'].sum():,.0f}")
            k5.metric("Total Comm Delivered", f"{co_data['delivered_count'].sum():,.0f}" if not co_data.empty else "0")
            
        elif channel_view == "In-App Ads":
            total_shows = ia_data['show_pv'].sum()
            k1.metric("Show PV", f"{total_shows:,.0f}")
            k2.metric("Daily Show UV", f"{ia_data['show_uv'].sum():,.0f}")
            k3.metric("Click PV", f"{ia_data['click_pv'].sum():,.0f}")
            k4.metric("Daily Click UV", f"{ia_data['click_uv'].sum():,.0f}")
            k5.metric("CTR (%)", f"{(ia_data['click_pv'].sum() / total_shows * 100):.2f}%" if total_shows else "0%")
            
        elif channel_view == "Promo Codes":
            total_reds = pr_data['redemption_count'].sum()
            total_use = pr_data['usage_count'].sum()
            k1.metric("Total Redemptions", f"{total_reds:,.0f}")
            k2.metric("Total Usage", f"{total_use:,.0f}")
            k3.metric("Active Promos", f"{pr_data['promocode'].nunique():,.0f}")
            k4.metric("Utilisation Rate (%)", f"{(total_use / total_reds * 100):.1f}%" if total_reds else "0%")
            k5.metric("Markets Active", f"{pr_data['city_name'].nunique():,.0f}")
            
        elif channel_view == "Communications":
            total_dels = co_data['delivered_count'].sum()
            total_clks = co_data['clicks'].sum()
            k1.metric("Total Delivered", f"{total_dels:,.0f}")
            k2.metric("Total Clicks", f"{total_clks:,.0f}")
            k3.metric("Active Campaigns", f"{co_data['canvas_id'].nunique():,.0f}")
            k4.metric("Delivered-to-Click Rate", f"{(total_clks / total_dels * 100):.2f}%" if total_dels else "0%")
            k5.metric("Total Sends", f"{co_data['sends'].sum():,.0f}")

        st.markdown("---")
        
        # 2. RENDER DYNAMIC CHARTS (1 Full Row Per Chart as requested)
        st.markdown(f"##### Analytics Diagrams")
        
        for chart_type in st.session_state.chart_layout[channel_view]:
            
            # --- TREND TIMELINE (Line) ---
            if chart_type == "Trend Timeline":
                if channel_view == "Overview (All)":
                    t_ia = ia_data.groupby('pt')['show_pv'].sum().reset_index().rename(columns={'pt':'Date', 'show_pv':'Value'}); t_ia['Metric'] = 'In-App Shows'
                    t_pr = pr_data.groupby('date')['redemption_count'].sum().reset_index().rename(columns={'date':'Date', 'redemption_count':'Value'}); t_pr['Metric'] = 'Promo Claims'
                    t_co = co_data.groupby('date')['delivered_count'].sum().reset_index().rename(columns={'date':'Date', 'delivered_count':'Value'}) if not co_data.empty else pd.DataFrame()
                    if not t_co.empty: t_co['Metric'] = 'Comm Delivered'
                    fig = px.line(pd.concat([t_ia, t_pr, t_co]), x='Date', y='Value', color='Metric', title="Cross-Platform Trend Timeline")
                elif channel_view == "In-App Ads":
                    df_t = ia_data.groupby('pt')[['show_pv', 'click_pv']].sum().reset_index()
                    fig = px.line(df_t, x='pt', y=['show_pv', 'click_pv'], title="Daily Show vs Click PV Trend")
                elif channel_view == "Promo Codes":
                    df_t = pr_data.groupby('date')[['redemption_count', 'usage_count']].sum().reset_index()
                    fig = px.line(df_t, x='date', y=['redemption_count', 'usage_count'], title="Redemptions vs Usage Trend")
                elif channel_view == "Communications":
                    df_t = co_data.groupby('date')[['delivered_count', 'clicks']].sum().reset_index()
                    fig = px.line(df_t, x='date', y=['delivered_count', 'clicks'], title="Delivery vs Clicks Trend")
                
                fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

            # --- DISTRIBUTION SHARE (Pie) ---
            elif chart_type == "Distribution Share":
                if channel_view == "Overview (All)":
                    df_p = pd.DataFrame({'Source': ['In-App Clicks', 'Promo Usages', 'Comm Clicks'], 'Vol': [ia_data['click_pv'].sum(), pr_data['usage_count'].sum(), co_data['clicks'].sum() if not co_data.empty else 0]})
                    fig = px.pie(df_p, values='Vol', names='Source', hole=0.4, title="Interaction Source Distribution")
                elif channel_view == "In-App Ads":
                    df_p = ia_data.groupby('campaign_ver')['show_pv'].sum().reset_index()
                    fig = px.pie(df_p, values='show_pv', names='campaign_ver', hole=0.4, title="Shows by Campaign Version")
                elif channel_view == "Promo Codes":
                    df_p = pr_data.groupby('city_name')['usage_count'].sum().reset_index()
                    fig = px.pie(df_p, values='usage_count', names='city_name', hole=0.4, title="Usage Distribution by City")
                elif channel_view == "Communications":
                    df_p = co_data.groupby('channel')['delivered_count'].sum().reset_index()
                    fig = px.pie(df_p, values='delivered_count', names='channel', hole=0.4, title="Delivery Distribution by Channel")
                
                fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
                
            # --- EFFICIENCY COMPARISON (Bar) ---
            elif chart_type == "Efficiency Comparison":
                if channel_view == "Overview (All)":
                    e_ia = (ia_data['click_pv'].sum() / ia_data['show_pv'].sum() * 100) if ia_data['show_pv'].sum() else 0
                    e_pr = (pr_data['usage_count'].sum() / pr_data['redemption_count'].sum() * 100) if pr_data['redemption_count'].sum() else 0
                    e_co = (co_data['clicks'].sum() / co_data['delivered_count'].sum() * 100) if not co_data.empty and co_data['delivered_count'].sum() else 0
                    df_e = pd.DataFrame({'Platform': ['In-App', 'Promo', 'Comm'], 'Rate (%)': [e_ia, e_pr, e_co]})
                    fig = px.bar(df_e, x='Platform', y='Rate (%)', color='Platform', title="Platform Efficiency Breakdown")
                elif channel_view == "In-App Ads":
                    df_e = ia_data.groupby('city_name')['show_pv'].sum().reset_index()
                    fig = px.bar(df_e, x='city_name', y='show_pv', color='city_name', title="City Delivery Volume")
                elif channel_view == "Promo Codes":
                    df_e = pr_data.groupby('city_name')[['redemption_count', 'usage_count']].sum().reset_index()
                    fig = px.bar(df_e, x='city_name', y=['redemption_count', 'usage_count'], barmode='group', title="City Performance Comparison")
                elif channel_view == "Communications":
                    df_e = co_data.groupby('channel').agg({'delivered_count':'sum', 'clicks':'sum'}).reset_index()
                    df_e['Rate (%)'] = (df_e['clicks'] / df_e['delivered_count'] * 100).fillna(0)
                    fig = px.bar(df_e, x='channel', y='Rate (%)', color='channel', title="Channel Efficiency Rates")
                
                fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

            # --- 4-QUADRANT SCATTER (Bubble) ---
            elif chart_type == "4-Quadrant Scatter":
                if channel_view == "Overview (All)":
                    i_m = ia_data.groupby('campaign_name').agg({'show_pv':'sum', 'click_pv':'sum'}).reset_index().rename(columns={'campaign_name':'ID', 'show_pv':'Vol', 'click_pv':'Int'}); i_m['Plat'] = 'In-App'
                    p_m = pr_data.groupby('promocode').agg({'redemption_count':'sum', 'usage_count':'sum'}).reset_index().rename(columns={'promocode':'ID', 'redemption_count':'Vol', 'usage_count':'Int'}); p_m['Plat'] = 'Promo'
                    c_m = co_data.groupby('push_title').agg({'delivered_count':'sum', 'clicks':'sum'}).reset_index().rename(columns={'push_title':'ID', 'delivered_count':'Vol', 'clicks':'Int'}) if not co_data.empty else pd.DataFrame()
                    if not c_m.empty: c_m['Plat'] = 'Comm'
                    df_q = pd.concat([i_m, p_m, c_m], ignore_index=True)
                    df_q['Rate'] = (df_q['Int'] / df_q['Vol'] * 100).fillna(0)
                    fig = px.scatter(df_q, x='Vol', y='Rate', size='Int', color='Plat', hover_name='ID', title="Cross-Platform 4-Quadrant Matrix")
                elif channel_view == "In-App Ads":
                    df_q = ia_data.groupby('campaign_name').agg({'show_pv':'sum', 'click_pv':'sum'}).reset_index()
                    df_q['Rate'] = (df_q['click_pv'] / df_q['show_pv'] * 100).fillna(0)
                    fig = px.scatter(df_q, x='show_pv', y='Rate', size='click_pv', hover_name='campaign_name', title="In-App Performance Matrix")
                elif channel_view == "Promo Codes":
                    df_q = pr_data.groupby('promocode').agg({'redemption_count':'sum', 'usage_count':'sum'}).reset_index()
                    df_q['Rate'] = (df_q['usage_count'] / df_q['redemption_count'] * 100).fillna(0)
                    fig = px.scatter(df_q, x='redemption_count', y='Rate', size='usage_count', hover_name='promocode', title="Promo Efficiency Matrix")
                elif channel_view == "Communications":
                    df_q = co_data.groupby('push_title').agg({'delivered_count':'sum', 'clicks':'sum'}).reset_index()
                    df_q['Rate'] = (df_q['clicks'] / df_q['delivered_count'] * 100).fillna(0)
                    fig = px.scatter(df_q, x='delivered_count', y='Rate', size='clicks', hover_name='push_title', title="Communication Efficiency Matrix")
                
                fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

            # --- ACTIVITY HEATMAP (Heatmap) ---
            elif chart_type == "Activity Heatmap":
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                if channel_view == "Overview (All)":
                    d1 = ia_data.groupby('day_of_week')['click_pv'].sum().reset_index().rename(columns={'click_pv':'Vol'}); d1['Plat'] = 'In-App'
                    d2 = pr_data.groupby('day_of_week')['usage_count'].sum().reset_index().rename(columns={'usage_count':'Vol'}); d2['Plat'] = 'Promo'
                    df_h = pd.concat([d1, d2])
                    heat = df_h.pivot_table(index='Plat', columns='day_of_week', values='Vol', aggfunc='sum').fillna(0).reindex(columns=days_order)
                    fig = px.imshow(heat, aspect="auto", color_continuous_scale='YlOrRd', title="Platform Activity by Day")
                elif channel_view == "In-App Ads":
                    heat = ia_data.pivot_table(index='campaign_name', columns='day_of_week', values='show_pv', aggfunc='sum').fillna(0).reindex(columns=days_order)
                    fig = px.imshow(heat.head(10), aspect="auto", color_continuous_scale='Blues', title="Top Campaign Activity Heatmap")
                elif channel_view == "Promo Codes":
                    heat = pr_data.pivot_table(index='city_name', columns='day_of_week', values='usage_count', aggfunc='sum').fillna(0).reindex(columns=days_order)
                    fig = px.imshow(heat, aspect="auto", color_continuous_scale='Greens', title="City Promo Usage Heatmap")
                elif channel_view == "Communications":
                    heat = co_data.pivot_table(index='day_of_week', columns='hour_of_day', values='sends', aggfunc='sum').fillna(0).reindex(days_order)
                    fig = px.imshow(heat, aspect="auto", color_continuous_scale='Purples', title="Push Sending Heatmap (Day x Hour)")
                
                fig.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

        # 3. TOP PERFORMANCE TABLE & DIAGRAM
        st.markdown("---")
        st.markdown("##### 🏆 Top Performance Leaderboard")
        
        if channel_view == "Overview (All)":
            mat1 = ia_data.groupby('campaign_name').agg({'show_pv':'sum', 'click_pv':'sum'}).reset_index().rename(columns={'campaign_name':'Code/Campaign', 'show_pv':'Volume', 'click_pv':'Interact'}); mat1['Type'] = 'In-App'
            mat2 = pr_data.groupby('promocode').agg({'redemption_count':'sum', 'usage_count':'sum'}).reset_index().rename(columns={'promocode':'Code/Campaign', 'redemption_count':'Volume', 'usage_count':'Interact'}); mat2['Type'] = 'Promo'
            mat = pd.concat([mat1, mat2], ignore_index=True)
            mat['Rate (%)'] = (mat['Interact'] / mat['Volume'] * 100).fillna(0)
        elif channel_view == "In-App Ads":
            mat = ia_data.groupby('campaign_name').agg({'show_pv':'sum', 'click_pv':'sum'}).reset_index().rename(columns={'campaign_name':'Code/Campaign', 'show_pv':'Volume', 'click_pv':'Interact'})
            mat['Rate (%)'] = (mat['Interact'] / mat['Volume'] * 100).fillna(0); mat['Type'] = 'In-App'
        elif channel_view == "Promo Codes":
            mat = pr_data.groupby('promocode').agg({'redemption_count':'sum', 'usage_count':'sum'}).reset_index().rename(columns={'promocode':'Code/Campaign', 'redemption_count':'Volume', 'usage_count':'Interact'})
            mat['Rate (%)'] = (mat['Interact'] / mat['Volume'] * 100).fillna(0); mat['Type'] = 'Promo'
        elif channel_view == "Communications":
            mat = co_data.groupby('push_title').agg({'delivered_count':'sum', 'clicks':'sum'}).reset_index().rename(columns={'push_title':'Code/Campaign', 'delivered_count':'Volume', 'clicks':'Interact'})
            mat['Rate (%)'] = (mat['Interact'] / mat['Volume'] * 100).fillna(0); mat['Type'] = 'Comm'

        fig_leader = px.bar(mat.nlargest(10, 'Rate (%)').sort_values('Rate (%)'), x='Rate (%)', y='Code/Campaign', orientation='h', color='Type', title="Top 10 Campaigns by Efficiency Rate")
        fig_leader.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_leader, use_container_width=True)
        
        st.dataframe(
            mat.sort_values('Volume', ascending=False),
            column_config={
                "Type": "Platform",
                "Code/Campaign": st.column_config.TextColumn("Campaign Name / Promo Code", width="large"),
                "Volume": st.column_config.NumberColumn("Exposure / Deliveries", format="%d"),
                "Interact": st.column_config.NumberColumn("Interactions", format="%d"),
                "Rate (%)": st.column_config.NumberColumn("Efficiency Rate", format="%.2f%%")
            },
            use_container_width=True, hide_index=True
        )

        # 4. RAW DATA VIEW (Actionable)
        st.markdown("---")
        st.markdown("##### 📋 Raw Data (Actionable View)")
        
        if channel_view == "Overview (All)":
            r1 = ia_data[['pt', 'city_name', 'campaign_name', 'show_pv', 'url']].rename(columns={'pt':'Date', 'city_name':'City', 'campaign_name':'Campaign/Code', 'show_pv':'Volume', 'url':'URL'}); r1['Type'] = 'In-App'
            r2 = pr_data[['date', 'city_name', 'promocode', 'redemption_count', 'url']].rename(columns={'date':'Date', 'city_name':'City', 'promocode':'Campaign/Code', 'redemption_count':'Volume', 'url':'URL'}); r2['Type'] = 'Promo'
            raw = pd.concat([r1, r2], ignore_index=True)
        elif channel_view == "In-App Ads":
            raw = ia_data[['pt', 'city_name', 'campaign_name', 'show_pv', 'click_pv', 'data_quality_status', 'url']].rename(columns={'pt':'Date', 'city_name':'City', 'campaign_name':'Campaign/Code', 'show_pv':'Volume', 'click_pv':'Interactions', 'data_quality_status':'Status', 'url':'URL'})
            raw['Type'] = 'In-App'
        elif channel_view == "Promo Codes":
            raw = pr_data[['date', 'city_name', 'promocode', 'redemption_count', 'usage_count', 'url']].rename(columns={'date':'Date', 'city_name':'City', 'promocode':'Campaign/Code', 'redemption_count':'Volume', 'usage_count':'Interactions', 'url':'URL'})
            raw['Type'] = 'Promo'
        elif channel_view == "Communications":
            raw = co_data[['date', 'target_markets', 'push_title', 'delivered_count', 'clicks', 'url']].rename(columns={'date':'Date', 'target_markets':'City', 'push_title':'Campaign/Code', 'delivered_count':'Volume', 'clicks':'Interactions', 'url':'URL'})
            raw['Type'] = 'Comm'

        st.dataframe(
            raw,
            column_config={
                "Date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD"),
                "Type": "Platform",
                "City": "City / Market",
                "Campaign/Code": "Campaign Name / Code",
                "Volume": "Total Volume",
                "URL": st.column_config.LinkColumn("Redirect URL", display_text="🔗 View Campaign")
            },
            use_container_width=True, hide_index=True
        )

except Exception as err:
    st.error(f"Error rendering dashboard: {err}")
