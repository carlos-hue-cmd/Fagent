import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import feedparser

# Pokus o import nového Google GenAI SDK
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# --- 1. KONFIGURACE STRÁNKY ---
st.set_page_config(
    page_title="Hybrid Market Pattern Agent", 
    page_icon="📈", 
    layout="wide"
)

st.title("📈 Hybridní Agent: US & Asia Market Intelligence")
st.markdown("Univerzální tržní agent s multi-source přehledem zpráv a inteligentním modulem.")

# --- 2. SIDEBAR PRO NASTAVENÍ API KLÍČE ---
st.sidebar.header("⚙️ Konfigurace agenta")
api_key_input = st.sidebar.text_input("Zadej Gemini API klíč:", type="password", help="Získej zdarma na aistudio.google.com")

if api_key_input:
    st.session_state["gemini_api_key"] = api_key_input
    st.sidebar.success("Gemini API klíč aktivován! 🚀")
else:
    if "gemini_api_key" not in st.session_state:
        st.session_state["gemini_api_key"] = ""

# --- 3. INICIALIZACE HISTORIE A WATCHLISTU ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = [
        "IBM", "TSMC", "AAPL", "MSFT", 
        "NVDA", "QUBT", "SMCI", "AMD", 
        "GOOGL", "AMZN", "META", "INTC", 
        "QCOM", "AVGO", "ASML", "ARM"
    ]

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

# --- 5. SEKCE: RYCHLÝ PŘEHLED SEKTORU & WATCHLIST ---
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
            # Oprava: odstraněn přebytečný tag v řetězci
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

# --- 7. SEKCE: INTELIGENTNÍ CHAT S GEMINI / FALLBACKEM ---
st.subheader("💬 AI Finanční Agent (Logika & Uvažování)")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Zeptej se na odhady zisků, asijské trhy, polovodiče..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    ai_response = None
    active_key = st.session_state.get("gemini_api_key", "")

    # Pokud je k dispozici knihovna a API klíč od uživatele, zapojíme Gemini
    if GENAI_AVAILABLE and active_key:
        try:
            client = genai.Client(api_key=active_key)
            system_instruction = (
                f"Jsi špičkový finanční a tržní agent zaměřený na US a Asijské trhy, polovodiče, čipy a paměti (TSMC, SK Hynix, NVDA atd.). "
                f"Uživatel má ve svém watchlistu tyto firmy: {watchlist}. "
                "Odpovídej analyticky, s hlubokou znalostí tržních cyklů, odhadů zisků a makroekonomických souvislostí v češtině."
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'system_instruction': system_instruction,
                    'temperature': 0.3
                }
            )
            ai_response = response.text
        except Exception as e:
            ai_response = f"⚠️ Chyba při volání Gemini API: {str(e)}"

    # Pokud klíč nebyl zadaný, použijeme chytrou analytickou logiku
    if not ai_response:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["odhad", "zisk", "polovodič", "paměť", "memory", "hynix", "samsung", "tsmc", "cyklus"]):
            ai_response = (
                "📊 **Analytický pohled: Odhady zisků v asijském polovodičovém sektoru & pamětech**\n\n"
                "1. **Struktura poptávky:** Trh zažívá silnou disproporci. Běžná spotřební elektronika stagnuje, zatímco **AI infrastruktura a HBM (High Bandwidth Memory)** generují historicky nejvyšší marže.\n"
                "2. **TSMC a pokročilý fab segment:** Odhady zisků pro nejbližší kvartály zůstávají revidované směrem nahoru díky plnému využití 3nm uzlů a pokročilého balípení (CoWoS).\n"
                "3. **Paměťoví hráči (SK Hynix, Samsung, Micron):** Ceny DRAM a NAND pamětí se stabilizovaly na vyšších úrovních.\n\n"
                "💡 *Tip: V levém bočním panelu (sidebaru) můžeš zadat svůj **Gemini API klíč** a agent se rázem přepne na plný výkon živé AI s pokročilým uvažováním!*"
            )
        elif any(w in prompt_lower for w in ["zpráv", "výtah", "shrnutí", "novink", "trh", "pre-market"]):
            news_items = fetch_global_tech_news()
            if news_items:
                formatted_news = "\n".join([f"- **[{item['source']}]** [{item['title']}]({item['link']})" for item in news_items[:8]])
                ai_response = f"📋 **Aktuální přehled zpráv:**\n\n{formatted_news}"
            else:
                ai_response = "⚠️ Zprávy se nepodařilo načíst."
        else:
            found_tickers = [t for t in watchlist if t.lower() in prompt_lower]
            if found_tickers:
                parts = []
                for t in found_tickers:
                    try:
                        info = yf.Ticker(t).info
                        p = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
                        c = info.get("currency", "USD")
                        pe = info.get("trailingPE", "N/A")
                        parts.append(f"**{t}**: Cena: {p} {c} | P/E: {pe}")
                    except Exception:
                        parts.append(f"**{t}**: Data nedostupná.")
                ai_response = "📈 **Analýza vyžádaných titulů z watchlistu:**\n\n" + "\n".join(parts)
            else:
                ai_response = (
                    f"Zaznamenal jsem tvůj dotaz: *'{prompt}'*.\n\n"
                    "Pro plné zapojení AI logiky zadej svůj **Gemini API klíč** vlevo v postranním panelu. "
                    "Jinak se spoléhám na vestavěný analytický přehled pro čipy, asijské trhy a odhady zisků."
                )

    with st.chat_message("assistant"):
        st.markdown(ai_response)
        
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()
