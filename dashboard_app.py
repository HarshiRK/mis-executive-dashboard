import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Executive AI Dashboard", page_icon="🤖", layout="wide")

# Professional Theme
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { border: 1px solid #e6e9ef; padding: 15px; border-radius: 10px; background: #ffffff; }
    .advice-box { background-color: #e8f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Executive AI MIS Dashboard")

uploaded_file = st.file_uploader("Upload Master Trial Balance", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # 1. LOAD DATA (Standard Robust Engine)
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None).fillna("")
        else:
            df_raw = pd.read_excel(uploaded_file, header=None).fillna("")

        # 2. HEADER & MONTH DETECTION
        header_idx = None
        for i in range(len(df_raw)):
            if "Particulars" in [str(v).strip() for v in df_raw.iloc[i]]:
                header_idx = i
                break

        month_keywords = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        col_to_month = {}
        for r in range(max(0, header_idx-5), header_idx):
            for c_idx, val in enumerate(df_raw.iloc[r]):
                if any(m in str(val).lower() for m in month_keywords):
                    col_to_month[c_idx] = str(val).strip()

        sub_headers = [str(s).strip() for s in df_raw.iloc[header_idx].tolist()]
        last_m, final_cols = "Base", []
        for i, s in enumerate(sub_headers):
            if i in col_to_month: last_m = col_to_month[i]
            if "Particulars" in s: final_cols.append(f"Ledger_{i}")
            else: final_cols.append(f"{last_m}|{s}|{i}")

        df = df_raw.iloc[header_idx + 1:].copy()
        df.columns = final_cols
        p_col = [c for c in df.columns if 'Ledger' in c][0]

        # 3. FILTERS
        all_months = sorted(list(set([c.split('|')[0] for c in final_cols if '|' in c])))
        st.sidebar.header("Executive Filters")
        m1 = st.sidebar.selectbox("Baseline Month", all_months, index=0)
        m2 = st.sidebar.selectbox("Current Month", all_months, index=len(all_months)-1)

        # 4. DATA PROCESSING
        def get_bal(m, data):
            cols = [c for c in data.columns if c.startswith(m)]
            def clean(x):
                try:
                    s = str(x).replace(' Dr', '').replace(' Cr', '').replace(',', '').strip()
                    return float(s) if s else 0.0
                except: return 0.0
            bal = [c for c in cols if 'Balance' in c or 'Closing' in c]
            if bal: return data[bal[0]].apply(clean)
            dr, cr = [c for c in cols if 'Debit' in c], [c for c in cols if 'Credit' in c]
            return (data[dr[0]].apply(clean) if dr else 0.0) - (data[cr[0]].apply(clean) if cr else 0.0)

        viz_df = pd.DataFrame({'Particulars': df[p_col], 'Old': get_bal(m1, df), 'New': get_bal(m2, df)})
        viz_df['Variance'] = viz_df['New'] - viz_df['Old']
        viz_df['Var_Pct'] = (viz_df['Variance'] / viz_df['Old'].replace(0, 1))

        # --- DASHBOARD SECTION ---

        # ROW 1: ENHANCED KPIs
        st.subheader("📌 Key Performance Indicators")
        total_old, total_new = viz_df['Old'].sum(), viz_df['New'].sum()
        var_abs = total_new - total_old
        var_pct = (var_abs / total_old) if total_old != 0 else 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(f"Balance ({m1})", f"₹{total_old:,.0f}")
        kpi2.metric(f"Balance ({m2})", f"₹{total_new:,.0f}", f"{var_abs:,.0f}")
        kpi3.metric("Growth %", f"{var_pct:.1%}")
        # High Risk Count (items that grew > 20%)
        risk_count = len(viz_df[viz_df['Var_Pct'] > 0.2])
        kpi4.metric("High Volatility Items", f"{risk_count}", "Check Advice")

        st.divider()

        # ROW 2: AI MANAGERIAL ADVICE
        st.subheader("💡 AI Managerial Insights")
        with st.container():
            # Logic-based AI Advice
            biggest_inc = viz_df.sort_values('Variance', ascending=False).iloc[0]
            biggest_dec = viz_df.sort_values('Variance', ascending=True).iloc[0]
            
            advice_html = f"""
            <div class="advice-box">
                <strong>Executive Summary:</strong> Overall, the portfolio has changed by {var_pct:.1%}. <br><br>
                🚩 <strong>Major Alert:</strong> The ledger <b>'{biggest_inc['Particulars']}'</b> saw the highest increase of 
                ₹{biggest_inc['Variance']:,.0f}. Audit is recommended if this exceeds budget.<br>
                ✅ <strong>Efficiency:</strong> Significant reduction observed in <b>'{biggest_dec['Particulars']}'</b>. 
                Investigate if this is a permanent saving or a timing difference.<br><br>
                <b>Strategic Advice:</b> Focus on the {risk_count} volatility items identified in the KPIs to maintain cash flow stability.
            </div>
            """
            st.markdown(advice_html, unsafe_allow_html=True)

        st.divider()

        # ROW 3: VISUALS
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("Variance Waterfall")
            top_w = viz_df.sort_values('Variance', ascending=False).head(6)
            fig_water = go.Figure(go.Waterfall(
                x = top_w['Particulars'], y = top_w['Variance'],
                measure = ["relative"] * len(top_w),
                connector = {"line":{"color":"#444"}}
            ))
            st.plotly_chart(fig_water, use_container_width=True)

        with col_r:
            st.subheader("Top Expense/Asset Mix")
            fig_pie = px.pie(viz_df[viz_df['New'] > 0].head(10), values='New', names='Particulars', hole=0.5)
            st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as e:
        st.error(f"Please check your Trial Balance headers. Error: {e}")
