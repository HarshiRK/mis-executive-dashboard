import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

st.set_page_config(page_title="Executive AI Dashboard", page_icon="🤖", layout="wide")

# Professional Styling
st.markdown("""
    <style>
    .stMetric { border: 1px solid #e6e9ef; padding: 15px; border-radius: 10px; background: #ffffff; }
    .advice-box { background-color: #f0f7f9; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; color: #1a1a1a; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Executive AI MIS Dashboard")

uploaded_file = st.file_uploader("Upload Trial Balance", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # 1. LOAD DATA
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None).fillna("")
        else:
            df_raw = pd.read_excel(uploaded_file, header=None).fillna("")

        # 2. FIND HEADER ROW
        header_idx = None
        for i in range(len(df_raw)):
            row_str = " ".join([str(v) for v in df_raw.iloc[i]])
            if "Particulars" in row_str:
                header_idx = i
                break

        # 3. ADVANCED MONTH DETECTION (Handles [February, 2026] format)
        month_map = {}
        # Search top 10 rows for anything that looks like a month
        months_pattern = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
        for r in range(0, header_idx):
            for c_idx, val in enumerate(df_raw.iloc[r]):
                if re.search(months_pattern, str(val).lower()):
                    month_map[c_idx] = str(val).strip().replace("[", "").replace("]", "")

        sub_headers = [str(s).strip() for s in df_raw.iloc[header_idx].tolist()]
        last_m, final_cols = "Opening", []
        for i, s in enumerate(sub_headers):
            if i in month_map: last_m = month_map[i]
            if "Particulars" in s: final_cols.append(f"Ledger_{i}")
            else: final_cols.append(f"{last_m}|{s}|{i}")

        df = df_raw.iloc[header_idx + 1:].copy()
        df.columns = final_cols
        p_col = [c for c in df.columns if 'Ledger' in c][0]

        # 4. DROPDOWN SELECTION
        all_months = sorted(list(set([c.split('|')[0] for c in final_cols if '|' in c])))
        m1 = st.sidebar.selectbox("Base Month", all_months, index=0)
        m2 = st.sidebar.selectbox("Current Month", all_months, index=len(all_months)-1)

        # 5. REINFORCED MATH ENGINE
        def get_val(m, data):
            cols = [c for c in data.columns if c.startswith(m)]
            def clean(x):
                try:
                    # Remove all non-numeric chars except . and -
                    s = re.sub(r'[^\d.-]', '', str(x))
                    return float(s) if s else 0.0
                except: return 0.0
            
            # Find Debit and Credit specifically
            dr = [c for c in cols if 'debit' in c.lower()]
            cr = [c for c in cols if 'credit' in c.lower()]
            bal = [c for c in cols if 'balance' in c.lower() or 'closing' in c.lower()]

            if bal: return data[bal[0]].apply(clean)
            
            dr_v = data[dr[0]].apply(clean) if dr else 0.0
            cr_v = data[cr[0]].apply(clean) if cr else 0.0
            return dr_v - cr_v

        # 6. ASSEMBLE VIZ DATAFRAME
        viz_df = pd.DataFrame({
            'Particulars': df[p_col],
            'Old': get_val(m1, df),
            'New': get_val(m2, df)
        })
        # Filter out rows where both are 0 (empty rows)
        viz_df = viz_df[(viz_df['Old'] != 0) | (viz_df['New'] != 0)]
        viz_df['Variance'] = viz_df['New'] - viz_df['Old']

        # --- THE DASHBOARD ---
        t_old, t_new = viz_df['Old'].sum(), viz_df['New'].sum()
        v_abs = t_new - t_old
        v_pct = (v_abs / t_old) if t_old != 0 else 0

        st.subheader("📌 Key Financial Metrics")
        k1, k2, k3 = st.columns(3)
        k1.metric(f"Balance ({m1})", f"₹{t_old:,.2f}")
        k2.metric(f"Balance ({m2})", f"₹{t_new:,.2f}", f"{v_abs:,.2f}")
        k3.metric("Change %", f"{v_pct:.1%}")

        st.divider()

        st.subheader("💡 AI Managerial Advice")
        top_inc = viz_df.sort_values('Variance', ascending=False).iloc[0]
        top_dec = viz_df.sort_values('Variance', ascending=True).iloc[0]
        
        st.markdown(f"""
        <div class="advice-box">
            <strong>Financial Insight:</strong> The net movement across all ledgers is <b>₹{v_abs:,.2f}</b>. <br><br>
            ⚠️ <strong>Action Required:</strong> The account <b>'{top_inc['Particulars']}'</b> shows the highest variance increase. 
            Ensure this aligns with current operational goals. <br>
            🔍 <strong>Opportunity:</strong> Significant reduction in <b>'{top_dec['Particulars']}'</b> suggests cost-saving 
            or high recovery in this period.
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        c_left, c_right = st.columns(2)
        with c_left:
            st.subheader("Top 10 Variance Analysis")
            fig = px.bar(viz_df.sort_values('Variance', ascending=False).head(10), 
                         x='Variance', y='Particulars', orientation='h', color='Variance',
                         color_continuous_scale='RdYlGn')
            st.plotly_chart(fig, use_container_width=True)
            
        with c_right:
            st.subheader("Account Mix")
            fig_p = px.pie(viz_df[viz_df['New'] > 0].head(10), values='New', names='Particulars')
            st.plotly_chart(fig_p, use_container_width=True)

    except Exception as e:
        st.error(f"Analysis failed. Please check file structure. Error: {e}")
