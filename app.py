import os
import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(
    page_title="Performance Marketing Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
st.markdown(
    """
    <style>
    ...
    </style>
    """,
    unsafe_allow_html=True
)


# Data loading
@st.cache_data
def load_data():
    ...
    return df_inapp, df_promo, df_comm_full


try:
    df_inapp, df_promo, df_comm = load_data()

    # Sidebar navigation block from Section 2
    ...

    # Page routing
    if nav_selection == "🏠 Home":
        ...

    elif nav_selection == "⚙️ Settings":
        # Settings block from Section 4
        ...

    elif nav_selection == "📈 Dashboards":
        # Keep your existing dashboard code here
        ...

except Exception as err:
    st.error(f"Error rendering dashboard: {err}")
