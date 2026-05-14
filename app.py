from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="SSB Byggeagent", page_icon="🏗️", layout="wide")

st.title("🏗️ SSB Byggeagent")
st.write("Beslutningsstøtte for hvor en utbygger bør bygge bolig basert på SSB-data.")

mode = st.radio(
    "Velg agentmodus:",
    ["Tokenfri regelbasert agent", "Google ADK / Gemini-agent"],
    horizontal=True,
    help="Tokenfri modus bruker ingen LLM. ADK/Gemini bruker én kort LLM-forespørsel per spørsmål.",
)

with st.sidebar:
    st.header("Eksempelspørsmål")
    examples = [
        "Hvor bør jeg bygge bolig?",
        "Hvilken kommune er beste kandidat?",
        "Sammenlign Trondheim, Bærum og Stavanger.",
        "Vurder Lillestrøm.",
    ]
    

    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state["question"] = example

if "question" not in st.session_state:
    st.session_state["question"] = ""

question = st.text_input("Still et spørsmål:", value=st.session_state["question"])

analyze = st.button("Analyser", type="primary")


if analyze:
    with st.spinner("Analyserer SSB-data..."):
        if mode == "Google ADK / Gemini-agent":
            from src.agent import answer_question

            result = answer_question(question)
        else:
            from src.rule_agent import answer_question_rule_based

            result = answer_question_rule_based(question)

    st.markdown(result)
