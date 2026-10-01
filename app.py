import streamlit as st
import yfinance as yf
import pandas as pd
import os
import google.generativeai as genai

# Nastavení stránky
st.set_page_config(page_title="Yahoo Finance Agent", page_icon="📈", layout="centered")

# Načtení klíče ze Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

st.title("📈 Yahoo Finance Agent s Gemini")
st.markdown("Tvůj osobní mobilní agent pro analýzu akcií, porovnání a AI dotazy.")

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
        news = stock.news
        news_texts = []
        if news:
            for item in news[:5]:
                title = item.get("title")
                publisher = item.get("publisher")
                link = item.get("link")
                news_texts.append(f"- [{title}]({link}) ({publisher})")
                st.markdown(f"- **[{title}]({link})** *({publisher})*")
        else:
            st.info("Žádné zprávy nebyly nalezeny.")

        # AI Chat s ochranou proti halucinacím
        st.divider()
        st.subheader("💬 Zeptej se agenta (Gemini AI)")
        user_query = st.text_input("Zadej dotaz k této firmě (např. 'Shrň poslední zprávy'):")
        
        if user_query:
            if not api_key:
                st.error("Chybí API klíč pro Gemini v nastavení Streamlit Secrets.")
            else:
                with st.spinner("Gemini analyzuje data..."):
                    try:
                        context = f"""
                        Jsi přísný finanční analytik. Tvým úkolem je odpovědět na dotaz uživatele POUZE a JENOM na základě dat uvedených níže. 
                        Pokud odpověď v datech není, napiš: "Tuto informaci v aktuálních datech nemám."
                        Nesmíš si vymýšlet žádná čísla, ceny ani události.

                        DATA PRO AKCII {default_ticker} ({company_name}):
                        - Aktuální cena: {current_price} {currency}
                        - Tržní kapitalizace: {info.get('marketCap', 'N/A')}
                        - P/E ratio: {info.get('trailingPE', 'N/A')}
                        - 52týdenní maximum: {info.get('fiftyTwoWeekHigh', 'N/A')}
                        - 52týdenní minimum: {info.get('fiftyTwoWeekLow', 'N/A')}

                        POSLEDNÍ ZPRÁVY:
                        {chr(10).join(news_texts) if news_texts else 'Žádné zprávy k dispozici'}
                        """
                        
                        model = genai.GenerativeModel('gemini-2.0-flash')
                        response = model.generate_content([
                            context, 
                            f"Dotaz uživatele: {user_query}. Odpověz česky a striktně jen podle výše uvedených dat!"
                        ])
                        
                        st.markdown("### Odpověď agenta:")
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"Chyba při komunikaci s Gemini API: {e}")

    except Exception as e:
        st.error(f"Nepodařilo se načíst data pro ticker {default_ticker}. Chyba: {e}")
