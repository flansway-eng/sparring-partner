import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Maeva's Success Partner", page_icon="🚀", layout="centered")
load_dotenv()

# Récupération Clé DeepSeek
api_key = os.getenv("DEEPSEEK_API_KEY")

# Fallback si déployé sur Streamlit Cloud
if not api_key:
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    except:
        st.error("❌ Clé DeepSeek introuvable. Vérifie ton .env")
        st.stop()

# Connexion au serveur DeepSeek
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"  # Adresse officielle DeepSeek
)

# --- 2. GESTION DU CALENDRIER ---
if "start_date" not in st.session_state:
    st.session_state.start_date = None

with st.sidebar:
    st.header("📅 Planning Réel")
    if st.session_state.start_date is None:
        new_date = st.date_input("Date de début du challenge", datetime.date.today())
        if st.button("Valider"):
            st.session_state.start_date = new_date
            st.rerun()
    else:
        st.success(f"Début : {st.session_state.start_date}")
        if st.button("Changer la date"):
            st.session_state.start_date = None
            st.rerun()
    
    st.divider()
    st.caption("🤖 Moteur : DeepSeek-Chat (V3)")

# Calcul intelligent du jour
current_prog_day = "En attente..."
if st.session_state.start_date:
    today = datetime.date.today()
    start_monday = st.session_state.start_date - datetime.timedelta(days=st.session_state.start_date.weekday())
    days_since_start_monday = (today - start_monday).days
    week_num = (days_since_start_monday // 7) + 1
    weekday_index = today.weekday()
    days_map = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"}
    day_name = days_map.get(weekday_index, "Jour inconnu")
    current_prog_day = f"SEMAINE {week_num} - {day_name}"

# --- 3. LE CERVEAU (SYSTEM PROMPT) ---
SYSTEM_PROMPT = f"""
Tu es le Mentor M&A de Maeva.
Ton objectif : Transformer Maeva (Juriste) en Analyste TS en 6 semaines.
Nous sommes aujourd'hui : **{current_prog_day}**.

### 📅 LE PROGRAMME (RAPPEL)
* **Lundi** : 3 États Financiers (Bilan/P&L/Cash).
* **Mardi** : EBITDA (Calcul & Enjeux).
* **Mercredi** : BFR (Working Capital) & Trésorerie.
* **Jeudi** : Dette Nette & Ajustements.
* **Vendredi** : Valorisation (Bridge EV-Eq).
* **Samedi** : Analyse de Rapport Annuel.

### ACTION
1. Analyse le jour actuel ({current_prog_day}).
2. Si Maeva dit "Go", donne l'objectif du jour et pose IMMÉDIATEMENT une question technique piège ou un exercice.
3. Sois direct, encourageant, et précis.
"""

# --- 4. INTERFACE ---
st.title("🚀 Maeva's Success Partner")
st.caption(f"Powered by DeepSeek • {current_prog_day}")

# Initialisation historique (Format OpenAI standard)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage historique
for msg in st.session_state.messages:
    if msg["role"] != "system": # On cache le prompt système
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 5. LOGIQUE DE CHAT ---
if prompt := st.chat_input("Tape 'Go' pour lancer ta journée !"):
    # 1. Message Utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Préparation du contexte (Système + Historique)
    full_context = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages

    # 3. Appel API DeepSeek
    with st.spinner("DeepSeek réfléchit..."):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat", # Utilise "deepseek-reasoner" si tu veux le modèle R1 (plus lent mais réfléchit plus)
                messages=full_context,
                temperature=1.0 # DeepSeek aime une température un peu plus haute
            )
            
            ai_response = response.choices[0].message.content
            
            # 4. Affichage Réponse
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.markdown(ai_response)
                
        except Exception as e:
            st.error(f"Erreur DeepSeek : {e}")