import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser
import requests
import json
import os
import time
from datetime import datetime

# --- SOUBORY PRO TRVALÉ ULOŽENÍ ---
CONFIG_FILE = "mistral_api_key_config.json"
HISTORY_FILE = "chat_history_mistral.json"

def load_saved_key():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("api_key", "")
        except Exception:
            return ""
    return ""

def save_key_to_disk(key):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": key}, f)
    except Exception:
        pass

def load_saved_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history_to_disk(messages):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# --- 1. KONFIGURACE STRÁNKY & VLASTNÍ CSS PRO ZVĚTŠENÍ ČATU A PÍSMA ---
st.set_page_config(
    page_title="Hybrid Market Pattern Agent (Mistral)", 
    page_icon="🤖", 
    layout="wide"
)

st.markdown("""
<style>
    /* Zvětšení písma a prostoru v chatových zprávách */
    .stChatMessage {
        font-size: 17px !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    /* Zvětšení vstupního pole pro chat (promptu) */
    .stChatInput textarea {
        font-size: 16px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Hybridní Agent: US & Asia Market Intelligence (Mistral AI)")
st.markdown("Univerzální tržní agent s fixním přehledem sektorových pozic poháněný modely od Mistral AI.")

# --- 2. INICIALIZACE WATCHLISTU, KLÍČE A HISTORIE ---
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = [
        "IBM", "TSMC", "AAPL", "MSFT", 
        "NVDA", "QUBT", "SMCI", "AMD", 
        "GOOGL", "AMZN", "META", "INTC", 
        "QCOM", "AVGO", "ASML", "ARM"
    ]

# Načtení trvale uložené historie chatu z disku
if "messages" not in st.session_state:
    st.session_state.messages = load_saved_history()

if "mistral_api_key" not in st.session_state:
    st.session_state["mistral_api_key"] = load_saved_key()

# --- 3. SIDEBAR PRO NASTAVENÍ A PŘEPSÁNÍ POZIC ---
st.sidebar.header("⚙️ Konfigurace & Správa pozic")

user_key = st.sidebar.text_input(
    "Zadej Mistral API klíč:", 
    type="password", 
    value=st.session_state["mistral_api_key"], 
    key="input_mistral_key",
    help="Získej na console.mistral.ai"
)

if user_key != st.session_state["mistral_api_key"]:
    st.session_state["mistral_api_key"] = user_key
    save_key_to_disk(user_key)

if st.session_state["mistral_api_key"]:
    st.sidebar.success("Mistral API klíč aktivován a uložen! 🚀")
else:
    st.sidebar.warning("API klíč není zadaný. Agent běží v záložním režimu.")

# Tlačítko pro vymazání historie
if st.sidebar.button("🗑️ Vymazat historii chatu"):
    st.session_state.messages = []
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("🔄 Úprava pozic ve mřížce")
with st.sidebar.form("replace_ticker_form"):
    target_pos = st.selectbox("Vyber pozici k přepsání:", st.session_state["watchlist"])
    new_replacement = st.text_input("Napsat nový Ticker (např. NFLX):").upper().strip()
    submit_replace = st.form_submit_button("Zaměnit firmu")
    
    if submit_replace and new_replacement:
        if target_pos in st.session_state["watchlist"]:
            idx = st.session_state["watchlist"].index(target_pos)
            st.session_state["watchlist"][idx] = new_replacement
            st.sidebar.success(f"Pozice {target_pos} úspěšně přepsána na {new_replacement}!")
            st.rerun()

# --- 4. SEKCE: RYCHLÝ PŘEHLED SEKTORU (FIXNÍ MŘÍŽKA) ---
st.subheader("⚡ Watchlist & Rychlý přehled sektoru (Fixní mřížka)")

watchlist = st.session_state["watchlist"]
cols_per_row = 4

for i in range(0, len(watchlist), cols_per_row):
    row_tickers = watchlist[i:i + cols_per_row]
    cols = st.columns(cols_per_row)
    
    for idx, ticker in enumerate(row_tickers):
        with cols[idx]:
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

            price_str = f"{current_price:.2f} {currency}" if isinstance(current_price, (int, float)) else "N/A"
            
            if change_pct >= 0:
                bg_color, border_color, text_color, sign = "rgba(46, 160, 67, 0.12)", "#2ea043", "#3fb950", "+"
            else:
                bg_color, border_color, text_color, sign = "rgba(248, 81, 73, 0.12)", "#f85149", "#f85149", ""

            card_html = f"""
            <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 8px 10px; text-align: center; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                    <span style="font-weight: bold; font-size: 13px;">{ticker}</span>
                    <span style="color: {text_color}; font-weight: bold; font-size: 12px;">{sign}{change_pct:.2f}%</span>
                </div>
                <div style="font-size: 15px; font-weight: bold; margin-top: 2px;">{price_str}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

st.divider()

# --- 5. SEKCE: DETAILNÍ HISTORICKÝ GRAF ---
st.subheader("📊 Detailní historický graf vybraného titulu")
default_index = watchlist.index("NVDA") if "NVDA" in watchlist else (0 if watchlist else None)
if default_index is not None and watchlist:
    selected_detail_ticker = st.selectbox("Zvol firmu pro detailní zobrazení grafu:", watchlist, index=default_index)

    if selected_detail_ticker:
        detail_hist = yf.Ticker(selected_detail_ticker).history(period="max")
        if not detail_hist.empty:
            fig = px.line(detail_hist, x=detail_hist.index, y='Close', title=f"Vývoj ceny: {selected_detail_ticker}")
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 6. SEKCE: INTELIGENTNÍ CHAT S MISTRAL API ---
st.subheader("💬 AI Finanční Agent (Mistral API)")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Zeptej se na výsledkovou sezónu, odhady zisků, asijské trhy..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_history_to_disk(st.session_state.messages)
    
    with st.chat_message("user"):
        st.markdown(prompt)

    ai_response = None
    active_key = st.session_state.get("mistral_api_key", "")

    if active_key:
        url = "https://api.mistral.ai/v1/chat/completions"
        
        current_date_str = datetime.now().strftime("%d. %m. %Y")
        
        system_prompt = (
            f"Aktuální datum dnes je: {current_date_str}. "
            f"Jsi špičkový finanční a tržní agent pro US a Asijské trhy, polovodiče a paměti. "
            f"Uživatel má ve svém watchlistu tyto firmy: {watchlist}. "
            "Odpovídej analyticky, s hlubokou znalostí tržních cyklů, odhadů zisků a harmonogramů v češtině."
        )
        
        payload = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {active_key}"
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            if res.status_code == 200:
                data = res.json()
                ai_response = data["choices"][0]["message"]["content"]
            else:
                ai_response = f"⚠️ Chyba Mistral API (kód {res.status_code}): {res.text}"
        except Exception as e:
            ai_response = f"⚠️ Chyba připojení k Mistralu: {str(e)}"

    if not ai_response:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["výsledk", "sezón", "termín", "říjen", "october", "datum"]):
            ai_response = (
                "📅 **Harmonogram výsledkové sezóny pro technologický sektor (říjen/listopad 2026):**\n\n"
                "1. **US Big Tech & Polovodiče:** Výsledková sezóna za 3. čtvrtletí startuje v polovině října a naplno běží koncem října a v listopadu (Alphabet, Meta, Microsoft, Apple, AMD, Nvidia).\n"
                "2. **Asijský dodavatelský řetězec (TSMC, SK Hynix):** TSMC obvykle publikuje výsledky v polovině října (cca 15.–20. v měsíci).\n\n"
                "💡 *Zadej svůj Mistral API klíč v postranním panelu pro živou AI analýzu.*"
            )
        else:
            ai_response = (
                f"Zaznamenal jsem dotaz: *'{prompt}'*.\n\n"
                "Pro plnohodnotné odpovědi ověř v levém panelu svůj Mistral API klíč."
            )

    with st.chat_message("assistant"):
        st.markdown(ai_response)
        
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    save_history_to_disk(st.session_state.messages)
    st.rerun()
