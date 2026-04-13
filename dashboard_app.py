import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

st.set_page_config(page_title="Executive AI Dashboard", page_icon="🤖", layout="wide")

# UI Enhancements
st.markdown("""
    <style>
    .stMetric { border: 1px solid #dee2e6; padding: 20px; border-radius: 12px; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .advice-box { background-color: #f8fbff; padding: 25px; border-radius: 15px; border-left: 6px solid #007bff; color: #2c3e50; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Executive AI MIS Dashboard")

uploaded_file = st.file_uploader("Upload Trial Balance", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # 1. DYNAMIC DATA LOAD
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None).fillna("")
        else:
            df_raw = pd.read_excel(uploaded_file, header=None).fillna("")

        # 2. FIND THE DATA START (Particulars Row)
        header_idx = None
        for i in range(len(df_raw)):
            row_vals = [str(v).strip().lower() for v in df_raw.iloc[i]]
            if "particulars" in row_vals or "account" in row_vals:
                header_idx = i
                break
        
        if header_idx is None:
            st.error("❌ Could not find the 'Particulars' column. Please check your Excel headers.")
            st.stop()

        # 3. IDENTIFY TIMELINES (Months)
        months_ref = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        col_month_map = {}
        for r in range(0, header_idx + 1):
            for c_idx, val in enumerate(df_raw.iloc[r]):
                v_str = str(val).lower()
                if any(m in v_str for m in months_ref):
                    # Clean month name (remove brackets/commas)
                    clean_name = re.sub(r'[^a-zA-Z0-9 ]', '', str(val)).strip()
                    col_month_map[c_idx] = clean_name

        # 4. MAPPING COLUMNS
        sub_headers = [str(s).strip() for s in df_raw.iloc[header_idx]]
        final_cols = []
        current_m = "Initial"
        
        for i, s in enumerate(sub_headers):
            if i in col_month_map: current_m = col_month_map[i]
            
            if "particulars" in s.lower():
                final_cols.append(f"Account_{i}")
            else:
                final_cols.append(f"{current_m}|{s}|{i}")

        # 5. DATA CLEANING
        df_clean = df_raw.iloc[header_idx + 1:].copy()
        df_clean.columns = final_cols
        p_col = [c for c in df_clean.columns if 'Account' in c][0]

        # 6. MONTH SELECTION
        unique_m = sorted(list(set([c.split('|')[0] for c in final_cols if '|' in c])))
        st.sidebar.header("Control Panel")
        m1 = st.sidebar.selectbox("Base Month", unique_m, index=0)
        m2 = st.sidebar.selectbox("Current Month", unique_m, index=len(unique_m)-1)

        # 7. NUMERIC ENGINE
        def get_amount(month, data):
            cols = [c for c in data.columns if c.startswith(month)]
            def to_f(x):
                # Handles (100), 100 Dr, 1,000.00
                s = str(x).replace(',', '').replace('(', '-').replace(')', '').replace('Dr', '').replace('Cr', '').strip()
                try: return float(s) if s and s != "-" else 0.0
                except: return 0.0

            # Logic: Look for Debit/Credit first
            dr_c = [c for c in cols if 'debit' in c.lower()]
            cr_c = [c for c in cols if 'credit' in c.lower()]
            
            if dr_c and cr_c:
                return data[dr_c[0]].apply(to_f) - data[cr_c[0]].apply(to_f)
            elif cols:
                return data[cols[0]].apply(to_f) # Default to first column if no Dr/Cr
            return 0.0

        viz_df = pd.DataFrame({
            'Ledger': df_clean[p_col],
            'Base': get_amount(m1, df_clean),
            'Curr': get_amount(m2, df_clean)
        })
        
        # Remove empty rows to force KPIs to calculate real numbers
        viz_df = viz_df[(viz_df['Base'] != 0) | (viz_df['Curr'] != 0)].dropna()
        viz_df['Variance'] = viz_df['Curr'] - viz_df['Base']

        # --- OUTPUT ---
        val_b, val_c = viz_df['Base'].sum(), viz_df['Curr'].sum()
        var_total = val_c - val_b

        st.subheader("📊 Strategic Metrics")
        k1, k2, k3 = st.columns(3)
        k1.metric(m1, f"₹{val_b:,.2f}")
        k2.metric(m2, f"₹{val_c:,.2f}", f"{var_total:,.2f}")
        k3.metric("Change %", f"{(var_total/val_b if val_b !=0 else 0):.1%}")

        st.divider()

        # AI ADVICE
        st.subheader("💡 Managerial Insights")
        top_inc = viz_df.sort_values('Variance', ascending=False).iloc[0]
        st.markdown(f"""
        <div class="advice-box">
            The net movement is <b>₹{var_total:,.2f}</b>. <br>
            <b>Key Finding:</b> The account <i>'{top_inc['Ledger']}'</i> has moved the most this period. 
            Check if this relates to any new billing or expense cycles in {m2}.
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            fig_bar = px.bar(viz_df.sort_values('Variance').tail(10), x='Variance', y='Ledger', orientation='h', title="Top 10 Fluctuations")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_pie = px.pie(viz_df[viz_df['Curr'] > 0].head(10), values='Curr', names='Ledger', title="Account Mix")
            st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing file: {e}")
