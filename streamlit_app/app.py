"""
Alabama Auction Watcher - Streamlit Dashboard

Interactive dashboard for browsing and analyzing tax delinquent properties
from the Alabama Department of Revenue.

Usage:
    streamlit run streamlit_app/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import (
    DEFAULT_PRICE_RANGE, DEFAULT_ACREAGE_RANGE, CHART_COLORS,
    CURRENCY_FORMAT, ACREAGE_FORMAT, SCORE_FORMAT
)

from scripts.utils import format_currency, format_acreage, format_score


# Page configuration
st.set_page_config(
    page_title="Alabama Auction Watcher",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding: 0rem 1rem;
    }
    .stAlert {
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .disclaimer-banner {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.25rem;
        padding: 1rem;
        margin-bottom: 1rem;
        color: #856404;
    }
    .data-table {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_watchlist_data(file_path: str) -> pd.DataFrame:
    """
    Load watchlist data with caching.

    Args:
        file_path: Path to the watchlist CSV file

    Returns:
        DataFrame with watchlist data
    """
    try:
        df = pd.read_csv(file_path)

        # Ensure required columns exist with defaults if missing
        required_columns = {
            'rank': 0,
            'parcel_id': 'Unknown',
            'amount': 0.0,
            'acreage': 0.0,
            'price_per_acre': 0.0,
            'water_score': 0.0,
            'investment_score': 0.0,
            'description': 'No description',
            'county': 'Unknown'
        }

        for col, default_value in required_columns.items():
            if col not in df.columns:
                df[col] = default_value

        return df
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


def display_legal_disclaimer():
    """Display the legal disclaimer banner."""
    st.markdown("""
    <div class="disclaimer-banner">
        <h4>⚠️ IMPORTANT LEGAL NOTICE</h4>
        <p><strong>Alabama Redemption Period:</strong> Properties purchased at tax auctions in Alabama are subject to a
        <strong>3-year redemption period</strong> during which the original owner can reclaim the property by paying
        the purchase price plus interest and costs. During this period, you cannot take possession of the property.
        Always consult with a real estate attorney before participating in tax auctions.</p>
    </div>
    """, unsafe_allow_html=True)


def create_sidebar_filters(df: pd.DataFrame) -> Dict:
    """
    Create sidebar filters and return filter values.

    Args:
        df: DataFrame with property data

    Returns:
        Dictionary with filter values
    """
    st.sidebar.header("🔍 Filters")

    filters = {}

    if len(df) > 0:
        # Price range filter
        min_price = float(df['amount'].min()) if 'amount' in df.columns else 0
        max_price = float(df['amount'].max()) if 'amount' in df.columns else DEFAULT_PRICE_RANGE[1]

        filters['price_range'] = st.sidebar.slider(
            "Price Range ($)",
            min_value=min_price,
            max_value=max_price,
            value=(min_price, max_price),
            step=100.0,
            format="$%.0f"
        )

        # Acreage range filter
        min_acres = float(df['acreage'].min()) if 'acreage' in df.columns else DEFAULT_ACREAGE_RANGE[0]
        max_acres = float(df['acreage'].max()) if 'acreage' in df.columns else DEFAULT_ACREAGE_RANGE[1]

        filters['acreage_range'] = st.sidebar.slider(
            "Acreage Range",
            min_value=min_acres,
            max_value=max_acres,
            value=(min_acres, max_acres),
            step=0.1,
            format="%.1f"
        )

        # Water features filter
        filters['water_only'] = st.sidebar.checkbox(
            "Show only properties with water features",
            value=False
        )

        # County filter
        if 'county' in df.columns and df['county'].nunique() > 1:
            counties = ['All'] + sorted(df['county'].dropna().unique().tolist())
            filters['county'] = st.sidebar.selectbox(
                "County",
                options=counties,
                index=0
            )
        else:
            filters['county'] = 'All'

        # Investment score threshold
        if 'investment_score' in df.columns:
            min_score = float(df['investment_score'].min())
            max_score = float(df['investment_score'].max())
            filters['min_investment_score'] = st.sidebar.slider(
                "Minimum Investment Score",
                min_value=min_score,
                max_value=max_score,
                value=min_score,
                step=0.1,
                format="%.1f"
            )

    else:
        # Default filters when no data
        filters = {
            'price_range': DEFAULT_PRICE_RANGE,
            'acreage_range': DEFAULT_ACREAGE_RANGE,
            'water_only': False,
            'county': 'All',
            'min_investment_score': 0.0
        }

    # Add refresh button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.experimental_rerun()

    return filters


def apply_filters(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """
    Apply filters to the DataFrame.

    Args:
        df: Original DataFrame
        filters: Dictionary with filter values

    Returns:
        Filtered DataFrame
    """
    if len(df) == 0:
        return df

    filtered_df = df.copy()

    # Price filter
    if 'amount' in filtered_df.columns:
        price_mask = (
            (filtered_df['amount'] >= filters['price_range'][0]) &
            (filtered_df['amount'] <= filters['price_range'][1])
        )
        filtered_df = filtered_df[price_mask]

    # Acreage filter
    if 'acreage' in filtered_df.columns:
        acreage_mask = (
            (filtered_df['acreage'] >= filters['acreage_range'][0]) &
            (filtered_df['acreage'] <= filters['acreage_range'][1])
        )
        filtered_df = filtered_df[acreage_mask]

    # Water features filter
    if filters['water_only'] and 'water_score' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['water_score'] > 0]

    # County filter
    if filters['county'] != 'All' and 'county' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['county'] == filters['county']]

    # Investment score filter
    if 'min_investment_score' in filters and 'investment_score' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['investment_score'] >= filters['min_investment_score']]

    return filtered_df


def display_summary_metrics(df: pd.DataFrame):
    """
    Display summary metrics cards.

    Args:
        df: Filtered DataFrame
    """
    if len(df) == 0:
        st.warning("No properties match the current filters.")
        return

    st.subheader("📊 Summary Metrics")

    # Create metrics columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Properties",
            value=f"{len(df):,}"
        )

    with col2:
        if 'amount' in df.columns:
            avg_price = df['amount'].mean()
            st.metric(
                label="Average Price",
                value=format_currency(avg_price)
            )

    with col3:
        if 'price_per_acre' in df.columns:
            avg_price_per_acre = df['price_per_acre'].mean()
            st.metric(
                label="Avg Price/Acre",
                value=format_currency(avg_price_per_acre)
            )

    with col4:
        if 'water_score' in df.columns:
            water_count = (df['water_score'] > 0).sum()
            water_percentage = (water_count / len(df)) * 100 if len(df) > 0 else 0
            st.metric(
                label="Water Features",
                value=f"{water_count} ({water_percentage:.1f}%)"
            )

    # Additional metrics row
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        if 'amount' in df.columns:
            total_investment = df['amount'].sum()
            st.metric(
                label="Total Investment",
                value=format_currency(total_investment)
            )

    with col6:
        if 'acreage' in df.columns:
            total_acreage = df['acreage'].sum()
            st.metric(
                label="Total Acreage",
                value=format_acreage(total_acreage)
            )

    with col7:
        if 'investment_score' in df.columns:
            avg_score = df['investment_score'].mean()
            st.metric(
                label="Avg Investment Score",
                value=format_score(avg_score)
            )

    with col8:
        if 'estimated_all_in_cost' in df.columns:
            avg_all_in = df['estimated_all_in_cost'].mean()
            st.metric(
                label="Avg All-in Cost",
                value=format_currency(avg_all_in)
            )


def display_properties_table(df: pd.DataFrame):
    """
    Display the properties data table.

    Args:
        df: Filtered DataFrame
    """
    if len(df) == 0:
        return

    st.subheader("🏘️ Properties")

    # Select columns to display
    display_columns = []
    column_config = {}

    if 'rank' in df.columns:
        display_columns.append('rank')
        column_config['rank'] = st.column_config.NumberColumn(
            "Rank", format="%d", width="small"
        )

    if 'parcel_id' in df.columns:
        display_columns.append('parcel_id')
        column_config['parcel_id'] = st.column_config.TextColumn(
            "Parcel ID", width="medium"
        )

    if 'county' in df.columns:
        display_columns.append('county')
        column_config['county'] = st.column_config.TextColumn(
            "County", width="small"
        )

    if 'amount' in df.columns:
        display_columns.append('amount')
        column_config['amount'] = st.column_config.NumberColumn(
            "Price", format="$%.2f", width="small"
        )

    if 'acreage' in df.columns:
        display_columns.append('acreage')
        column_config['acreage'] = st.column_config.NumberColumn(
            "Acres", format="%.2f", width="small"
        )

    if 'price_per_acre' in df.columns:
        display_columns.append('price_per_acre')
        column_config['price_per_acre'] = st.column_config.NumberColumn(
            "$/Acre", format="$%.2f", width="small"
        )

    if 'water_score' in df.columns:
        display_columns.append('water_score')
        column_config['water_score'] = st.column_config.NumberColumn(
            "Water", format="%.1f", width="small"
        )

    if 'investment_score' in df.columns:
        display_columns.append('investment_score')
        column_config['investment_score'] = st.column_config.NumberColumn(
            "Score", format="%.1f", width="small"
        )

    if 'description' in df.columns:
        display_columns.append('description')
        column_config['description'] = st.column_config.TextColumn(
            "Description", width="large"
        )

    # Display the dataframe
    st.dataframe(
        df[display_columns],
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )

    # Export functionality
    if st.button("📥 Export Current View as CSV"):
        csv_data = df[display_columns].to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="filtered_watchlist.csv",
            mime="text/csv"
        )


def create_visualizations(df: pd.DataFrame):
    """
    Create and display visualizations.

    Args:
        df: Filtered DataFrame
    """
    if len(df) == 0:
        return

    st.subheader("📈 Visualizations")

    # Create two columns for charts
    col1, col2 = st.columns(2)

    with col1:
        # Scatter plot: Price per Acre vs Acreage
        if 'price_per_acre' in df.columns and 'acreage' in df.columns:
            fig_scatter = px.scatter(
                df,
                x='acreage',
                y='price_per_acre',
                color='water_score' if 'water_score' in df.columns else None,
                size='investment_score' if 'investment_score' in df.columns else None,
                hover_data=['parcel_id', 'amount'] if 'parcel_id' in df.columns else None,
                title="Price per Acre vs. Acreage",
                labels={
                    'acreage': 'Acreage',
                    'price_per_acre': 'Price per Acre ($)',
                    'water_score': 'Water Score',
                    'investment_score': 'Investment Score'
                },
                color_continuous_scale='Blues'
            )
            fig_scatter.update_layout(height=400)
            st.plotly_chart(fig_scatter, use_container_width=True)

    with col2:
        # Histogram: Price Distribution
        if 'amount' in df.columns:
            fig_hist = px.histogram(
                df,
                x='amount',
                nbins=20,
                title="Price Distribution",
                labels={'amount': 'Price ($)', 'count': 'Number of Properties'},
                color_discrete_sequence=[CHART_COLORS['primary']]
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True)

    # Second row of visualizations
    col3, col4 = st.columns(2)

    with col3:
        # Bar chart: Properties by County
        if 'county' in df.columns and df['county'].nunique() > 1:
            county_counts = df['county'].value_counts().head(10)
            fig_county = px.bar(
                x=county_counts.index,
                y=county_counts.values,
                title="Properties by County (Top 10)",
                labels={'x': 'County', 'y': 'Number of Properties'},
                color_discrete_sequence=[CHART_COLORS['secondary']]
            )
            fig_county.update_layout(height=400)
            st.plotly_chart(fig_county, use_container_width=True)

    with col4:
        # Box plot: Investment Score Distribution
        if 'investment_score' in df.columns:
            water_label = df['water_score'].apply(lambda x: 'With Water Features' if x > 0 else 'No Water Features') if 'water_score' in df.columns else 'All Properties'

            fig_box = px.box(
                df,
                y='investment_score',
                x=water_label if 'water_score' in df.columns else None,
                title="Investment Score Distribution",
                labels={'investment_score': 'Investment Score'},
                color_discrete_sequence=[CHART_COLORS['water_features'], CHART_COLORS['no_water']]
            )
            fig_box.update_layout(height=400)
            st.plotly_chart(fig_box, use_container_width=True)


def main():
    """Main Streamlit application."""

    # Page title and description
    st.title("🏡 Alabama Auction Watcher")
    st.markdown("**Interactive dashboard for analyzing Alabama tax delinquent property auctions**")

    # Display legal disclaimer
    display_legal_disclaimer()

    # Load data
    watchlist_path = "data/processed/watchlist.csv"
    df = load_watchlist_data(watchlist_path)

    if len(df) == 0:
        st.error(f"""
        **No watchlist data found!**

        To get started:
        1. Download CSV files from [Alabama DOR](https://www.revenue.alabama.gov/property-tax/delinquent-search/)
        2. Place them in the `data/raw/` directory
        3. Run the parser: `python scripts/parser.py --input data/raw/your_file.csv`
        4. Refresh this page

        Expected file location: `{watchlist_path}`
        """)
        st.stop()

    # Create sidebar filters
    filters = create_sidebar_filters(df)

    # Apply filters
    filtered_df = apply_filters(df, filters)

    # Display results
    display_summary_metrics(filtered_df)

    # Add some spacing
    st.markdown("---")

    display_properties_table(filtered_df)

    # Add some spacing
    st.markdown("---")

    create_visualizations(filtered_df)

    # Footer information
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <p>Alabama Auction Watcher • Built with ❤️ for property investors</p>
        <p>⚠️ Always consult with legal and real estate professionals before investing</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()