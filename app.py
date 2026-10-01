import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from groq import Groq

# Nastavení stránky
st.set_page_config(page_title="Hybrid Market Pattern Agent", page_icon="📈", layout="centered")

# Načtení Groq API klíče
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

st.title("📈 Hybridní Agent: Yahoo & Google Finance + AI")
st.markdown("Matematické vyhledávání historických shod, duální zdroj dat a expertní vyhodnocení přes Groq.")

# Boční panel
st.sidebar.header("Nastavení analýzy")
default_ticker = st.sidebar.text_input("Sledovaný Ticker (např. IBM, AAPL)", value="IBM").upper()
compare_ticker = st.sidebar.text_input("Srovnání (nepovinné)", value="AAPL").upper()
window_days = st.sidebar.slider("Délka srovnávaného okna (dny)", min_value=15, max_value=60, value=30)

# Funkce pro stažení dat s podporou Google Finance fallbacku
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker):
    history_df = pd.DataFrame()
    info = {}
    source_used = "Yahoo Finance"
    
    # Pokus 1: Yahoo Finance
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        history_df = stock.history(period="max")
        
        # Pokud yfinance vrátí prázdno, vyvoláme výjimku pro přechod na fallback
        if history_df.empty or 'Close' not in history_df.columns:
            raise ValueError("Yahoo Finance vrátilo prázdná data.")
            
    except Exception as e:
        # Pokus 2: Fallback na Google Finance (získání aktuální ceny a základu přes scraping)
        source_used = "Google Finance (Fallback)"
        try:
            url = f"https://www.google.com/finance/quote/{ticker}:NASDAQ" # případně NYSE, zkusíme obecně
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Hledání aktuální ceny v Google Finance struktuře
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
                    # Vytvoříme alespoň simulovaný/základní DataFrame, pokud chybí hluboká historie
                    # Pozn.: Google Finance nemá jednoduše přístupnou celou matici historie přes prostý GET, 
                    # proto pro hlubokou historii doporučujeme Yahoo, ale aspoň nezůstaneme zcela bez dat.
        except Exception as google_err:
            pass
            
    return history_df, info, source_used

if default_ticker:
    with st.spinner("Stahuji tržní data..."):
        hist, info, data_source = fetch_stock_data(default_ticker)
    
    company_name = info.get("longName", default_ticker)
    currency = info.get("currency", "USD")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice", info.get("previousClose", "N/A"))
    
    st.header(f"{company_name} ({default_ticker})")
    st.caption(f"Zdroj dat: **{data_source}**")
    
    # Metriky
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Aktuální cena", f"{current_price} {currency}" if isinstance(current_price, (int, float)) else current_price)
    with col2:
        st.metric("52T Maximum", info.get("fiftyTwoWeekHigh", "N/A"))
    with col3:
        st.metric("P/E Ratio", info.get("trailingPE", "N/A"))

    # Graf vývoje (pokud máme historická data)
    if not hist.empty and 'Close' in hist.columns:
        st.subheader("📊 Historický vývoj a kontext")
        st.line_chart(hist['Close'].tail(500))
    else:
        st.warning("Pro tento ticker nejsou k dispozici detailní historická data v rozvržení časové řady.")

    # Zprávy / Sentiment (pokud jsou k dispozici přes yfinance)
    news_texts = []
    try:
        stock_obj = yf.Ticker(default_ticker)
        news = stock_obj.news
        if news:
            for item in news[:5]:
                title = item.get("title") or item.get("content", {}).get("title")
                publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName")
                if title:
                    news_texts.append(f"- {title} ({publisher})")
    except Exception:
        pass

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

    st.divider()
    st.subheader("🔍 Hybridní analýza tržních vzorců")
    
    if st.button("Spustit hledání a AI vyhodnocení"):
        if not client:
            st.error("Chybí API klíč pro Groq v nastavení Streamlit Secrets.")
        elif hist.empty or len(hist) < window_days * 2:
            st.error("Nedostatek historických dat pro matematický výpočet korelací.")
        else:
            with st.spinner("Fáze 1: Python prohledává historická data a počítá korelace..."):
                matches = find_historical_matches(hist, window_days)
            
            if not matches:
                st.warning("Nepodařilo se nalézt dostatečné historické shody.")
            else:
                st.success("Matematické shody úspěšně spočítány. Předávám modelům Groq (Llama 3.3)...")
                
                matches_summary = ""
                for idx, match in enumerate(matches, 1):
                    direction = "růst" if match['future_return'] > 0 else "pokles"
                    matches_summary += f"{idx}. Období {match['start']} až {match['end']} (korelace: {match['corr']:.2f}) -> Následný vývoj v dalším období: {direction} o {match['future_return']:.2f}%\n"

                with st.spinner("Fáze 2: Groq (Llama 3.3 70B) analyzuje kontext a tvoří predikci..."):
                    try:
                        system_prompt = "Jsi expert na burzovní analýzu a behaviorální finance. Tvým úkolem je porovnat aktuální tržní situaci s historickými analogy, které ti dodal systém, zohlednit aktuální zprávy a určit pravděpodobný scénář vývoje. Odpovídej věcně a strukturovaně v češtině."
                        
                        user_prompt = f"""
                        Aktuální ticker: {company_name} ({default_ticker})
                        - Aktuální cena: {current_price} {currency}
                        - P/E ratio: {info.get('trailingPE', 'N/A')}
                        
                        Top 3 historické shody vypočítané algoritmicky z cenového vývoje za posledních {window_days} dní:
                        {matches_summary}
                        
                        Aktuální zprávy / sentiment na trhu:
                        {chr(10).join(news_texts) if news_texts else 'Žádné specifické zprávy'}
                        
                        Úkol: Zanalizuj tyto 3 historické scénáře v kontextu aktuálních metrik a zpráv. Vyhodnoť, ke kterému z těchto historických scénářů má akcie dnes nejblíže a jaký pravděpodobný směr vývoje to indikuje.
                        """
                        
                        chat_completion = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            model="llama-3.3-70b-versatile",
                        )
                        
                        st.markdown("### Výsledek hybridní analýzy:")
                        st.write(chat_completion.choices[0].message.content)
                        
                    except Exception as e:
                        st.error(f"Chyba při komunikaci s Groq API: {e}")
