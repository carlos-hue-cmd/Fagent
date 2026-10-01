import streamlit as st
import yfinance as yf
import pandas as pd
import os
from groq import Groq

# Nastavení stránky
st.set_page_config(page_title="Yahoo Finance Agent", page_icon="📈", layout="centered")

# Načtení Groq API klíče ze Streamlit Secrets
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

st.title("📈 Yahoo Finance Agent s Groq (Llama 3)")
st.markdown("Tvůj osobní mobilní agent pro analýzu akcií, porovnání a AI dotazy bez limitů.")

# Boční panel
st.sidebar.header("Nastavení")
default_ticker = st.sidebar.text_input("Hlavní ticker firmy", value="IBM").upper()
compare_ticker = st.sidebar.text_input("Ticker pro porovnání (nepovinné)", value="AAPL").upper()

if default_ticker:
    try:
        stock = yf.Ticker(default_ticker)
        info = stock.info
        
        company_name = info.get("longName", default_ticker)
        currency = info.get("currency", "USD")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
        
        st.header(f"{company_name} ({default_ticker})")
        
        # Metriky
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Aktuální cena", f"{current_price} {currency}")
        with col2:
            market_cap = info.get('marketCap')
            st.metric("Tržní kapitalizace", f"{market_cap:,}" if market_cap else "N/A")
        with col3:
            st.metric("P/E Ratio", info.get("trailingPE", "N/A"))

        # Graf
        st.subheader("📊 Vývoj ceny za 1 rok")
        hist = stock.history(period="1y")
        if not hist.empty:
            st.line_chart(hist['Close'])
        else:
            st.warning("Data pro graf nejsou k dispozici.")

        # Porovnání
        if compare_ticker:
            st.subheader(f"⚖️ Srovnání: {default_ticker} vs {compare_ticker}")
            comp_stock = yf.Ticker(compare_ticker)
            comp_info = comp_stock.info
            
            comparison_data = {
                "Metrika": ["Firma", "Cena", "Tržní kapitalizace", "P/E Ratio", "52T Maximum", "52T Minimum"],
                default_ticker: [
                    company_name,
                    f"{current_price} {currency}",
                    f"{info.get('marketCap', 0):,}" if info.get('marketCap') else "N/A",
                    info.get("trailingPE", "N/A"),
                    info.get("fiftyTwoWeekHigh", "N/A"),
                    info.get("fiftyTwoWeekLow", "N/A")
                ],
                compare_ticker: [
                    comp_info.get("longName", compare_ticker),
                    f"{comp_info.get('currentPrice') or comp_info.get('regularMarketPrice', 'N/A')} {comp_info.get('currency', 'USD')}",
                    f"{comp_info.get('marketCap', 0):,}" if comp_info.get('marketCap') else "N/A",
                    comp_info.get("trailingPE", "N/A"),
                    comp_info.get("fiftyTwoWeekHigh", "N/A"),
                    comp_info.get("fiftyTwoWeekLow", "N/A")
                ]
            }
            df_comp = pd.DataFrame(comparison_data)
            st.table(df_comp.set_index("Metrika"))

        # Zprávy
        st.subheader("📰 Poslední zprávy")
        news_texts = []
        try:
            news = stock.news
            if news:
                for item in news[:5]:
                    title = item.get("title") or item.get("content", {}).get("title")
                    publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName")
                    link = item.get("link") or item.get("content", {}).get("clickThroughUrl", {}).get("url")
                    
                    if title:
                        news_texts.append(f"- {title} ({publisher})")
                        if link:
                            st.markdown(f"- **[{title}]({link})** *({publisher})*")
                        else:
                            st.markdown(f"- **{title}** *({publisher})*")
            if not news_texts:
                st.info("Yahoo Finance aktuálně neposkytuje pro tento ticker žádné zprávy.")
        except Exception:
            st.info("Zprávy se nepodařilo načíst.")

        # AI Chat s Groq (Llama 3) a ochranou proti halucinacím
        st.divider()
        st.subheader("💬 Zeptej se agenta (Llama 3)")
        user_query = st.text_input("Zadej dotaz k této firmě (např. 'Zhodnoť aktuální metriky'):")
        
        if user_query:
            if not client:
                st.error("Chybí API klíč pro Groq v nastavení Streamlit Secrets.")
            else:
                with st.spinner("Groq analyzuje data..."):
                    try:
                        system_prompt = f"""
                        Jsi přísný finanční analytik. Tvým úkolem je odpovědět na dotaz uživatele POUZE a JENOM na základě dat uvedených níže. 
                        Pokud odpověď v datech není, napiš: "Tuto informaci v aktuálních datech nemám."
                        Nesmíš si vymýšlet žádná čísla, ceny ani události. Odpovídej v češtině.

                        DATA PRO AKCII {default_ticker} ({company_name}):
                        - Aktuální cena: {current_price} {currency}
                        - Tržní kapitalizace: {info.get('marketCap', 'N/A')}
                        - P/E ratio: {info.get('trailingPE', 'N/A')}
                        - 52týdenní maximum: {info.get('fiftyTwoWeekHigh', 'N/A')}
                        - 52týdenní minimum: {info.get('fiftyTwoWeekLow', 'N/A')}

                        POSLEDNÍ ZPRÁVY:
                        {chr(10).join(news_texts) if news_texts else 'Žádné zprávy k dispozici'}
                        """
                        
                        chat_completion = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_query}
                            ],
                            model="llama-3.3-70b-versatile", # Velmi schopný a rychlý model na Groqu
                        )
                        
                        st.markdown("### Odpověď agenta:")
                        st.write(chat_completion.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Chyba při komunikaci s Groq API: {e}")

    except Exception as e:
        st.error(f"Nepodařilo se načíst data pro ticker {default_ticker}. Chyba: {e}")
