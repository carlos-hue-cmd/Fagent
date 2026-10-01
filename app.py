import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(
    page_title="Hybrid Market Pattern Agent", 
    page_icon="📈", 
    layout="wide"
)

st.title("📈 Hybridní Agent: US & Asia Market Intelligence")
st.markdown("Univerzální tržní agent, interaktivní mřížka sektoru a vytrvalá AI paměť.")

# --- INICIALIZACE HISTORIE CHATU A WATCHLISTU ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = [
        "IBM", "TSMC", "AAPL", "MSFT", 
        "NVDA", "QUBT", "SMCI", "AMD", 
        "GOOGL", "AMZN", "META", "INTC", 
        "QCOM", "AVGO", "ASML", "ARM"
    ]

# --- SEKCE 1: RYCHLÝ PŘEHLED SEKTORU (HTML/CSS FLEXBOX MŘÍŽKA - GARANTOVANÉ 4 SLOUPCE) ---
st.subheader("⚡ Watchlist & Rychlý přehled sektoru")

# Formulář pro přidání nové firmy
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

# Vykreslení mřížky pomocí HTML/CSS
watchlist = st.session_state["watchlist"]

# CSS pro flexbox kontejner a jednotlivé karty
# flex-basis: 22% znamená, že každá karta zabere přibližně 22% šířky kontejneru (+ mezery), takže se vejdou 4 na řádek.
grid_style = """
<style>
.flex-grid-container {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: flex-start;
    margin-bottom: 20px;
}

.flex-grid-card {
    flex: 0 0 calc(25% - 8px); /* Přesně čtvrtina šířky mínus mezera */
    border-radius: 8px;
    padding: 10px;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    box-sizing: border-box;
}

/* Responzivita: Na tabletech 3 na řádek */
@media (max-width: 992px) {
    .flex-grid-card { flex: 0 0 calc(33.33% - 8px); }
}

/* Responzivita: Na mobilech 2 na řádek */
@media (max-width: 576px) {
    .flex-grid-card { flex: 0 0 calc(50% - 8px); }
}
</style>
"""

# Začátek HTML gridu
cards_html = "<div class='flex-grid-container'>"

# Generování obsahu karet
for ticker in watchlist:
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

    # Barvy podle plusu / mínusu
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

    # Jedna karta v HTML
    cards_html += f"""
    <div class='flex-grid-card' style="background-color: {bg_color}; border: 1px solid {border_color};">
        <h4 style="margin: 0; color: inherit;">{ticker}</h4>
        <p style="margin: 4px 0 0 0; font-size: 12px; opacity: 0.8;">{price_str}</p>
        <h3 style="margin: 4px 0 0 0; color: {text_color}; font-size: 18px;">
            {sign}{change_pct:.2f}%
        </h3>
        
        {st.button("❌", key=f"del_{ticker}", help=f"Smazat {ticker}", type="primary")}
    </div>
    """

cards_html += "</div>"

# Vykreslení stylů a gridu
st.markdown(grid_style + cards_html, unsafe_allow_html=True)

st.divider()

# --- SEKCE 2: DETAILNÍ HISTORICKÝ GRAF (VÝCHOZÍ NVDA) ---
st.subheader("📊 Detailní historický graf vybraného titulu")

default_index = 0
if "NVDA" in watchlist:
    default_index = watchlist.index("NVDA")

selected_detail_ticker = st.selectbox("Zvol firmu pro detailní zobrazení grafu:", watchlist, index=default_index)

if selected_detail_ticker:
    detail_hist = yf.Ticker(selected_detail_ticker).history(period="max")
    if not detail_hist.empty:
        fig = px.line(detail_hist, x=detail_hist.index, y='Close', title=f"Vývoj ceny: {selected_detail_ticker}")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- SEKCE 3: CHAT S ASISTENTEM A TLAČÍTKO KOPÍROVAT ---
st.subheader("💬 AI Finanční Agent (Globální kontext & Live Data)")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Zeptej se na trhy, akcie nebo anomálie..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    ai_response = f"Zpracovávám požadavek k tématu: **{prompt}**. Sleduji aktuální data z yfinance pro váš watchlist."
    
    with st.chat_message("assistant"):
        st.markdown(ai_response)
        
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()

if st.session_state.messages:
    last_assistant_msg = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    if last_assistant_msg:
        st.markdown("---")
        safe_text = last_assistant_msg.replace("`", "\\`").replace('"', '\\"')
        copy_button_html = f"""
        <button onclick="navigator.clipboard.writeText(`{safe_text}`); alert('Poslední odpověď byla zkopírována do schránky!');" 
                style="background-color: #ff4b4b; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%;">
            📋 Kopírovat poslední odpověď agenta
        </button>
        """
        st.markdown(copy_button_html, unsafe_allow_html=True)
