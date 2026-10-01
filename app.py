import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import feedparser
from groq import Groq

# Nastavení stránky
st.set_page_config(page_title="Hybrid Market Pattern Agent", page_icon="📈", layout="centered")

# Načtení Groq API klíče
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

st.title("📈 Hybridní Agent: US & Asia Market Intelligence")
st.markdown("Sledování trhu, matematické historické paralely a AI chat s filtrací na US/Asijské primární zdroje a wire služby.")

# --- BOČNÍ PANEL PRO VÝBĚR AKTIVA ---
st.sidebar.header("Nastavení sledování")
input_ticker = st.sidebar.text_input("Zadej Ticker firmy (např. AAPL, TSLA, IBM, QUBT, SMCI):", value="IBM").upper().strip()
compare_ticker = st.sidebar.text_input("Srovnání (nepovinné, např. MSFT):", value="").upper().strip()
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
            url = `https://www.google.com/finance/quote/{ticker}:NASDAQ`
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

# Funkce pro získání zpráv přes RSS z primárních zdrojů a odfiltrování evropského šumu
def fetch_filtered_news(ticker):
    news_texts = []
    # Seznam výrazů indikujících evropská periodika nebo lokální média k vyřazení
    excluded_keywords = [
        "euribor", "reuters deutschland", "handelsblatt", "faz", "bloomberg uk", 
        "milan", "frankfurt", "le monde", "corriere", "el país", "der spiegel", 
        "die welt", "gb news", "uk wire", "london stock exchange news (uk)"
    ]
    
    # 1. Yahoo Finance RSS pro daný ticker (obsahuje primárně US wire jako BusinessWire, PR Newswire, Zacks, Motley Fool atd.)
    rss_url = `https://finance.yahoo.com/rss/headline?s={ticker}`
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title = entry.get("title", "")
            # V RSS bývá zdroj často součástí názvu za pomlčkou nebo v autorovi
            source = entry.get("source", {}).get("title", "US/Global Wire")
            
            # Kontrola filtru
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

    # Graf vývoje
    if not hist.empty and 'Close' in hist.columns:
        st.subheader("📊 Historický vývoj a kontext")
        st.line_chart(hist['Close'].tail(500))
    else:
        st.warning("Pro tento ticker nejsou k dispozici detailní historická data v rozvržení časové řady.")

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

    # --- FÁZE 2: PLNOHODNOTNÝ INTERAKTIVNÍ CHAT S AGENTEM ---
    st.divider()
    st.subheader(f"💬 Chat s Finančním Agentem ({input_ticker})")
    
    chat_session_key = f"messages_{input_ticker}"
    if chat_session_key not in st.session_state:
        st.session_state[chat_session_key] = [
            {
                "role": "system",
                "content": f"""Jsi špičkový burzovní analytik a kvantitativní expert zaměřený výhradně na US a asijské trhy (Wall Street, tchajwanské/japonské dodavatelské řetězce, makro data FEDu atd.). 
Pomáháš uživateli sledovat akcii {company_name} ({input_ticker}). 

⚠️ PŘÍSNÉ PRAVIDLO PRO ZDROJE: Zcela ignoruj evropská periodika a média, považuješ je za nedůvěryhodná nebo zpožděná. Opírej se striktně o primární tiskové zprávy firem, US/asijské wire služby (Business Wire, PR Newswire) a oficiální regulatorní hlášení (SEC apod.).

Máš k dispozici tyto aktuální údaje a matematicky spočítané historické paralely za posledních {window_days} dní:
- Aktuální cena: {current_price} {currency}
- P/E ratio: {info.get('trailingPE', 'N/A')}
- 52týdenní maximum: {info.get('fiftyTwoWeekHigh', 'N/A')}
- 52týdenní minimum: {info.get('fiftyTwoWeekLow', 'N/A')}
- Top historické shody zjištěné algoritmem:
{matches_summary}
- Poslední zprávy z ověřených US/asijských RSS wire zdrojů:
{chr(10).join(news_texts) if news_texts else 'Žádné přímé zprávy k dispozici'}

Odpovídej věcně, inteligentně a přirozeně v češtině. Zohledňuj globální průmyslový kontext a chování velkých hráčů v USA a Asii."""
            }
        ]

    for message in st.session_state[chat_session_key][1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_message := st.chat_input("Zeptej se na vývoj, průmyslový kontext, US/asijské vlivy nebo historické paralely..."):
        st.session_state[chat_session_key].append({"role": "user", "content": user_message})
        with st.chat_message("user"):
            st.markdown(user_message)

        if not client:
            st.error("Chybí API klíč pro Groq v nastavení Streamlit Secrets.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("Agent analyzuje US/asijský kontext z primárních zdrojů..."):
                    try:
                        chat_completion = client.chat.completions.create(
                            messages=st.session_state[chat_session_key],
                            model="llama-3.3-70b-versatile",
                        )
                        assistant_response = chat_completion.choices[0].message.content
                        st.markdown(assistant_response)
                        st.session_state[chat_session_key].append({"role": "assistant", "content": assistant_response})
                    except Exception as e:
                        st.error(f"Chyba při komunikaci s Groq API: {e}")
