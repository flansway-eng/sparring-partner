import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import datetime

# =========================================================
# 1) CONFIG
# =========================================================
st.set_page_config(page_title="Maeva's Success Partner", page_icon="🚀", layout="centered")
load_dotenv()

MAX_MESSAGES = 20  # ✅ limite d'historique (user+assistant)

# Récupération Clé DeepSeek (local .env)
api_key = os.getenv("DEEPSEEK_API_KEY")

# Fallback si déployé sur Streamlit Cloud (st.secrets)
if not api_key:
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        st.error("❌ Clé DeepSeek introuvable. Vérifie ton .env ou st.secrets.")
        st.stop()

# Connexion au serveur DeepSeek (API compatible OpenAI)
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# =========================================================
# 2) STATE
# =========================================================
if "start_date" not in st.session_state:
    st.session_state.start_date = None

if "messages" not in st.session_state:
    st.session_state.messages = []

def trim_messages():
    """✅ Garde uniquement les MAX_MESSAGES derniers messages dans l'historique."""
    if len(st.session_state.messages) > MAX_MESSAGES:
        st.session_state.messages = st.session_state.messages[-MAX_MESSAGES:]

# =========================================================
# 3) PROGRAMME (séquence fixe J1->J7, boucle jusqu'à J42)
# =========================================================
PROGRAM_SEQUENCE = [
    {"title": "3 États Financiers (Bilan / P&L / Cash)", "focus": "Structure + liens + lecture rapide"},
    {"title": "EBITDA (Calcul & Enjeux)", "focus": "Pont du résultat vers l’EBITDA + normalisations"},
    {"title": "BFR (Working Capital) & Trésorerie", "focus": "Drivers + impacts cash + saisonnalité"},
    {"title": "Dette Nette & Ajustements", "focus": "Net debt bridge + items-like-debt"},
    {"title": "Valorisation (Bridge EV → Equity)", "focus": "EV, net debt, equity value, multiples"},
    {"title": "Analyse de Rapport Annuel", "focus": "Qualité des earnings + risques + KPIs"},
    {"title": "Synthèse + rattrapage + mini-test", "focus": "Consolidation + plan correctif"},
]

DAYS_MAP = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}

def compute_progress(start_date: datetime.date | None, today: datetime.date):
    """
    Retourne un dict:
      - label : "Jx/42 • Semaine y • <jour réel>"
      - day_number : int (J1..)
      - week_num : int
      - real_day_name : str
      - theme : {title, focus}
      - is_finished : bool
      - progress_ratio : float (0..1)
      - progress_text : str
    """
    if not start_date:
        return {
            "label": "En attente...",
            "day_number": None,
            "week_num": None,
            "real_day_name": None,
            "theme": None,
            "is_finished": False,
            "progress_ratio": 0.0,
            "progress_text": "Progression : 0/42",
        }

    delta = (today - start_date).days
    if delta < 0:
        return {
            "label": "En attente...",
            "day_number": None,
            "week_num": None,
            "real_day_name": None,
            "theme": None,
            "is_finished": False,
            "progress_ratio": 0.0,
            "progress_text": "Progression : 0/42",
        }

    day_number = delta + 1  # J1, J2, ...
    real_day_name = DAYS_MAP[today.weekday()]

    # Challenge terminé (J43+)
    if day_number > 42:
        return {
            "label": f"Challenge terminé • J{day_number}/42 • {real_day_name}",
            "day_number": day_number,
            "week_num": 6,
            "real_day_name": real_day_name,
            "theme": {"title": "Bilan final + plan 30 jours", "focus": "forces/faiblesses + next steps"},
            "is_finished": True,
            "progress_ratio": 1.0,
            "progress_text": "Progression : 42/42 (100%)",
        }

    week_num = (day_number - 1) // 7 + 1
    cycle_index = (day_number - 1) % 7
    theme = PROGRAM_SEQUENCE[cycle_index]

    ratio = day_number / 42.0
    pct = int(ratio * 100)

    label = f"J{day_number}/42 • Semaine {week_num} • {real_day_name}"
    return {
        "label": label,
        "day_number": day_number,
        "week_num": week_num,
        "real_day_name": real_day_name,
        "theme": theme,
        "is_finished": False,
        "progress_ratio": ratio,
        "progress_text": f"Progression : {day_number}/42 ({pct}%)",
    }

# =========================================================
# 4) SIDEBAR (planning + reset)
# =========================================================
with st.sidebar:
    st.header("📅 Planning Réel")

    today = datetime.date.today()

    if st.session_state.start_date is None:
        new_date = st.date_input("Date de début du challenge", today)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Valider", use_container_width=True):
                if new_date > today:
                    st.error("❌ La date de début ne peut pas être dans le futur.")
                else:
                    st.session_state.start_date = new_date
                    st.rerun()
        with col2:
            if st.button("Reset chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

    else:
        st.success(f"Début : {st.session_state.start_date}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Changer la date", use_container_width=True):
                st.session_state.start_date = None
                st.rerun()
        with c2:
            if st.button("Reset chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

    st.divider()
    st.caption("🤖 Moteur : DeepSeek-Chat")
    st.caption(f"🧠 Historique : max {MAX_MESSAGES} messages")

# =========================================================
# 5) CALCUL JOUR COURANT + THEME
# =========================================================
progress = compute_progress(st.session_state.start_date, datetime.date.today())
current_label = progress["label"]
theme = progress["theme"]

# =========================================================
# 6) SYSTEM PROMPT (dépend du thème du jour)
# =========================================================
SYSTEM_PROMPT = f"""
Tu es le Mentor M&A de Maeva.
Ton objectif : Transformer Maeva (Juriste) en Analyste TS en 6 semaines (42 jours).
Nous sommes aujourd'hui : **{current_label}**.

### THÈME DU JOUR
- Titre : {theme["title"] if theme else "N/A"}
- Focus : {theme["focus"] if theme else "N/A"}

### RÈGLES D'ACTION (STRICT)
1) Si Maeva dit exactement "Go" (insensible à la casse), tu donnes :
   - Objectif du jour (1 phrase)
   - Puis IMMÉDIATEMENT un exercice technique ou une question piège (sans blabla).
2) Si Maeva ne dit pas "Go", tu poses UNE question courte de diagnostic alignée sur le thème du jour.
3) Si le challenge est terminé, tu fais un bilan final structuré (forces/faiblesses) + plan 30 jours.
4) Style : direct, encourageant, précis. Zéro blabla.
"""

# =========================================================
# 7) UI PRINCIPALE
# =========================================================
st.title("🚀 Maeva's Success Partner")
st.caption(f"Powered by DeepSeek • {current_label}")

# ✅ Progression (barre + texte)
st.progress(progress["progress_ratio"])
st.caption(progress["progress_text"])

if theme:
    st.info(f"🎯 Thème du jour : **{theme['title']}**  \n🧭 Focus : {theme['focus']}")

# Affichage historique (on cache le system)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# =========================================================
# 8) CHAT LOGIC
# =========================================================
user_input = st.chat_input("Tape 'Go' pour lancer ta journée !")

if user_input:
    # 1) Ajout message utilisateur
    st.session_state.messages.append({"role": "user", "content": user_input})
    trim_messages()

    with st.chat_message("user"):
        st.markdown(user_input)

    # 2) Contexte complet : system + historique limité
    # ✅ On envoie uniquement les MAX_MESSAGES derniers messages
    limited_history = st.session_state.messages[-MAX_MESSAGES:]
    full_context = [{"role": "system", "content": SYSTEM_PROMPT}] + limited_history

    with st.spinner("DeepSeek réfléchit..."):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=full_context,
                temperature=0.6
            )

            choices = getattr(response, "choices", None)
            if not choices:
                st.error("❌ Réponse vide du modèle.")
                st.stop()

            ai_response = choices[0].message.content or "❌ Réponse vide."

            # 3) Ajout message assistant
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            trim_messages()

            with st.chat_message("assistant"):
                st.markdown(ai_response)

        except Exception as e:
            st.error(f"Erreur DeepSeek : {e}")
