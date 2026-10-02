# --- SEKCE 3: CHAT S ASISTENTEM A INTELIGENTNÍM VÝTAHEM ZPRÁV ---
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
            # Sestavíme přehledný výtah rozdělený podle zdrojů/témat
            formatted_news = "\n".join([f"- **[{item['source']}]** [{item['title']}]({item['link']})" for item in news_items[:10]])
            
            ai_response = (
                "📋 **Stručný výtah nejnovějších zpráv a tržních pohybů:**\n\n"
                f"{formatted_news}\n\n"
                "📌 **Klíčové závěry pro technologický sektor:**\n"
                "1. **Asijské trhy a dodavatelský řetězec (Nikkei):** Sledují se provozní metriky výrobců čipů a poptávka po polovodičích.\n"
                "2. **US předbursní dění (CNBC / Reuters):** Trh vyhlíží makroekonomická data a výsledkovou sezónu, což drží investory v pozoru ohledně valuací růstových titulů.\n"
                "3. **Hloubkové analýzy (Seeking Alpha):** Pozornost se upírá na kvantitativní odhady zisků v Q4.\n\n"
                "💡 *Chceš některý z těchto bodů rozebrat do hloubky ve vazbě na konkrétní firmu z tvého watchlistu?*"
            )
        else:
            ai_response = "⚠️ Externí RSS feedy aktuálně neodpovídají. Zkus dotaz za chvíli zopakovat."
            
    else:
        # Kontrola, zda uživatel nezabrousil na konkrétní ticker z watchlistu
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
            # Reakce s ohledem na historii, pokud nepadlo specifické klíčové slovo
            ai_response = f"Zaznamenal jsem: *'{prompt}'*. Navazuji na naši předchozí konverzaci. Pokud chceš vytvořit výtah zpráv z asijských trhů či Seeking Alpha, stačí napsat např. *„Udělej výtah zpráv“*."

    # 3. Uložení odpovědi asistenta do paměti
    with st.chat_message("assistant"):
        st.markdown(ai_response)
        
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()

# Tlačítko pro kopírování poslední odpovědi
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
