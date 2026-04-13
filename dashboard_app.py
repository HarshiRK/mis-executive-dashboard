import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

st.set_page_config(page_title="Universal AI MIS", page_icon="🤖", layout="wide")

# High-End UI Styling
st.markdown("""
    <style>
    .stMetric { border: 1px solid #dee2e6; padding: 20px; border-radius: 12px; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .advice-box { background-color: #f8fbff; padding: 25px; border-radius: 15px; border-left: 6px solid #007bff; color: #2c3e50; font-size: 16px; line-height: 1.6; }
    .main-title { color: #1e3a8a; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Universal Executive AI Dashboard")
st.markdown("### Strategic Financial Insights • Auto-Detection Active")

uploaded_file = st.file_uploader("Upload any Tally/Excel Trial Balance", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # 1. DYNAMIC FILE LOADING
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None).fillna("")
        else:
            df_raw = pd.read_excel(uploaded_file, header=None).fillna("")

        # 2. FIND DATA ANCHOR (Search for 'Particulars' anywhere)
        header_idx = None
        for i in range(len(df_raw)):
            if any("particulars" in str(v).lower() for v in df_raw.iloc[i]):
                header_idx = i
                break
        
        if header_idx is None:
            st.error("❌ 'Particulars' column not found. Please ensure the file contains account names.")
            st.stop()

        # 3. SMART TIMELINE ENGINE (Scans top rows for Month names)
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        col_map = {}
        
        # Look through all rows from the top down to the Particulars row
        for r in range(0, header_idx + 1):
            for c, val in enumerate(df_raw.iloc[r]):
                val_str = str(val).strip().lower()
                if any(m in val_str for m in months):
                    # Clean the month name (remove brackets, etc.)
                    clean_m = re.sub(r'[\[\]]', '', str(val)).strip()
                    col_map[c] = clean_m

        # 4. FORWARD-FILL COLUMNS
        # This ensures that if 'February' is in Col 2, then Col 3 and 4 also belong to February
        sub_headers = [str(s).strip() for s in df_raw.iloc[header_idx]]
        final_cols = []
        current_m = "Opening/Base"
        
        for i, s in enumerate(sub_headers):
            if i in col_map: current_m = col_map[i]
            
            if "particulars" in s.lower():
                final_cols.append(f"Account_{i}")
            elif s == "" or s.lower() == "nan":
                final_cols.append(f"Ignore_{i}")
            else:
                # Format: "Month | SubHeader | Index"
                final_cols.append(f"{current_m}|{s}|{i}")

        # 5. DATA CLEANING
        df = df_raw.iloc[header_idx + 1:].copy()
        df.columns = final_cols
        p_col = [c for c in df.columns if 'Account' in c][0]

        # 6. EXECUTIVE FILTERING
        unique_months = sorted(list(set([c.split('|')[0] for c in final_cols if '|' in c])))
        
        st.sidebar.header("📊 Dashboard Settings")
        m1 = st.sidebar.selectbox("Base Period", unique_months, index=0)
        m2 = st.sidebar.selectbox("Comparison Period", unique_months, index=len(unique_months)-1)

        # 7. UNIVERSAL MATH ENGINE
        def calculate_net(month_name, data):
            relevant = [c for c in data.columns if c.startswith(month_name)]
            def to_num(x):
                # Robust cleaning of strings like "(1,200.00) Dr"
                s = str(x).replace(',', '').replace('(', '-').replace(')', '').replace('Dr', '').replace('Cr', '').strip()
                try: return float(s) if s else 0.0
                except: return 0.0

            # Logic: If 'Debit' and 'Credit' exist, Net them. Otherwise, take the first numeric column.
            dr_cols = [c for c in relevant if 'debit' in c.lower()]
            cr_cols = [c for c in relevant if 'credit' in c.lower()]
            bal_cols = [c for c in relevant if any(k in c.lower() for k in ['balance', 'closing', 'amount'])]

            if dr_cols and cr_cols:
                return data[dr_cols[0]].apply(to_num) - data[cr_cols[0]].apply(to_num)
            elif bal_cols:
                return data[bal_cols[0]].apply(to_num)
            elif relevant:
                return data[relevant[0]].apply(to_num)
            return 0.0

        viz_df = pd.DataFrame({
            'Ledger': df[p_col],
            'Old': calculate_net(m1, df),
            'New': calculate_net(m2, df)
        })
        viz_df = viz_df[(viz_df['Old'] != 0) | (viz_df['New'] != 0)]
        viz_df['Variance'] = viz_df['New'] - viz_df['Old']

        # 8. THE DASHBOARD VIEW
        val_old, val_new = viz_df['Old'].sum(), viz_df['New'].sum()
        var_total = val_new - val_old
        
        # --- KPI SECTION ---
        st.subheader("📌 Performance Metrics")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f"Total {m1}", f"₹{val_old:,.0f}")
        k2.metric(f"Total {m2}", f"₹{val_new:,.0f}", f"{var_total:,.0f}")
        k3.metric("Growth %", f"{(var_total/val_old if val_old !=0 else 0):.1%}")
        k4.metric("Active Ledgers", len(viz_df))

        st.divider()

        # --- AI ADVICE SECTION ---
        st.subheader("💡 AI Managerial Consultant")
        top_spike = viz_df.sort_values('Variance', ascending=False).iloc[0]
        top_drop = viz_df.sort_values('Variance', ascending=True).iloc[0]
        
        st.markdown(f"""
        <div class="advice-box">
            <strong>Executive Briefing:</strong><br>
            The portfolio has shifted by <b>₹{var_total:,.2f}</b> between {m1} and {m2}.<br><br>
            ⚠️ <b>Priority Alert:</b> <i>'{top_spike['Ledger']}'</i> shows the most significant upward movement. 
            Management should verify if this aligns with current project timelines.<br>
            📉 <b>Efficiency Note:</b> <i>'{top_drop['Ledger']}'</i> has decreased significantly. 
            This represents either a successful cost reduction or a delay in billing that needs investigation.
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # --- CHARTS ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Significant Variances")
            fig = px.bar(viz_df.sort_values('Variance').tail(10), x='Variance', y='Ledger', 
                         orientation='h', color='Variance', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("Value Composition")
            fig_p = px.pie(viz_df[viz_df['New'] > 0].head(12), values='New', names='Ledger', hole=0.4)
            st.plotly_chart(fig_p, use_container_width=True)

    except Exception as e:
        st.error(f"The tool encountered an unexpected structure: {e}")
