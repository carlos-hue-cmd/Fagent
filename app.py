import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import json
import feedparser
from groq import Groq
import plotly.express as px

# Nastavení stránky
st.set_page_config(page_title="Hybrid Market Pattern Agent", page_icon="📈", layout="centered")

# Načtení Groq API klíče
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

st.title("📈 Hybridní Agent: US & Asia Market Intelligence")
st.markdown("Univerzální tržní agent, interaktivní Plotly grafy a vytrvalá AI paměť.")

# --- PERSISTENTNÍ PAMĚŤ ---
MEMORY_FILE = "agent_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_memory(memory_data):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

if "app_memory" not in st.session_state:
    st.session_state["app_memory"] = load_memory()

# --- BOČNÍ PANEL PRO VÝBĚR AKTIVA ---
st.sidebar.header("Nastavení sledování")
input_ticker = st.sidebar.text_input("Zadej Ticker firmy (např. AAPL, TSLA, IBM, QUBT, SMCI):", value="IBM").upper().strip()
window_days = st.sidebar.slider("Délka srovnávaného okna (dny)", min_value=15, max_value=60, value=30)

# Funkce pro stažení dat s podporou Google Finance fallbacku
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker):
    history_df = pd.DataFrame()
    info = {}
    source_used = "Yahoo Finance"
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        history_df = stock.history(period="max")
        
        if history_df.empty or 'Close' not in history_df.columns:
            raise ValueError("Yahoo Finance vrátilo prázdná data.")
            
    except Exception as e:
        source_used = "Google Finance (Fallback)"
        try:
            url = f"https://www.google.com/finance/quote/{ticker}:NASDAQ"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                price_div = soup.find(attrs={"jsname": "vWLAgc"})
                if price_div:
                    raw_price = price_div.text.replace(',', '').replace('$', '')
                    current_p = float(raw_price)
                    info = {
                        "longName": ticker,
                        "currency": "USD",
                        "currentPrice": current_p,
                        "regularMarketPrice": current_p,
                        "trailingPE": "N/A",
                        "fiftyTwoWeekHigh": "N/A",
                        "fiftyTwoWeekLow": "N/A"
                    }
        except Exception:
            pass
            
    return history_df, info, source_used

def fetch_filtered_news(ticker):
    news_texts = []
    excluded_keywords = [
        "euribor", "reuters deutschland", "handelsblatt", "faz", "bloomberg uk", 
        "milan", "frankfurt", "le monde", "corriere", "el país", "der spiegel", 
        "die welt", "gb news", "uk wire", "london stock exchange news (uk)"
    ]
    
    rss_url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title = entry.get("title", "")
            source = entry.get("source", {}).get("title", "US/Global Wire")
            
            combined_text = (title + " " + source).lower()
            if any(ex in combined_text for ex in excluded_keywords):
                continue
                
            news_texts.append(f"- {title} ({source})")
            if len(news_texts) >= 6:
                break
    except Exception:
        pass
        
    return news_texts

if input_ticker:
    with st.spinner(f"Stahuji tržní data a primární zprávy pro {input_ticker}..."):
        hist, info, data_source = fetch_stock_data(input_ticker)
        news_texts = fetch_filtered_news(input_ticker)
    
    company_name = info.get("longName", input_ticker)
    currency = info.get("currency", "USD")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice", info.get("previousClose", "N/A"))
    
    st.header(f"{company_name} ({input_ticker})")
    st.caption(f"Zdroj dat: **{data_source}** | Zprávy: **Filtrované US & Asijské primární RSS wire služby**")
    
    # Metriky
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Aktuální cena", f"{current_price} {currency}" if isinstance(current_price, (int, float)) else current_price)
    with col2:
        st.metric("52T Maximum", info.get("fiftyTwoWeekHigh", "N/A"))
    with col3:
        st.metric("P/E Ratio", info.get("trailingPE", "N/A"))

    # --- INTERAKTIVNÍ GRAF PŘES PLOTLY (S JEDNOCENÝM TOOLTIPEM) ---
    if not hist.empty and 'Close' in hist.columns:
        st.subheader("📊 Interaktivní historický graf")
        
        plot_df = hist['Close'].reset_index()
        
        # Ošetření časové zóny sloupcového indexu
        date_col = plot_df.columns[0]
        if plot_df[date_col].dt.tz is not None:
            plot_df[date_col] = plot_df[date_col].dt.tz_localize(None)
            
        max_dt = plot_df[date_col].max()
        
        time_frame = st.selectbox(
            "Zvol rozsah zobrazení grafu:",
            [
                "Poslední den",
                "Poslední týden",
                "Poslední 1 měsíc",
                "Poslední 3 měsíce",
                "Poslední rok (1Y)",
                "Posledních 5 let (5Y)",
                "Maximální historie"
            ],
            index=2
        )
        
        if time_frame == "Poslední den":
            plot_df = plot_df[plot_df[date_col] >= (max_dt - pd.Timedelta(days=1))]
        elif time_frame == "Poslední týden":
            plot_df = plot_df[plot_df[date_col] >= (max_dt - pd.Timedelta(days=7))]
        elif time_frame == "Poslední 1 měsíc":
            plot_df = plot_df[plot_df[date_col] >= (max_dt - pd.Timedelta(days=30))]
        elif time_frame == "Poslední 3 měsíce":
            plot_df = plot_df[plot_df[date_col] >= (max_dt - pd.Timedelta(days=90))]
        elif time_frame == "Poslední rok (1Y)":
            plot_df = plot_df[plot_df[date_col] >= (max_dt - pd.Timedelta(days=365))]
        elif time_frame == "Posledních 5 let (5Y)":
            plot_df = plot_df[plot_df[date_col] >= (max_dt - pd.Timedelta(days=1825))]
            
        fig = px.line(plot_df, x=date_col, y='Close')
        fig.update_traces(hovertemplate='<b>Datum</b>: %{x|%Y-%m-%d}<br><b>Cena</b>: %{y:.2f} ' + currency)
        fig.update_layout(
            xaxis_title="Datum", 
            yaxis_title=f"Cena ({currency})", 
            hovermode="x unified",
            margin=dict(l=10, r=10, t=10, b=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Pro tento ticker nejsou k dispozici detailní historická data.")

    # --- FÁZE 1: MATEMATICKÉ VYHLEDÁNÍ SHODY V PYTHONU ---
    def find_historical_matches(df, win_size):
        if df.empty or len(df) < win_size * 2 or 'Close' not in df.columns:
            return []
        
        recent = df['Close'].iloc[-win_size:]
        recent_norm = (recent / recent.iloc[0]) - 1
        
        historical_data = df['Close'].iloc[:-win_size]
        correlations = []
        
        for i in range(len(historical_data) - win_size):
            window = historical_data.iloc[i:i+win_size]
            window_norm = (window / window.iloc[0]) - 1
            
            corr = recent_norm.corr(window_norm)
            if not pd.isna(corr):
                start_date = window.index[0].strftime('%Y-%m-%d')
                end_date = window.index[-1].strftime('%Y-%m-%d')
                
                future_window = df['Close'].iloc[i+win_size : i+win_size+win_size]
                future_return = ((future_window.iloc[-1] / future_window.iloc[0]) - 1) * 100 if not future_window.empty else 0.0
                
                correlations.append({
                    "start": start_date,
                    "end": end_date,
                    "corr": corr,
                    "future_return": future_return
                })
        
        correlations = sorted(correlations, key=lambda x: x['corr'], reverse=True)
        
        top_matches = []
        for m in correlations:
            if not any(abs(pd.to_datetime(m['start']).timestamp() - pd.to_datetime(existing['start']).timestamp()) < win_size * 86400 for existing in top_matches):
                top_matches.append(m)
                if len(top_matches) >= 3:
                    break
        return top_matches

    matches_summary = "Zatím nebyly spočítány historické korelace."
    if not hist.empty and len(hist) >= window_days * 2:
        matches = find_historical_matches(hist, window_days)
        if matches:
            matches_summary = ""
            for idx, match in enumerate(matches, 1):
                direction = "růst" if match['future_return'] > 0 else "pokles"
                matches_summary += f"{idx}. Období {match['start']} až {match['end']} (korelace: {match['corr']:.2f}) -> Následný vývoj v dalším období: {direction} o {match['future_return']:.2f}%\n"

    # --- FÁZE 2: STANDARDNÍ NATIVNÍ STREAMLIT CHAT ---
    st.divider()
    st.subheader("💬 AI Finanční Agent (Globální kontext & Live Data)")
    
    chat_session_key = "global_agent_chat"
    
    live_context_prompt = f"""Jsi špičkový burzovní analytik a kvantitativní expert zaměřený výhradně na US a asijské trhy (Wall Street, tchajwanské/japonské dodavatelské řetězce, makro data FEDu, korporátní earnings atd.). 
Uživatel s tebou mluví napříč trhy. Máš přímý přístup k živým tržním datům z Yahoo/Google Finance a primárním wire službám.

PRÁVĚ SLEDOVANÝ TICKER V APLIKACI (pro okamžitý kontext, pokud se uživatel zeptá):
- Ticker: {input_ticker} ({company_name})
- Aktuální cena: {current_price} {currency}
- P/E ratio: {info.get('trailingPE', 'N/A')}
- 52týdenní maximum: {info.get('fiftyTwoWeekHigh', 'N/A')}
- 52týdenní minimum: {info.get('fiftyTwoWeekLow', 'N/A')}
- Poslední zprávy z ověřených US/asijských RSS wire zdrojů:
{chr(10).join(news_texts) if news_texts else 'Žádné přímé zprávy k dispozici'}

⚠️ PŘÍSNÉ PRAVIDLO PRO ZDROJE: Zcela ignoruj evropská periodika a média, považuješ je za nedůvěryhodná nebo zpožděná. Opírej se striktně o primární tiskové zprávy firem, US/asijské wire služby (Business Wire, PR Newswire) a oficiální regulatorní hlášení (SEC apod.).

Odpovídej věcně, inteligentně a přirozeně v češtině. Zohledňuj globální průmyslový kontext a chování velkých hráčů v USA a Asii."""

    if chat_session_key not in st.session_state:
        if chat_session_key in st.session_state["app_memory"]:
            st.session_state[chat_session_key] = st.session_state["app_memory"][chat_session_key]
            st.session_state[chat_session_key][0]["content"] = live_context_prompt
        else:
            st.session_state[chat_session_key] = [
                {
                    "role": "system",
                    "content": live_context_prompt
                }
            ]
    else:
        st.session_state[chat_session_key][0]["content"] = live_context_prompt

    # Vykreslení historie chatu
    for message in st.session_state[chat_session_key][1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Nativní chat input
    if user_message := st.chat_input("Zeptej se na cokoliv z US/asijských trhů, earnings, trendů nebo paralel..."):
        st.session_state[chat_session_key].append({"role": "user", "content": user_message})
        with st.chat_message("user"):
            st.markdown(user_message)

        if not client:
            st.error("Chybí API klíč pro Groq v nastavení Streamlit Secrets.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("Agent analyzuje živá data a tržní kontext..."):
                    try:
                        chat_completion = client.chat.completions.create(
                            messages=st.session_state[chat_session_key],
                            model="openai/gpt-oss-20b",
                        )
                        assistant_response = chat_completion.choices[0].message.content
                        st.markdown(assistant_response)
                        
                        st.session_state[chat_session_key].append({"role": "assistant", "content": assistant_response})
                        
                        st.session_state["app_memory"][chat_session_key] = st.session_state[chat_session_key]
                        save_memory(st.session_state["app_memory"])
                        
                    except Exception as e:
                        st.error(f"Chyba při komunikaci s Groq API: {e}")
