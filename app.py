import gradio as gr
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

# ==========================================
# PART 1: Generate 1 Year of Historical Mock Data (Combined from d72ededd)
# ==========================================
np.random.seed(42)

# Generate a date range for the past 365 days
end_date = pd.to_datetime('today')
start_date = end_date - pd.Timedelta(days=365)
date_range = pd.date_range(start=start_date, end=end_date, freq='D')

platforms_for_mock = ['Meta Ads', 'Quoll Email', 'App Promo Zone'] # Renamed
tiers_for_mock = ['10% Off', '20% Off', '50% Off'] # Renamed

mock_data_list = []
for d in date_range:
    # Generate 1 to 3 entries per day
    for _ in range(np.random.randint(1, 4)):
        plat = np.random.choice(platforms_for_mock)
        tier = np.random.choice(tiers_for_mock)

        clicks = np.random.randint(500, 5000)
        if tier == '10% Off':
            redeemed = int(clicks * np.random.uniform(0.1, 0.3))
        elif tier == '20% Off':
            redeemed = int(clicks * np.random.uniform(0.3, 0.6))
        else:
            redeemed = int(clicks * np.random.uniform(0.6, 0.8))

        trips = int(redeemed * np.random.uniform(0.4, 0.9))

        mock_data_list.append({
            'Date': d,
            'Platform': plat,
            'Voucher_Tier': tier,
            'Clicks': clicks,
            'Redeemed_Vouchers': redeemed,
            'Actual_Trips': trips
        })

initial_global_df = pd.DataFrame(mock_data_list)
initial_global_df['Date'] = pd.to_datetime(initial_global_df['Date'])

# Define the theme separately
orange_theme = gr.themes.Default(primary_hue="orange")

# Redefine platforms and tiers for Gradio dropdown choices
platforms = ['Meta Ads', 'Quoll Email', 'App Promo Zone']
tiers = ['10% Off', '20% Off', '50% Off']

# ==========================================
# PART 2: Backend Functions (Logic) - Modified for gr.State
# ==========================================

def submit_data(df, input_date, platform, tier, clicks, redeemed, trips):
    new_record = pd.DataFrame([{
        'Date': pd.to_datetime(input_date),
        'Platform': platform,
        'Voucher_Tier': tier,
        'Clicks': int(clicks),
        'Redeemed_Vouchers': int(redeemed),
        'Actual_Trips': int(trips)
    }])
    df = pd.concat([df, new_record], ignore_index=True)
    df = df.sort_values(by='Date').reset_index(drop=True)
    msg = f"✅ Success! Data for {input_date} added to the database."
    return msg, df.tail(5), df # Return updated df for state

def generate_report(df, report_type, start_d, end_d):
    df_filtered = df.copy() # Work on a copy

    # 1. Filter by Date if Custom
    if report_type == "Custom Date Range":
        df_filtered = df_filtered[(df_filtered['Date'] >= pd.to_datetime(start_d)) & (df_filtered['Date'] <= pd.to_datetime(end_d))]

    if df_filtered.empty:
        # Return empty figures and the original df state if no data
        return "⚠️ No data available for this period. Try adjusting your date range.", go.Figure(), go.Figure(), df

    # 2. Aggregate Data Based on Report Type
    if report_type == "Daily":
        df_filtered['Time_Period'] = df_filtered['Date'].dt.date.astype(str)
    elif report_type == "Weekly":
        # %V for week number in year (01-53), Monday as the first day of the week.
        df_filtered['Time_Period'] = df_filtered['Date'].dt.strftime('%Y-W%V')
    elif report_type == "Monthly":
        df_filtered['Time_Period'] = df_filtered['Date'].dt.strftime('%Y-%m')
    elif report_type == "Yearly":
        df_filtered['Time_Period'] = df_filtered['Date'].dt.year.astype(str)
    # No else: default behavior implies no aggregation if type is not recognized,
    # but the radio buttons ensure one of these is always selected.

    # Ensure Time_Period is sorted for correct trend plotting
    agg_time = df_filtered.groupby('Time_Period')[['Clicks', 'Redeemed_Vouchers', 'Actual_Trips']].sum().reset_index()
    agg_time['Time_Period'] = pd.Categorical(agg_time['Time_Period'], categories=agg_time['Time_Period'].unique(), ordered=True) # Ensure correct sorting for plotly
    agg_time = agg_time.sort_values('Time_Period')


    # 3. Create Trend Chart
    fig_trend = px.line(
        agg_time, x='Time_Period', y=['Redeemed_Vouchers', 'Actual_Trips'],
        markers=True, title="Performance Trend",
        color_discrete_sequence=["#999999", "#FF5A00"]
    )
    fig_trend.update_layout(template="plotly_white", xaxis_title="Time Period", yaxis_title="Count")

    # 4. Create Platform Breakdown
    agg_plat = df_filtered.groupby('Platform')[['Redeemed_Vouchers', 'Actual_Trips']].sum().reset_index()
    fig_plat = px.bar(
        agg_plat, x='Platform', y=['Redeemed_Vouchers', 'Actual_Trips'],
        barmode='group', title="Platform Summary",
        color_discrete_sequence=["#CCCCCC", "#FF5A00"]
    )
    fig_plat.update_layout(template="plotly_white", yaxis_title="Count")

    # 5. KPIs
    total_red = agg_time['Redeemed_Vouchers'].sum()
    total_trp = agg_time['Actual_Trips'].sum()
    conv_rate = (total_trp / total_red * 100) if total_red > 0 else 0
    kpi_text = f"**Total Redeemed:** {total_red:,} | **Total Trips:** {total_trp:,} | **Conversion:** {conv_rate:.1f}%"

    return kpi_text, fig_trend, fig_plat, df # Return the stateful df

with gr.Blocks() as report_app:
    # Use gr.State to maintain the DataFrame across interactions
    current_df_state = gr.State(initial_global_df)

    gr.Markdown("# 🚗 DiDi Central Data & Reporting Framework")

    with gr.Tabs():
        with gr.TabItem("📝 1. Data Entry Portal"):
            with gr.Row():
                with gr.Column():
                    in_date = gr.Textbox(label="Date (YYYY-MM-DD)", value=str(date.today()))
                    in_plat = gr.Dropdown(choices=platforms, value="Meta Ads", label="Platform")
                    in_tier = gr.Dropdown(choices=tiers, value="20% Off", label="Voucher Tier")
                with gr.Column():
                    in_clicks = gr.Number(label="Total Clicks / Opens", value=1000)
                    in_red = gr.Number(label="Vouchers Redeemed", value=450)
                    in_trips = gr.Number(label="Actual Trips", value=300)
            btn_submit = gr.Button("Submit Data", variant="primary")
            msg_status = gr.Markdown()
            table_preview = gr.Dataframe(label="Latest Entries")
            btn_submit.click(
                fn=submit_data,
                inputs=[current_df_state, in_date, in_plat, in_tier, in_clicks, in_red, in_trips],
                outputs=[msg_status, table_preview, current_df_state]
            )

        with gr.TabItem("📊 2. Report Generator"):
            with gr.Row():
                report_type = gr.Radio(choices=["Daily", "Weekly", "Monthly", "Yearly", "Custom Date Range"], value="Monthly", label="Time Scale")
                custom_start = gr.Textbox(label="Start Date", value=str(date.today() - timedelta(days=30)))
                custom_end = gr.Textbox(label="End Date", value=str(date.today()))
            btn_generate = gr.Button("Generate Report", variant="primary")
            out_kpis = gr.Markdown()
            out_plot_trend = gr.Plot()
            out_plot_plat = gr.Plot()
            btn_generate.click(
                fn=generate_report,
                inputs=[current_df_state, report_type, custom_start, custom_end],
                outputs=[out_kpis, out_plot_trend, out_plot_plat, current_df_state]
            )

# Pass theme to launch.
report_app.launch(theme=orange_theme)
