import streamlit as st
import pandas as pd
import altair as alt

# ==============================================================
# Configuration de la page
# ==============================================================
st.set_page_config(page_title="Enquête à chaud — Items", layout="wide")
st.title("📝 Enquête à chaud")



# ==============================================================
# Session state (pour garder les infos entre les écrans)
# ==============================================================
if "meta" not in st.session_state:
    st.session_state.meta = {"num_session": "", "date_session": None, "libelle_session": ""}
if "csv_bytes" not in st.session_state:
    st.session_state.csv_bytes = None
if "csv_name" not in st.session_state:
    st.session_state.csv_name = None
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False

# ==============================================================
# Onglets : Saisie / Rapport
# ==============================================================
tab_saisie, tab_rapport = st.tabs(["🧾 1) Saisie", "📊 2) Rapport"])

# ==============================================================
# ONGLET 1 : SAISIE
# ==============================================================
with tab_saisie:
    st.subheader("🧾 Saisie des informations de la session")

    st.info("""
    Étape 1 : Supprimez les informations des colonnes A et B.  
    Étape 2 : Saisissez les infos de la session   
    Étape 3 : Déposez le fichier CSV  
    Étape 4 : Lancez la génération du rapport  
    Étape 5 : A partir de l'onglet Rapport, vous pouvez imprimer en pdf  
    """)

    with st.form("form_session"):
        num_session = st.text_input("Numéro de session", value=st.session_state.meta["num_session"])
        date_session = st.date_input("Date de la session", value=st.session_state.meta["date_session"])
        libelle_session = st.text_input("Libellé de la session", value=st.session_state.meta["libelle_session"])

        uploaded_file = st.file_uploader(
            "Déposez le fichier CSV (export Evento, séparateur `;`)",
            type=["csv"]
        )

        submitted = st.form_submit_button("✅ Générer le rapport")

    if submitted:
        if not uploaded_file:
            st.error("Merci de déposer le fichier CSV.")
        else:
            # on stocke tout en session_state
            st.session_state.meta = {
                "num_session": num_session.strip(),
                "date_session": date_session,
                "libelle_session": libelle_session.strip(),
            }
            st.session_state.csv_bytes = uploaded_file.getvalue()
            st.session_state.csv_name = uploaded_file.name
            st.session_state.report_ready = True

            st.success("Rapport prêt ✅ Va dans l’onglet « Rapport ».")

# ==============================================================
# ONGLET 2 : RAPPORT
# ==============================================================
with tab_rapport:
    if not st.session_state.report_ready or not st.session_state.csv_bytes:
        st.info("Commence par remplir la saisie et déposer le CSV dans l’onglet « Saisie ».")
        st.stop()

    # ----------------------------------------------------------
    # En-tête rapport (visible pour impression PDF)
    # ----------------------------------------------------------
    meta = st.session_state.meta
   # st.subheader("📌 Informations session (à inclure dans le PDF)")

    colA, colB, colC = st.columns([1, 1, 2])
    with colA:
        st.markdown(f"**Numéro de session :** {meta['num_session'] or '—'}")
    with colB:
        st.markdown(f"**Date :** {meta['date_session'].strftime('%d/%m/%Y') if meta['date_session'] else '—'}")
    with colC:
        st.markdown(f"**Libellé :** {meta['libelle_session'] or '—'}")

    st.caption(f"Fichier : {st.session_state.csv_name}")

    st.divider()

    # ----------------------------------------------------------
    # Lecture CSV (depuis bytes)
    # ----------------------------------------------------------
    csv_bytes = st.session_state.csv_bytes

    # UTF-8 puis fallback latin-1 (accents)
    try:
        df_raw = pd.read_csv(pd.io.common.BytesIO(csv_bytes), sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        df_raw = pd.read_csv(pd.io.common.BytesIO(csv_bytes), sep=";", encoding="latin-1")

    if df_raw.shape[1] <= 2:
        st.error("Le fichier ne semble pas contenir plus de 2 colonnes (A et B).")
        st.stop()

    # ==============================================================
    # Sélection des colonnes C → AZ (indices 2 à 51)
    # ==============================================================
    max_col = min(df_raw.shape[1], 52)
    df = df_raw.iloc[:, 2:max_col].copy()

    #st.write(f"Nombre de lignes dans le fichier : {len(df)}")
    #st.write(f"Nombre de colonnes analysées (C → AZ) : {df.shape[1]}")

    last_row = df.iloc[-1]
    df_without_total = df.iloc[:-1]

    # ==============================================================
    # Préparation des items : base = texte avant le dernier '.'
    # ==============================================================
    items = {}
    for col in df.columns:
        full = str(col)
        if "." in full:
            base, modality = full.rsplit(".", 1)
        else:
            base, modality = full, ""

        base = base.strip()
        modality = modality.strip()

        if base not in items:
            items[base] = {"mod_cols": [], "comment_cols": []}

        if "commentaire" in modality.lower():
            items[base]["comment_cols"].append(col)
        else:
            items[base]["mod_cols"].append((modality, col))

    # ==============================================================
    # Palette satisfaction + ordre dédié
    # ==============================================================
    ordre_satisfaction = ["Très satisfait", "Satisfait", "Peu satisfait", "Pas du tout satisfait"]
    couleurs_satisfaction = {
        "Très satisfait": "#1b7837",
        "Satisfait": "#5aae61",
        "Peu satisfait": "#80cdc1",
        "Pas du tout satisfait": "#f46d43",
    }

    # ==============================================================
    # Affichage des items (camembert + commentaires en 2 colonnes)
    # ==============================================================
    for item_label, info in items.items():
        mod_cols = info["mod_cols"]
        comment_cols = info["comment_cols"]

        if not mod_cols and not comment_cols:
            continue

        chart_df = None
        pie = None
        total = 0

        if mod_cols:
            labels, counts = [], []
            for modality, col in mod_cols:
                labels.append(modality)
                try:
                    val = int(last_row[col])
                except (ValueError, TypeError):
                    val = 0
                counts.append(val)

            total = sum(counts)

            if total > 0:
                percentages = [round(c / total * 100, 1) for c in counts]
                chart_df = pd.DataFrame({"Modalité": labels, "Nombre": counts, "Pourcentage": percentages})

                if set(labels).issubset(set(ordre_satisfaction)):
                    chart_df["Modalité"] = pd.Categorical(
                        chart_df["Modalité"], categories=ordre_satisfaction, ordered=True
                    )
                    chart_df = chart_df.sort_values("Modalité")

                    pie = (
                        alt.Chart(chart_df)
                        .mark_arc(innerRadius=40)
                        .encode(
                            theta="Nombre:Q",
                            color=alt.Color(
                                "Modalité:N",
                                scale=alt.Scale(
                                    domain=ordre_satisfaction,
                                    range=[couleurs_satisfaction[m] for m in ordre_satisfaction],
                                ),
                                legend=alt.Legend(title="Modalité"),
                            ),
                            tooltip=["Modalité", "Nombre", "Pourcentage"],
                        )
                        # ton réglage “prod”
                        .properties(width=400, height=200)
                    )
                else:
                    pie = (
                        alt.Chart(chart_df)
                        .mark_arc(innerRadius=40)
                        .encode(
                            theta="Nombre:Q",
                            color=alt.Color("Modalité:N", legend=alt.Legend(title="Modalité")),
                            tooltip=["Modalité", "Nombre", "Pourcentage"],
                        )
                        .properties(width=400, height=200)
                    )

        commentaires = []
        if comment_cols:
            for col in comment_cols:
                s = df_without_total[col].dropna().astype(str).str.strip()
                s = s[s != ""]
                commentaires.extend(list(s))

        st.markdown(f"## ❓ {item_label}")
        col1, col2 = st.columns([1, 1])

        with col1:
            if mod_cols:
                if total > 0 and pie is not None:
                    st.markdown(f"**{total} réponses**")
                    st.altair_chart(pie, use_container_width=False)
                else:
                    st.info("Aucun total disponible pour calculer les pourcentages.")
            else:
                st.info("Aucune modalité fermée (uniquement commentaire).")

        with col2:
            if mod_cols and chart_df is not None:
                st.markdown("### 📊 Détail des réponses")
                for lab, c, p in zip(chart_df["Modalité"], chart_df["Nombre"], chart_df["Pourcentage"]):
                    st.markdown(f"- **{lab}** : {c} réponses ({p}%)")

            if comment_cols:
                st.markdown("### 💬 Commentaires")
                if not commentaires:
                    st.info("Aucun commentaire.")
                else:
                    for i, txt in enumerate(commentaires, start=1):
                        st.markdown(f"- **Commentaire {i}** : {txt}")

        st.markdown("---")

    # ==============================================================
    # Questions ouvertes finales (BO, BQ, BS)
    # ==============================================================
    st.header("📝 Questions ouvertes finales")

    open_indices = [66, 68, 70]
    ncols = df_raw.shape[1]

    for idx in open_indices:
        if idx >= ncols:
            continue

        col_name = str(df_raw.columns[idx])
        if ".Commentaire" in col_name:
            question_label = col_name.replace(".Commentaire", "").strip()
        else:
            question_label = col_name.split(".")[0].strip()

        st.subheader(f"❓ {question_label}")

        serie = df_raw.iloc[:-1, idx].dropna().astype(str).str.strip()
        serie = serie[serie != ""]

        if serie.empty:
            st.info("Aucune réponse renseignée pour cette question.")
        else:
            for i, txt in enumerate(serie, start=1):
                st.markdown(f"- **Réponse {i}** : {txt}")
