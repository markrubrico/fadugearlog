import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px

# --- CONFIGURATION ---
st.set_page_config(page_title="Badminton Gear Health", layout="wide")

# Sidebar for Pricing Inputs
st.sidebar.header("💰 Pricing & Settings (PHP)")
retire_limit = st.sidebar.number_input("Shoe Retire Limit (Hrs)", value=150)
string_cost = st.sidebar.number_input("Exbolt Stringing Cost", value=470)

# Sidebar: Expandable Shoe Pricing
with st.sidebar.expander("Edit Shoe Prices"):
    shoe_prices = {
        "Eclipsion": st.number_input("Eclipsion", value=7800),
        "Comfort Z": st.number_input("Comfort Z", value=7800),
        "C90NL": st.number_input("C90NL", value=7995),
        "P8500NL": st.number_input("P8500NL", value=7795),
        "P9200TTY": st.number_input("P9200TTY", value=8995),
        "VG2NL": st.number_input("VG2NL", value=7695),
        "VG-DBZ": st.number_input("VG-DBZ", value=6895),
        "P9200III AC": st.number_input("P9200III AC", value=6000),
        "Subaxia": st.number_input("Subaxia", value=9000),
        "A970NL": st.number_input("A970NL", value=7800)
    }

# Main UI
st.title("🏸 Gear Impact & Economic Dashboard")
st.markdown("Analyze gear wear based on intensity and track Cost-Per-Hour in PHP.")

log_input = st.text_area("Paste your Master Log here:", height=250)

if log_input:
    # --- PROCESSING ENGINE ---
    calibration = {"Eclipsion": 110, "SB101CR": 95, "Comfort Z": 53, "C90NL": 17}

    def standardize(name):
        mapping = {'88dpro': '88D Pro', 'c90nl': 'C90NL', 'p8500nl': 'P8500NL',
                   'subaxia': 'Subaxia', 'p9200tty': 'P9200TTY', 'comfort z': 'Comfort Z'}
        return mapping.get(str(name).strip().lower(), str(name).strip())

    data = []
    for line in log_input.strip().split('\n'):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 4: continue
        try:
            date_obj = datetime.strptime(parts[0], "%d-%b-%Y")
            tag = parts[1]
            is_maint = "RE-" in tag.upper()
            
            # Hours Calculation
            hrs_match = re.search(r'(\d+\.?\d*)', parts[2])
            raw_hrs = float(hrs_match.group(1)) if hrs_match else 0.0
            
            # Impact Logic: Training 1.0x, Games 0.4x
            session = parts[3].lower()
            impact_mult = 1.0 if any(x in session for x in ["train", "drill", "feed", "machine"]) else 0.4
            
            r_info = parts[4] if len(parts) > 4 else ""
            r_list = [standardize(r) for r in re.sub(r'\[.*\]|\(.*\)', '', r_info).split('/') if r.strip() and r.strip() != "—"]
            
            data.append({
                "Date": date_obj, "Tag": tag, "Hrs": raw_hrs, 
                "Impact": raw_hrs * impact_mult, "IsMaint": is_maint, "Rackets": r_list
            })
        except: continue

    df = pd.DataFrame(data)

    # --- SHOE STATS ---
    usage = df[~df['IsMaint']].copy()
    usage['Shoe'] = usage['Tag'].apply(standardize)
    shoe_df = usage.groupby('Shoe').agg(Logged=('Hrs', 'sum'), Last_Used=('Date', 'max'))
    shoe_df['Total'] = shoe_df['Logged'] + shoe_df.index.map(calibration).fillna(0)
    shoe_df['CPH'] = (shoe_df.index.map(shoe_prices).fillna(0) / shoe_df['Total']).round(2)
    
    # --- RACKET STATS ---
    exp_usage = usage.explode('Rackets').dropna(subset=['Rackets'])
    exp_maint = df[df['IsMaint']].explode('Rackets').dropna(subset=['Rackets'])
    
    r_sum = []
    for r in sorted(exp_usage['Rackets'].unique()):
        m_r = exp_maint[exp_maint['Rackets'] == r]
        l_s = m_r[m_r['Tag'].str.contains("STRING", case=False)].Date.max()
        l_g = m_r[m_r['Tag'].str.contains("GRIP", case=False)].Date.max()
        
        # Weighted Impact Since Maintenance
        imp_s = exp_usage[(exp_usage['Rackets']==r) & (exp_usage['Date'] > (l_s or datetime(2000,1,1)))].Impact.sum()
        imp_g = exp_usage[(exp_usage['Rackets']==r) & (exp_usage['Date'] > (l_g or datetime(2000,1,1)))].Impact.sum()
        
        r_sum.append({"Racket": r, "String Impact": round(imp_s, 1), "Grip Impact": round(imp_g, 1)})
    
    r_df = pd.DataFrame(r_sum)

    # --- DISPLAY ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👟 Shoe Health")
        # Maintenance Alert for Shoes
        def shoe_style(v):
            return 'color: red; font-weight: bold' if v >= retire_limit else 'color: green'
        
        st.dataframe(shoe_df[['Total', 'CPH']].style.applymap(shoe_style, subset=['Total']))
        
        fig_shoe = px.bar(shoe_df.reset_index(), x='Total', y='Shoe', orientation='h', 
                          range_x=[0, retire_limit + 20], color='Total', 
                          color_continuous_scale='YlOrRd')
        fig_shoe.add_vline(x=retire_limit, line_dash="dash", line_color="red", annotation_text="Retire")
        st.plotly_chart(fig_shoe, use_container_width=True)

    with col2:
        st.subheader("🏸 Racket Health")
        # Maintenance Alert for Rackets
        def racket_style(v):
            return 'background-color: #ffcccc' if v >= 30 else ''
            
        st.dataframe(r_df.style.applymap(racket_style, subset=['String Impact']))
        
        fig_racket = px.bar(r_df, x='Racket', y=['String Impact', 'Grip Impact'], barmode='group')
        st.plotly_chart(fig_racket, use_container_width=True)

    st.success(f"Dashboard Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
else:
    st.warning("Awaiting log input...")