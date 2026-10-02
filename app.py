import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser
import requests
import json

# --- 1. KONFIGURACE STRÁNKY ---
st.set_page_config(
    page_title="Hybrid Market Pattern Agent", 
    page_icon="📈", 
    layout="wide"
)

st.title("📈 Hybridní Agent: US & Asia Market Intelligence")
st.markdown("Univerzální tržní agent s fixním přehledem sektorových pozic a přímou Gemini AI.")

# --- 2. INICIALIZACE WATCHLISTU A KLÍČE ---
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = [
        "IBM", "TSMC", "AAPL", "MSFT", 
        "NVDA", "QUBT", "SMCI", "AMD", 
        "GOOGL", "AMZN", "META", "INTC", 
        "QCOM", "AVGO", "ASML", "ARM"
    ]

if "messages" not in st.session_state:
    st.session_state.messages = []

if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = ""

# --- 3. SIDEBAR PRO NASTAVENÍ A PŘEPSÁNÍ POZIC ---
st.sidebar.header("⚙️ Konfigurace & Správa pozic")

# Použití 'key' zajistí, že se hodnota v inputu neztratí při přepnutí obrazovki / překreslení
user_key = st.sidebar.text_input(
    "Zadej Gemini API klíč:", 
    type="password", 
    value=st.session_state["gemini_api_key"], 
    key="input_gemini_key",
    help="Získej zdarma na aistudio.google.com"
)

if user_key != st.session_state["gemini_api_key"]:
    st.session_state["gemini_api_key"] = user_key

if st.session_state["gemini_api_key"]:
    st.sidebar.success("Gemini API klíč aktivován! 🚀")
else:
    st.sidebar.warning("API klíč není zadaný. Agent běží v záložním režimu.")

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

# --- 4. FUNKCE PRO STAŽENÍ ŽIVÝCH ZPRÁV ---
def fetch_global_tech_news():
    feeds = {
        "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
        "Seeking Alpha": "https://seekingalpha.com/market_currents.xml",
        "CNBC Markets": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "Reuters Tech": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
        "MarketWatch": "https://www.marketwatch.com/rss/topstories"
    }
    all_articles = []
    for source_name, url in feeds.items():
        try:
            parsed_feed = feedparser.parse(url)
            for entry in parsed_feed.entries[:3]:
                all_articles.append({
                    "source": source_name,
                    "title": entry.get("title", "Bez titulku"),
                    "link": entry.get("link", "#")
                })
        except Exception:
            continue
    return all_articles

# --- 5. SEKCE: RYCHLÝ PŘEHLED SEKTORU (FIXNÍ MŘÍŽKA) ---
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

# --- 6. SEKCE: DETAILNÍ HISTORICKÝ GRAF ---
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

# --- 7. SEKCE: INTELIGENTNÍ CHAT S PŘÍMÝM GEMINI API ---
st.subheader("💬 AI Finanční Agent (Logika & Uvažování)")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Zeptej se na výsledkovou sezónu, odhady zisků, asijské trhy..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    ai_response = None
    active_key = st.session_state.get("gemini_api_key", "")

    if active_key:
        try:
            # Model gemini-3.8-flash s 30s timeoutem pro mobilní sítě
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={active_key}"
            
            system_prompt = (
                f"Jsi špičkový finanční a tržní agent pro US a Asijské trhy, polovodiče a paměti. "
                f"Uživatel má ve svém watchlistu tyto firmy: {watchlist}. "
                "Odpovídej analyticky, s hlubokou znalostí tržních cyklů, odhadů zisků a harmonogramů v češtině."
            )
            
            payload = {
                "contents": [
                    {"parts": [{"text": f"{system_prompt}\n\nDotaz uživatele: {prompt}"}]}
                ]
            }
            
            headers = {"Content-Type": "application/json"}
            res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            
            if res.status_code == 200:
                data = res.json()
                ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                ai_response = f"⚠️ Chyba API (kód {res.status_code}): {res.text}"
        except requests.exceptions.Timeout:
            ai_response = "⚠️ Požadavek vypršel (Timeout). Mobilní síť neodpověděla včas – zkuste to prosím znovu."
        except Exception as e:
            ai_response = f"⚠️ Chyba připojení: {str(e)}"

    # Záložní logika, pokud klíč chybí nebo dojde k výpadku spojení
    if not ai_response:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["výsledk", "sezón", "termín", "říjen", "october", "datum"]):
            ai_response = (
                "📅 **Harmonogram výsledkové sezóny pro technologický sektor (říjen/listopad):**\n\n"
                "1. **US Big Tech & Polovodiče:** Výsledková sezóna za 3. čtvrtletí startuje v polovině října a naplno běží koncem října a v listopadu (Alphabet, Meta, Microsoft, Apple, AMD, Nvidia).\n"
                "2. **Asijský dodavatelský řetězec (TSMC, SK Hynix):** TSMC obvykle publikuje výsledky v polovině října (cca 15.–20. v měsíci).\n\n"
                "💡 *Zadej svůj Gemini API klíč v postranním panelu pro živou AI analýzu.*"
            )
        else:
            ai_response = (
                f"Zaznamenal jsem dotaz: *'{prompt}'*.\n\n"
                "Pro plnohodnotné odpovědi ověř v levém panelu svůj Gemini API klíč."
            )

    with st.chat_message("assistant"):
        st.markdown(ai_response)
        
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()
