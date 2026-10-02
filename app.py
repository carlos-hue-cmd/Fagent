import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser  # Knihovna pro parsování RSS zpráv

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(
    page_title="Hybrid Market Pattern Agent", 
    page_icon="📈", 
    layout="wide"
)

st.title("📈 Hybridní Agent: US & Asia Market Intelligence")
st.markdown("Univerzální tržní agent s multi-source přehledem zpráv (Nikkei Asia, Seeking Alpha, CNBC, Reuters, MarketWatch, Investing).")

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

# --- FUNKCE PRO STAŽENÍ ŽIVÝCH ZPRÁV VČETNĚ NIKKEI A SEEKING ALPHA ---
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

# --- SEKCE 1: RYCHLÝ PŘEHLED SEKTORU ---
st.subheader("⚡ Watchlist & Rychlý přehled sektoru")

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
            <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <h4 style="margin: 0; color: inherit;">{ticker}</h4>
                <p style="margin: 4px 0 0 0; font-size: 12px; opacity: 0.8;">{price_str}</p>
                <h3 style="margin: 4px 0 0 0; color: {text_color}; font-size: 18px;">
                    {sign}{change_pct:.2f}%
                </h3>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

st.divider()

# --- SEKCE 2: DETAILNÍ HISTORICKÝ GRAF ---
st.subheader("📊 Detailní historický graf vybraného titulu")
default_index = watchlist.index("NVDA") if "NVDA" in watchlist else 0
selected_detail_ticker = st.selectbox("Zvol firmu pro detailní zobrazení grafu:", watchlist, index=default_index)

if selected_detail_ticker:
    detail_hist = yf.Ticker(selected_detail_ticker).history(period="max")
    if not detail_hist.empty:
        fig = px.line(detail_hist, x=detail_hist.index, y='Close', title=f"Vývoj ceny: {selected_detail_ticker}")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- SEKCE 3: CHAT S ASISTENTEM A PLNOU KONTEXTOVOU PAMĚTÍ ---
st.subheader("💬 AI Finanční Agent (Nikkei, Seeking Alpha, CNBC & Paměť)")

# Vykreslení celé historie chatu bez ztráty kontextu
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Zeptej se na asijské trhy, Seeking Alpha, pre-market nebo akcie..."):
    # 1. Přidání zprávy uživatele do historie
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    prompt_lower = prompt.lower()
    
    # 2. Vyhodnocení dotazu
    if any(keyword in prompt_lower for keyword in ["zpráv", "pre-market", "premarket", "cnbc", "nikkei", "seeking alpha", "asij", "prohlášen", "novink", "sektor", "výsled", "trh", "reuters", "bloomberg", "marketwatch"]):
        news_items = fetch_global_tech_news()
        
        if news_items:
            formatted_news = "\n".join([f"- **[{item['source']}]** [{item['title']}]({item['link']})" for item in news_items[:10]])
            ai_response = (
                "🌐 **Global & Asia Market Intelligence:**\n\n"
                "Stáhl jsem nejnovější zprávy z rozšířeného spektra zdrojů (Nikkei Asia, Seeking Alpha, CNBC, Reuters, MarketWatch a další):\n\n"
                f"{formatted_news}\n\n"
                "💡 *Analytický pohled:* Sleduji asijský dodavatelský řetězec i americké předbursní dění. Chceš propojit tyto informace s konkrétním titulem z tvého watchlistu?"
            )
        else:
            ai_response = "⚠️ Externí RSS feedy aktuálně neodpovídají. Zkus dotaz za chvíli zopakovat."
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
            ai_response = f"Zaznamenal jsem: *'{prompt}'*. Navazuji na naši předchozí konverzaci. Pokud chceš rozebrat data z asijských trhů nebo Seeking Alpha, dej mi vědět."

    # 3. Uložení odpovědi asistenta do paměti
    with st.chat_message("assistant"):
        st.markdown(ai_response)
        
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()

# Tlačítko pro kopírování
if st.session_state.messages:
    last_assistant_msg = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    if last_assistant_msg:
        st.markdown("---")
        safe_text = last_assistant_msg.replace("`", "\\`").replace('"', '\\"')
        copy_button_html = f"""
        <button onclick="navigator.clipboard.writeText(`{safe_text}`); alert('Zkopírováno do schránky!');" 
                style="background-color: #ff4b4b; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%;">
            📋 Kopírovat poslední odpověď agenta
        </button>
        """
        st.markdown(copy_button_html, unsafe_allow_html=True)
