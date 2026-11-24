from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="From Views to Value", page_icon="📈", layout="wide")

DATA_PATH = Path(__file__).with_name("Instagram_Reach_Cleaned.csv")
GROUPS = ["Q1 · Lowest", "Q2 · Lower middle", "Q3 · Upper middle", "Q4 · Highest"]
METRICS = ["Profile Visits", "Follows", "Total Engagement"]
METRIC_LABELS = {
    "Profile Visits": "Profile visits",
    "Follows": "Follows",
    "Total Engagement": "Engagement actions",
}
ENGAGEMENT = "Engagement Rate (%)"
VISITS = "Profile Visit Rate (%)"


@st.cache_data
def load_posts():
    posts = pd.read_csv(DATA_PATH)
    posts.insert(0, "Post", range(1, len(posts) + 1))
    cutoffs = posts["Impressions"].quantile([0.25, 0.50, 0.75])
    group_index = sum((posts["Impressions"] > cutoff).astype(int) for cutoff in cutoffs)
    posts["Impression group"] = pd.Categorical.from_codes(
        group_index, categories=GROUPS, ordered=True
    )
    return posts


def percent(value):
    return "—" if pd.isna(value) else f"{value:.2f}%"


def style_chart(chart, height=350):
    chart.update_layout(
        height=height,
        margin=dict(l=8, r=18, t=12, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#31483D"),
    )
    chart.update_xaxes(gridcolor="#E5EEE7", zeroline=False)
    chart.update_yaxes(gridcolor="#E5EEE7", zeroline=False)
    return chart


def reset_filters():
    st.session_state.impression_group = "All groups"
    st.session_state.post_search = ""


posts = load_posts()
st.markdown(
    """
    <div style="background:#142e25;color:white;border-radius:20px;padding:2rem 2.35rem;margin-bottom:1.1rem">
      <div style="color:#d9f498;font-size:.75rem;font-weight:750;letter-spacing:.12em">
        INSTAGRAM ANALYTICS · LAMOY SPENCER
      </div>
      <h1 style="color:white;font-size:clamp(2rem,5vw,3.7rem);letter-spacing:-.06em;padding:0;margin:.15em 0">
        From Views to Value
      </h1>
      <p style="color:#d8e5dd;margin:0">See which posts earn attention and which prompt profile visits or follows.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

group_col, search_col, reset_col = st.columns([1.2, 2, 0.8], vertical_alignment="bottom")
group = group_col.selectbox("Impression group", ["All groups", *GROUPS], key="impression_group")
query = search_col.text_input("Caption or hashtag", placeholder="Try #python", key="post_search").strip()
reset_col.button("Reset filters", on_click=reset_filters)

visible = posts
if group != "All groups":
    visible = visible[visible["Impression group"] == group]
if query:
    matches = visible[["Caption", "Hashtags"]].fillna("").agg(" ".join, axis=1)
    visible = visible[matches.str.contains(query, case=False, regex=False)]

st.caption(f"{len(visible):,} of {len(posts):,} posts")
if visible.empty:
    st.info("No posts match these filters. Change your search or reset the filters.")
    st.stop()

cards = st.columns(4)
cards[0].metric("Total impressions", f"{visible['Impressions'].sum():,}", border=True,
                help="Displays across matching posts, including repeat views.")
cards[1].metric("Median engagement rate", percent(visible[ENGAGEMENT].median()), border=True,
                help="Median post rate for likes, comments, shares and saves per 100 impressions.")
cards[2].metric("Median profile visit rate", percent(visible[VISITS].median()), border=True,
                help="Median post rate for profile visits per 100 impressions.")
cards[3].metric("Total follows", f"{visible['Follows'].sum():,}", border=True,
                help="Reported follows across matching posts.")

left, right = st.columns([1.45, 1])
with left.container(border=True):
    st.subheader("Impressions and audience response")
    response = st.selectbox("Audience response", METRICS, format_func=METRIC_LABELS.get)
    st.caption("Hover over a dot to see how an individual post performed.")
    scatter = px.scatter(
        visible, x="Impressions", y=response, color_discrete_sequence=["#287355"],
        labels={**METRIC_LABELS, "Impressions": "Impressions per post"},
        hover_data={"Post": True, "Impression group": True, VISITS: ":.2f"},
    )
    scatter.update_traces(marker=dict(size=10, opacity=0.75, line=dict(width=1, color="white")))
    st.plotly_chart(style_chart(scatter, 318), width="stretch", config={"displayModeBar": False})

with right.container(border=True):
    st.subheader("Profile visit rate by group")
    st.caption("Median post rate · visits per 100 impressions")
    summary = (
        visible.groupby("Impression group", observed=True)[VISITS]
        .agg(rate="median", count="size")
        .reset_index()
    )
    summary["Rate"] = summary["rate"].map(percent)
    bar = px.bar(
        summary, x="rate", y="Impression group", orientation="h", text="Rate",
        color_discrete_sequence=["#40916E"], hover_data={"count": True, "Rate": False},
        labels={"rate": "Median profile visit rate (%)", "count": "Posts", "Impression group": "Group"},
    )
    bar.update_traces(textposition="outside", cliponaxis=False)
    bar.update_yaxes(categoryorder="array", categoryarray=GROUPS[::-1], title=None)
    bar.update_xaxes(ticksuffix="%", range=[0, max(0.1, summary["rate"].max() * 1.27)])
    st.plotly_chart(style_chart(bar), width="stretch", config={"displayModeBar": False})
    st.caption("Group cutoffs use the full dataset and stay fixed as you filter.")

with st.container(border=True):
    st.subheader("What to test next")
    ranked = summary.sort_values("rate", ascending=False)
    top = ranked.iloc[0]
    bottom = ranked.iloc[-1]
    if len(ranked) > 1 and top["rate"] > bottom["rate"]:
        st.write(
            f"**{top['Impression group']}** recorded a median profile visit rate of "
            f"**{top['Rate']}** across {top['count']} matching posts. "
            f"**{bottom['Impression group']}** recorded **{bottom['Rate']}**."
        )
    else:
        st.write(
            f"The matching groups show a median profile visit rate of **{top['Rate']}**."
            if len(ranked) > 1
            else f"**{top['Impression group']}** shows a median profile visit rate of "
                 f"**{top['Rate']}** across {top['count']} matching posts."
        )
    st.write("Sort by profile visit rate and look for a caption or call to action you could test in a future post.")

with st.container(border=True):
    st.subheader("Explore posts")
    sort_by = st.selectbox(
        "Sort by", [VISITS, "Impressions", ENGAGEMENT, "Follows"],
        format_func=lambda metric: metric.replace(" (%)", ""),
    )
    rows = visible.sort_values(sort_by, ascending=False, kind="stable")
    st.dataframe(
        rows[["Caption", "Impressions", ENGAGEMENT, VISITS, "Follows"]],
        hide_index=True, width="stretch",
        column_config={
            "Caption": st.column_config.TextColumn(width="large"),
            ENGAGEMENT: st.column_config.NumberColumn("Engagement rate", format="%.2f%%"),
            VISITS: st.column_config.NumberColumn("Profile visit rate", format="%.2f%%"),
        },
    )

with st.expander("Metric definitions and dataset limits"):
    st.markdown(
        """
        - **Impressions** count displays, including repeat views.
        - **Engagement rate** counts likes, comments, shares and saves per 100 impressions.
        - **Profile visit rate** counts profile visits per 100 impressions.
        - **Follows** count reported follows across posts.

        Profile visits and follows indicate audience interest. The dataset has no sales,
        revenue, or user-level conversion records.
        """
    )
    st.markdown("[Instagram Reach Analysis](https://github.com/iauh23/Instagram-Reach-Analysis) · Assignment 2 cleaned dataset")
