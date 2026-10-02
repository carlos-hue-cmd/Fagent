# --- 7. SEKCE: INTELIGENTNÍ CHAT S PŘÍMÝM GEMINI API ---
st.subheader("💬 AI Finanční Agent (Logika & Uvažování)")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Zeptej se na výsledkovou sezónu, odhady zisků, asijské trhy..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_history_to_disk(st.session_state.messages)
    
    with st.chat_message("user"):
        st.markdown(prompt)

    ai_response = None
    active_key = st.session_state.get("gemini_api_key", "")

    if active_key:
        # Použijeme stabilnější model gemini-2.5-flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={active_key}"
        
        current_date_str = datetime.now().strftime("%d. %m. %Y")
        
        system_prompt = (
            f"Aktuální datum dnes je: {current_date_str}. "
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
        
        # Pokus o odeslání s jedním opakováním při 503
        import time
        for attempt in range(2):
            try:
                res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
                
                if res.status_code == 200:
                    data = res.json()
                    ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                    break
                elif res.status_code == 503 and attempt == 0:
                    time.sleep(2) # Počkáme 2 sekundy a zkusíme to podruhé
                    continue
                elif res.status_code == 503:
                    ai_response = "⚠️ **Servery Gemini jsou momentálně přetížené (Chyba 503).** Zkuste to prosím za chvíli zopakovat."
                else:
                    ai_response = f"⚠️ Chyba API (kód {res.status_code}): {res.text}"
                    break
            except requests.exceptions.Timeout:
                if attempt == 0:
                    continue
                ai_response = "⚠️ Požadavek vypršel (Timeout). Síť neodpověděla včas."
            except Exception as e:
                ai_response = f"⚠️ Chyba připojení: {str(e)}"
                break

    if not ai_response:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["výsledk", "sezón", "termín", "říjen", "october", "datum"]):
            ai_response = (
                "📅 **Harmonogram výsledkové sezóny pro technologický sektor (říjen/listopad 2026):**\n\n"
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
    save_history_to_disk(st.session_state.messages)
    st.rerun()
