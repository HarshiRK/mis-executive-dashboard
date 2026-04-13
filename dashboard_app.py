import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Executive MIS Dashboard", page_icon="📊", layout="wide")

# Professional Styling
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 Executive MIS Dashboard")
st.info("Upload the Master Trial Balance to view visual financial insights.")

uploaded_file = st.file_uploader("Upload File (Excel or CSV)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # 1. LOAD DATA
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None).fillna("")
        else:
            df_raw = pd.read_excel(uploaded_file, header=None).fillna("")

        # 2. LOCATE HEADERS
        header_idx = None
        for i in range(len(df_raw)):
            if "Particulars" in [str(v).strip() for v in df_raw.iloc[i]]:
                header_idx = i
                break

        # 3. IDENTIFY MONTHS
        month_list = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        col_to_month = {}
        for r in range(max(0, header_idx-5), header_idx):
            for c_idx, val in enumerate(df_raw.iloc[r]):
                if any(m in str(val).lower() for m in month_list):
                    col_to_month[c_idx] = str(val).strip()

        sub_headers = [str(s).strip() for s in df_raw.iloc[header_idx].tolist()]
        last_m = "Base"
        final_cols = []
        for i, s in enumerate(sub_headers):
            if i in col_to_month: last_m = col_to_month[i]
            if "Particulars" in s: final_cols.append(f"Ledger_{i}")
            else: final_cols.append(f"{last_m}|{s}|{i}")

        df = df_raw.iloc[header_idx + 1:].copy()
        df.columns = final_cols
        p_col = [c for c in df.columns if 'Ledger' in c][0]

        # 4. DASHBOARD FILTERS
        all_months = sorted(list(set([c.split('|')[0] for c in final_cols if '|' in c])))
        st.sidebar.header("Dashboard Controls")
        m1 = st.sidebar.selectbox("Base Month", all_months, index=0)
        m2 = st.sidebar.selectbox("Comparison Month", all_months, index=len(all_months)-1)

        # 5. DATA CLEANING ENGINE
        def get_balance(month, data):
            cols = [c for c in data.columns if c.startswith(month)]
            def clean(x):
                try:
                    s = str(x).replace(' Dr', '').replace(' Cr', '').replace(',', '').strip()
                    return float(s) if s else 0.0
                except: return 0.0
            
            bal = [c for c in cols if 'Balance' in c or 'Closing' in c]
            if bal: return data[bal[0]].apply(clean)
            dr, cr = [c for c in cols if 'Debit' in c], [c for c in cols if 'Credit' in c]
            return (data[dr[0]].apply(clean) if dr else 0.0) - (data[cr[0]].apply(clean) if cr else 0.0)

        viz_df = pd.DataFrame({
            'Particulars': df[p_col],
            'Old': get_balance(m1, df),
            'New': get_balance(m2, df)
        })
        viz_df['Variance'] = viz_df['New'] - viz_df['Old']

        # --- VISUAL SECTION ---
        
        # Metrics Row
        m_old, m_new = viz_df['Old'].sum(), viz_df['New'].sum()
        diff = m_new - m_old
        diff_pct = (diff / m_old) if m_old != 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric(f"Total Value ({m1})", f"₹{m_old:,.0f}")
        c2.metric(f"Total Value ({m2})", f"₹{m_new:,.0f}", f"{diff:,.0f}")
        c3.metric("Growth/Change", f"{diff_pct:.1%}")

        st.divider()

        # Charts Row
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Top 10 Variances")
            top_v = viz_df.reindex(viz_df.Variance.abs().sort_values(ascending=False).index).head(10)
            fig_bar = px.bar(top_v, x='Variance', y='Particulars', orientation='h', 
                             color='Variance', color_continuous_scale='RdYlGn')
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.subheader("Account Distribution")
            pie_df = viz_df[viz_df['New'] > 0].sort_values('New', ascending=False).head(15)
            fig_pie = px.pie(pie_df, values='New', names='Particulars', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as e:
        st.error(f"Please ensure the file has 'Particulars' and valid Month headers. Error: {e}")
