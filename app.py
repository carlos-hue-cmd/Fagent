import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Hybrid Market Pattern Agent", page_icon="📈", layout="wide")

st.subheader("⚡ Watchlist & Rychlý přehled sektoru (4 sloupce)")

# --- SPRÁVA WATCHLISTU V SESSION STATE ---
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = [
        "IBM", "TSMC", "AAPL", "MSFT", 
        "NVDA", "QUBT", "SMCI", "AMD", 
        "GOOGL", "AMZN", "META", "INTC", 
        "QCOM", "AVGO", "ASML", "ARM"
    ]

# Formulář pro přidání nového tickera
with st.expander("➕ Přidat novou firmu do mřížky"):
    with st.form("add_ticker_form", clear_on_submit=True):
        new_ticker = st.text_input("Zadej Ticker (např. NFLX, COIN):").upper().strip()
        submit_add = st.form_submit_button("Přidat do přehledu")
        if submit_add and new_ticker:
            if new_ticker not in st.session_state["watchlist"]:
                st.session_state["watchlist"].append(new_ticker)
                st.success(f"Ticker {new_ticker} byl přidán!")
                st.rerun()
            else:
                st.warning(f"Ticker {new_ticker} už v seznamu je.")

# --- VYKRESLENÍ MŘÍŽKY 4 SLOUPCE ---
num_cols = 4
watchlist = st.session_state["watchlist"]

for i in range(0, len(watchlist), num_cols):
    row_tickers = watchlist[i:i + num_cols]
    cols = st.columns(num_cols)
    
    for j, ticker in enumerate(row_tickers):
        with cols[j]:
            try:
                t_data = yf.Ticker(ticker)
                hist = t_data.history(period="2d")
                info = t_data.info
                
                current_price = info.get("currentPrice") or info.get("regularMarketPrice")
                if not current_price and not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                
                if len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    curr_close = hist['Close'].iloc[-1]
                    change_pct = ((curr_close - prev_close) / prev_close) * 100
                else:
                    change_pct = 0.0
                    
                currency = info.get("currency", "USD")
            except Exception:
                current_price = "N/A"
                change_pct = 0.0
                currency = "USD"

            if isinstance(current_price, (int, float)):
                price_str = f"{current_price:.2f} {currency}"
            else:
                price_str = "N/A"

            if change_pct >= 0:
                bg_color = "rgba(46, 160, 67, 0.12)"
                border_color = "#2ea043"
                text_color = "#3fb950"
                sign = "+"
            else:
                bg_color = "rgba(248, 81, 73, 0.12)"
                border_color = "#f85149"
                text_color = "#f85149"
                sign = ""

            card_html = f"""
            <div style="
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 12px;
                text-align: center;
                margin-bottom: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            ">
                <h4 style="margin: 0; color: inherit;">{ticker}</h4>
                <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.8;">{price_str}</p>
                <h3 style="margin: 6px 0 0 0; color: {text_color};">
                    {sign}{change_pct:.2f}%
                </h3>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            if st.button("❌ Smazat", key=f"del_{ticker}", help=f"Odstranit {ticker} z přehledu"):
                st.session_state["watchlist"].remove(ticker)
                st.rerun()

st.divider()

# --- DETAILNÍ HISTORICKÝ GRAF (VÝCHOZÍ NVDA) ---
st.subheader("📊 Detailní historický graf vybraného titulu")

# Nastavení výchozího indexu na "NVDA", pokud je v seznamu
default_index = 0
if "NVDA" in watchlist:
    default_index = watchlist.index("NVDA")

selected_detail_ticker = st.selectbox("Zvol firmu pro detailní zobrazení grafu:", watchlist, index=default_index)

if selected_detail_ticker:
    detail_hist = yf.Ticker(selected_detail_ticker).history(period="max")
    if not detail_hist.empty:
        fig = px.line(detail_hist, x=detail_hist.index, y='Close', title=f"Vývoj ceny: {selected_detail_ticker}")
        st.plotly_chart(fig, use_container_width=True)
