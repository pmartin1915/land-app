"""
County-level analysis view for the Streamlit dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from scripts.utils import format_currency, format_score

def county_deep_dive_view(df: pd.DataFrame):
    """
    Renders the county deep dive view.

    Args:
        df: The full DataFrame of property data.
    """
    st.header("County Deep Dive")

    # County Selector
    county_list = sorted(df['county'].unique())
    selected_county = st.selectbox("Select a County", county_list)

    if selected_county:
        county_df = df[df['county'] == selected_county]

        st.subheader(f"Metrics for {selected_county} County")

        # Display aggregate metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Properties", len(county_df))
        with col2:
            st.metric("Average Investment Score", format_score(county_df['investment_score'].mean()))
        with col3:
            st.metric("Average Price/Acre", format_currency(county_df['price_per_acre'].mean()))

        # Display score distributions
        st.subheader("Score Distributions")
        fig = px.histogram(
            county_df,
            x=['county_market_score', 'geographic_score', 'market_timing_score'],
            title=f"Score Distributions for {selected_county}",
            labels={'value': 'Score', 'variable': 'Score Type'},
            barmode='overlay'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Display top 5 properties
        st.subheader(f"Top 5 Properties in {selected_county}")
        top_5_df = county_df.sort_values('investment_score', ascending=False).head(5)
        st.dataframe(top_5_df[['parcel_id', 'amount', 'acreage', 'investment_score']])
