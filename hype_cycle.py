import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from hypecycle import HypeCycle as hc
from notion_client import Client
from dotenv import load_dotenv
import os

load_dotenv()

notion_token = os.getenv("NOTION_TOKEN")
notion_database_id = os.getenv("NOTION_DATABASE_ID")
notion = Client(auth=notion_token)

def get_notion_data(database_id):
    results = notion.databases.query(database_id=database_id).get("results")
    return results

def extract_technologies_data(database_id):
    data = get_notion_data(database_id)
    technologies = []
    for item in data:
        tech_name = item["properties"]["Nom du sujet"]["title"][0]["plain_text"]
        hype_status = item["properties"]["Hype cycle"]["select"]["name"]
        phase_weight = item["properties"]["Poids dans la phase"]["number"]
        selection_hype_cycle = item["properties"]["Sélection Hype cycle"]["checkbox"]
        if selection_hype_cycle:
            technologies.append(
                {
                    "Nom du sujet": tech_name,
                    "Hype cycle": hype_status,
                    "Poids dans la phase": phase_weight,
                }
            )
    return pd.DataFrame(technologies)

def get_max_weights_by_phase(technologies):
    return technologies.groupby("Hype cycle")["Poids dans la phase"].max().to_dict()

def calculate_x_position(hype_status, phase_weight, max_weights):
    max_weight = max_weights[hype_status]
    
    # Define the ranges for each phase
    phase_ranges = {
        "Innovation Trigger": (0, 15),
        "Peak of Inflated Expectations": (15, 25),
        "Trough of Disillusionment": (25, 35),
        "Slope of Enlightenment": (35, 60),
        "Plateau of Productivity": (60, 100),
    }

    phase_start, phase_end = phase_ranges[hype_status]
    # Normalize the phase_weight to the range of the phase based on max_weight
    x_position = phase_start + (phase_end - phase_start) * (phase_weight / max_weight)
    return x_position

def create_hype_cycle_data():
    x = np.linspace(0, 100, 5000)
    y = hc.create(x)
    return pd.DataFrame({"x": x, "y": y})

def draw_hype_cycle(technologies):
    data = create_hype_cycle_data()

    line = (
        alt.Chart(data)
        .mark_line(color="blue")
        .encode(
            x=alt.X("x", title="Time", axis=alt.Axis(labels=False, ticks=True), scale=alt.Scale(domain=[-1, 101])),
            y=alt.Y("y", title="Visibility", axis=alt.Axis(labels=False, ticks=True)),
        )
        .properties(width=1200, height=600)
    )

    vertical_lines = (
        alt.Chart(pd.DataFrame({"x": [15, 25, 35, 60]}))
        .mark_rule(color="grey")
        .encode(x="x")
    )

    max_weights = get_max_weights_by_phase(technologies)

    technologies["x"] = technologies.apply(
        lambda row: calculate_x_position(row["Hype cycle"], row["Poids dans la phase"], max_weights),
        axis=1,
    )
    technologies["y"] = hc.create(technologies["x"])

    # Alterner les positions des étiquettes de texte
    for i in range(len(technologies)):
        if i % 2 == 0:
            technologies.at[i, "text_x"] = technologies.at[i, "x"]
            technologies.at[i, "text_y"] = (
                technologies.at[i, "y"] - (i + 1) * 2
            )  # Ligne vers le haut
        else:
            technologies.at[i, "text_x"] = technologies.at[i, "x"]
            technologies.at[i, "text_y"] = (
                technologies.at[i, "y"] + (i + 1) * 2
            )  # Ligne vers le bas

    tech_points = (
        alt.Chart(technologies)
        .mark_point(size=100)
        .encode(
            x="x",
            y="y",
            tooltip=[
                alt.Tooltip("Nom du sujet", title="Technologies"),
                alt.Tooltip("Hype cycle", title="Hype cycle"),
                alt.Tooltip("Poids dans la phase", title="Poids dans la phase"),
            ],
        )
        .interactive()
    )

    tech_text = (
        alt.Chart(technologies)
        .mark_text(align="center", baseline="middle", color="red")
        .encode(x="text_x", y="text_y", text="Nom du sujet")
    )

    connectors = (
        alt.Chart(technologies)
        .mark_line(color="gray")
        .encode(x="x", x2="text_x", y="y", y2="text_y")
    )

    # Create individual charts for each section label with specific colors
    section_labels = pd.DataFrame(
        {
            "x": [7.5, 20, 30, 48, 80],
            "y": [0, 0, 0, 0, 0],
            "text": [
                "Technology Trigger",
                "Peak of Inflated Expectations",
                "Through of Disillusionment",
                "Slope of Enlightenment",
                "Plateau of Productivity",
            ],
            "color": ["fuchsia", "blueviolet", "green", "darkorange", "brown"],
        }
    )

    label_charts = []
    for i, row in section_labels.iterrows():
        label_chart = alt.Chart(pd.DataFrame({"x": [row["x"]], "text": [row["text"]]})).mark_text(
            baseline="top", dy=20, fontWeight="bold", color=row["color"], fontSize=10
        ).encode(
            x="x:Q",
            y=alt.value(0),
            text="text:N"
        )
        label_charts.append(label_chart)

    section_text = alt.layer(*label_charts)

    chart = alt.layer(
        line, vertical_lines, tech_points, connectors, tech_text, section_text
    ).properties(width=1200, height=600)

    return chart

# Configuration de l'application Streamlit
st.set_page_config(
    page_title="Hype Cycle",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

# Centrer le titre avec du CSS
st.markdown(
    """
    <style>
    .title {
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Titre de l'application
st.markdown('<h1 class="title">Hype Cycle Visualization</h1>', unsafe_allow_html=True)

# Extraction des données de Notion
technologies = extract_technologies_data(notion_database_id)

# Dessiner la courbe Hype Cycle et l'afficher dans Streamlit
chart = draw_hype_cycle(technologies)
st.altair_chart(chart, use_container_width=True)

# Ajouter un bouton pour actualiser la page
st.markdown(
    """
    <style>
    .centered-button {
        display: flex;
        justify-content: center;
        margin-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.button("Actualiser"):
    st.experimental_rerun()
