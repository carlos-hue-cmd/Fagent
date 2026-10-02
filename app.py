import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser
import json

# --- 1. KONFIGURACE STRÁNKY ---
st.set_page_config(
    page_title="Hybrid Market Pattern Agent", 
    page_icon="📈", 
    layout="wide"
)

st.title("📈 Hybridní Agent: US & Asia Market Intelligence")
st.markdown("Univerzální tržní agent s multi-source přehledem zpráv (Nikkei Asia, Seeking Alpha, CNBC, Reuters, MarketWatch, Investing).")

# --- 2. INICIALIZACE HISTORIE A WATCHLISTU ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = [
        "IBM", "TSMC", "AAPL", "MSFT", 
        "NVDA", "QUBT", "SMCI", "AMD", 
        "GOOGL", "AMZN", "META", "INTC", 
        "QCOM", "AVGO", "ASML", "ARM"
    ]

# --- 3. FUNKCE PRO STAŽENÍ ŽIVÝCH ZPRÁV ---
def fetch_global_tech_news():
    """Stahuje aktuální zprávy z RSS feedů globálních finančních a asijských portálů."""
    feeds = {
        "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
        "Seeking Alpha": "https://seekingalpha.com/market_currents.xml",
        "CNBC Markets": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "Reuters Tech": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
        "MarketWatch": "https://www.marketwatch.com/rss/topstories",
        "Investing.com": "https://www.investing.com/rss/news.rss",
        "Yahoo Finance": "https://finance.yahoo.com/news/rssindex"
    }
    
    all_articles = []
    for source_name, url in feeds.items():
        try:
            parsed_feed = feedparser.parse(url)
            for entry in parsed_feed.entries[:3]: # 3 nejnovější z každého zdroje
                all_articles.append({
                    "source": source_name,
                    "title": entry.get("title", "Bez titulku"),
                    "link": entry.get("link", "#")
                })
        except Exception:
            continue
    return all_articles

# --- 4. SEKCE: RYCHLÝ PŘEHLED SEKTORU & SPRÁVA WATCHLISTU ---
st.subheader("⚡ Watchlist & Rychlý přehled sektoru")

with st.expander("➕ Přidat nebo ❌ odebrat firmu z přehledu"):
    col_add, col_rem = st.columns(2)
    
    with col_add:
        with st.form("add_ticker_form", clear_on_submit=True):
            new_ticker = st.text_input("Přidat Ticker (např. NFLX):").upper().strip()
            submit_add = st.form_submit_button("Přidat")
            if submit_add and new_ticker:
                if new_ticker not in st.session_state["watchlist"]:
                    st.session_state["watchlist"].append(new_ticker)
                    st.success(f"Ticker {new_ticker} přidán!")
                    st.rerun()
                else:
                    st.warning(f"Ticker {new_ticker} již existuje.")

    with col_rem:
        with st.form("remove_ticker_form", clear_on_submit=True):
            ticker_to_remove = st.selectbox("Odebrat Ticker:", ["-- Vyber --"] + st.session_state["watchlist"])
            submit_rem = st.form_submit_button("Odebrat vybraný")
            if submit_rem and ticker_to_remove != "-- Vyber --":
                if ticker_to_remove in st.session_state["watchlist"]:
                    st.session_state["watchlist"].remove(ticker_to_remove)
                    st.success(f"Ticker {ticker_to_remove} odebrán!")
                    st.rerun()

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

            # Zmenšená výška karet (kompaktnější padding a menší písma)
            card_html = f"""
            <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 6px 10px; text-align: center; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; font-size: 14px; margin: 0;">{ticker}</span>
                    <span style="color: {text_color}; font-weight: bold; font-size: 13px; margin: 0;">{sign}{change_pct:.2f}%</span>
                </div>
                <div style="font-size: 11px; opacity: 0.75; text-align: left; margin-top: 2px;">{price_str}</div>
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
else:
    st.info("Watchlist je prázdný. Přidejte nějakou firmu nahoře v rozbalovacím menu.")

st.divider()

# --- 6. SEKCE: CHAT S ASISTENTEM A INTELIGENTNÍM VÝTAHEM ---
st.subheader("💬 AI Finanční Agent (Multi-Source Zprávy & Shrnutí)")

# Vykreslení celé historie chatu
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Zeptej se na výtah zpráv, asijské trhy, Seeking Alpha nebo akcie..."):
    # 1. Přidání zprávy uživatele do historie
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    prompt_lower = prompt.lower()
    
    # 2. Inteligentní detekce požadavku na zprávy, výtah nebo shrnutí
    if any(kw in prompt_lower for kw in ["zpráv", "výtah", "shrnutí", "nejdůležitějších", "pre-market", "premarket", "cnbc", "nikkei", "seeking alpha", "asij", "prohlášen", "novink", "sektor", "výsled", "trh", "reuters", "bloomberg", "marketwatch"]):
        news_items = fetch_global_tech_news()
        
        if news_items:
            formatted_news = "\n".join([f"- **[{item['source']}]** [{item['title']}]({item['link']})" for item in news_items[:10]])
            
            ai_response = (
                "📋 **Stručný výtah nejnovějších zpráv a tržních pohybů:**\n\n"
                f"{formatted_news}\n\n"
                "📌 **Klíčové závěry pro technologický sektor:**\n"
                "1. **Asijské trhy a dodavatelský řetězec (Nikkei):** Sledují se provozní metriky výrobců čipů a poptávka po polovodičích.\n"
                "2. **US předbursní dění (CNBC / Reuters):** Trh vyhlíží makroekonomická data a výsledkovou sezónu, což drží investory v pozoru ohledně valuací růstových titulů.\n"
                "3. **Hloubkové analýzy (Seeking Alpha):** Pozornost se upírá na kvantitativní odhady zisků.\n\n"
                "💡 *Chceš některý z těchto bodů rozebrat do hloubky ve vazbě na konkrétní firmu z tvého watchlistu?*"
            )
        else:
            ai_response = "⚠️️ Externí RSS feedy aktuálně neodpovídají. Zkus dotaz za chvíli zopakovat."
    else:
        found_tickers = [t for t in watchlist if t.lower() in prompt_lower]
        if found_tickers:
            response_parts = []
            for t in found_tickers:
                try:
                    t_info = yf.Ticker(t).info
                    p = t_info.get("currentPrice") or t_info.get("regularMarketPrice", "N/A")
                    c = t_info.get("currency", "USD")
                    response_parts.append(f"**{t}**: aktuální cena je {p} {c}.")
                except Exception:
                    response_parts.append(f"**{t}**: data nedostupná.")
            ai_response = f"📋 **Stav vyžádaných titulů:**\n\n" + "\n".join(response_parts)
        else:
            ai_response = f"Zaznamenal jsem: *'{prompt}'*. Navazuji na naši předchozí konverzaci. Pokud chceš vytvořit výtah zpráv z asijských trhů či Seeking Alpha, stačí napsat např. *„Udělej výtah zpráv“*."

    # 3. Uložení odpovědi asistenta do paměti
    with st.chat_message("assistant"):
        st.markdown(ai_response)
        
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()

# --- 7. BEZPEČNÉ TLAČÍTKO PRO KOPÍROVÁNÍ ---
if st.session_state.messages:
    last_assistant_msg = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    if last_assistant_msg:
        st.markdown("---")
        safe_json = json.dumps(last_assistant_msg)
        copy_button_html = f"""
        <button onclick="navigator.clipboard.writeText({safe_json}); alert('Zkopírováno do schránky!');" 
                style="background-color: #ff4b4b; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%;">
            📋 Kopírovat poslední odpověď agenta
        </button>
        """
        st.markdown(copy_button_html, unsafe_allow_html=True)
