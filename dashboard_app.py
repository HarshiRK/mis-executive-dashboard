import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

st.set_page_config(page_title="Executive AI Dashboard", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    .stMetric { border: 1px solid #e6e9ef; padding: 15px; border-radius: 10px; background: #ffffff; }
    .advice-box { background-color: #f0f7f9; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; color: #111; }
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

        # 2. FIND HEADER ROW (Search for Particulars)
        header_idx = None
        for i in range(len(df_raw)):
            row_str = " ".join([str(v) for v in df_raw.iloc[i]])
            if "Particulars" in row_str:
                header_idx = i
                break

        if header_idx is None:
            st.error("Could not find 'Particulars' column.")
            st.stop()

        # 3. SPATIAL MONTH DETECTION
        # We find every cell that looks like a month and remember its column index
        month_found = [] # List of (column_index, month_name)
        month_pattern = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
        
        for r in range(0, header_idx):
            for c_idx, val in enumerate(df_raw.iloc[r]):
                val_clean = str(val).strip().replace("[", "").replace("]", "").replace(",", "")
                if re.search(month_pattern, val_clean.lower()):
                    month_found.append((c_idx, val_clean))

        # 4. MAP COLUMNS TO MONTHS
        sub_headers = [str(s).strip() for s in df_raw.iloc[header_idx].tolist()]
        final_columns = []
        
        for i, s in enumerate(sub_headers):
            # Find the month that is closest to the left of this column
            current_m = "Opening"
            for m_idx, m_name in month_found:
                if i >= m_idx:
                    current_m = m_name
            
            if "Particulars" in s:
                final_columns.append(f"Ledger_{i}")
            else:
                final_columns.append(f"{current_m}|{s}|{i}")

        df = df_raw.iloc[header_idx + 1:].copy()
        df.columns = final_columns
        p_col = [c for c in df.columns if 'Ledger' in c][0]

        # 5. SIDEBAR
        all_months = sorted(list(set([c.split('|')[0] for c in final_columns if '|' in c])))
        m1 = st.sidebar.selectbox("Base Month", all_months, index=0)
        m2 = st.sidebar.selectbox("Current Month", all_months, index=len(all_months)-1)

        # 6. CALCULATE VALUES
        def get_net(m, data):
            relevant = [c for c in data.columns if c.startswith(m)]
            def clean(x):
                s = re.sub(r'[^\d.-]', '', str(x))
                return float(s) if s and s != "." else 0.0
            
            dr = [c for c in relevant if 'debit' in c.lower()]
            cr = [c for c in relevant if 'credit' in c.lower()]
            
            res_dr = data[dr[0]].apply(clean) if dr else 0.0
            res_cr = data[cr[0]].apply(clean) if cr else 0.0
            return res_dr - res_cr

        viz_df = pd.DataFrame({
            'Particulars': df[p_col],
            'Old': get_net(m1, df),
            'New': get_net(m2, df)
        })
        viz_df = viz_df[(viz_df['Old'] != 0) | (viz_df['New'] != 0)]
        viz_df['Variance'] = viz_df['New'] - viz_df['Old']

        # 7. DASHBOARD DISPLAY
        t_o, t_n = viz_df['Old'].sum(), viz_df['New'].sum()
        v_a = t_n - t_o
        
        k1, k2, k3 = st.columns(3)
        k1.metric(m1, f"₹{t_o:,.0f}")
        k2.metric(m2, f"₹{t_n:,.0f}", f"{v_a:,.0f}")
        k3.metric("Change", f"{(v_a/t_o if t_o !=0 else 0):.1%}")

        st.markdown(f"""
        <div class="advice-box">
            <strong>AI Strategy Note:</strong> Net Variance is <b>₹{v_a:,.2f}</b>. 
            The most significant move was in <b>{viz_df.sort_values('Variance', ascending=False).iloc[0]['Particulars']}</b>.
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(viz_df.sort_values('Variance').tail(10), x='Variance', y='Particulars', orientation='h', title="Top 10 Variances")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig_p = px.pie(viz_df[viz_df['New']>0].head(10), values='New', names='Particulars', title="Asset/Expense Mix")
            st.plotly_chart(fig_p, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
