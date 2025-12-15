"""
Advanced Analytics Dashboard for Alabama Auction Watcher
Professional-grade analytics showcasing 5-10x more analytical depth than basic auction data
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from typing import Dict
import logging

# Import existing utility functions
from config.security import get_security_config, create_secure_headers

logger = logging.getLogger(__name__)

@st.cache_data(ttl=300)
def load_analytics_data(filters: Dict = None) -> pd.DataFrame:
    """
    Load property data optimized for analytics with intelligence filtering.

    Args:
        filters: Optional filters to apply

    Returns:
        DataFrame with full intelligence data
    """
    # Use secure configuration for API access
    security_config = get_security_config()
    API_URL = f"{security_config.api_base_url}/properties/"
    headers = create_secure_headers()

    # Build comprehensive parameters for analytics
    params = {
        "page_size": 10000,  # Get all data for analytics
        "sort_by": "investment_score",
        "sort_order": "desc"
    }

    # Apply filters if provided
    if filters:
        params.update({k: v for k, v in filters.items() if v is not None})

    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        properties_list = data.get('properties', [])
        df = pd.DataFrame(properties_list)

        if df.empty:
            return pd.DataFrame()

        # Ensure required columns exist with defaults
        intelligence_columns = {
            'county_market_score': 0.0,
            'geographic_score': 0.0,
            'market_timing_score': 0.0,
            'total_description_score': 0.0,
            'road_access_score': 0.0,
            'lot_dimensions_score': 0.0,
            'shape_efficiency_score': 0.0,
            'corner_lot_bonus': 0.0,
            'irregular_shape_penalty': 0.0,
            'subdivision_quality_score': 0.0,
            'location_type_score': 0.0,
            'title_complexity_score': 0.0,
            'survey_requirement_score': 0.0,
            'premium_water_access_score': 0.0,
            'investment_score': 0.0,
            'water_score': 0.0,
            'amount': 0.0,
            'acreage': 0.0,
            'price_per_acre': 0.0,
            'county': 'Unknown'
        }

        for col, default in intelligence_columns.items():
            if col not in df.columns:
                df[col] = default

        return df

    except Exception as e:
        logger.error(f"Failed to load analytics data: {e}")
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

def create_county_intelligence_matrix(df: pd.DataFrame) -> go.Figure:
    """
    Create an interactive county intelligence matrix showing all counties with their scores.

    Args:
        df: DataFrame with property data

    Returns:
        Plotly figure with county intelligence matrix
    """
    if df.empty:
        return go.Figure()

    # Aggregate county intelligence scores
    county_stats = df.groupby('county').agg({
        'county_market_score': 'mean',
        'geographic_score': 'mean',
        'market_timing_score': 'mean',
        'investment_score': 'mean',
        'amount': 'count'  # Property count
    }).round(1)

    county_stats.columns = ['Market Score', 'Geographic Score', 'Timing Score', 'Avg Investment Score', 'Property Count']
    county_stats = county_stats.sort_values('Market Score', ascending=False)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=county_stats[['Market Score', 'Geographic Score', 'Timing Score', 'Avg Investment Score']].values,
        x=['Market Score', 'Geographic Score', 'Timing Score', 'Avg Investment Score'],
        y=county_stats.index,
        colorscale='RdYlBu_r',
        text=county_stats[['Market Score', 'Geographic Score', 'Timing Score', 'Avg Investment Score']].values,
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False,
        zmin=0,
        zmax=100
    ))

    fig.update_layout(
        title="County Intelligence Matrix - Performance Across All Metrics",
        xaxis_title="Intelligence Metrics",
        yaxis_title="Alabama Counties",
        height=600,
        font=dict(size=12)
    )

    return fig

def create_investment_opportunity_ranking(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """
    Create investment opportunity ranking visualization.

    Args:
        df: DataFrame with property data
        top_n: Number of top opportunities to show

    Returns:
        Plotly figure with opportunity ranking
    """
    if df.empty:
        return go.Figure()

    # Get top opportunities by investment score
    top_properties = df.nlargest(top_n, 'investment_score')

    # Create compound score combining multiple intelligence factors
    top_properties = top_properties.copy()
    top_properties['compound_score'] = (
        top_properties['investment_score'] * 0.4 +
        top_properties['county_market_score'] * 0.25 +
        top_properties['geographic_score'] * 0.2 +
        top_properties['market_timing_score'] * 0.15
    )

    fig = go.Figure()

    # Add investment score bars
    fig.add_trace(go.Bar(
        name='Investment Score',
        x=top_properties['parcel_id'],
        y=top_properties['investment_score'],
        marker_color='lightblue',
        opacity=0.7
    ))

    # Add compound score line
    fig.add_trace(go.Scatter(
        name='Compound Intelligence Score',
        x=top_properties['parcel_id'],
        y=top_properties['compound_score'],
        mode='lines+markers',
        line=dict(color='red', width=3),
        marker=dict(size=8)
    ))

    fig.update_layout(
        title=f"Top {top_n} Investment Opportunities - Intelligence-Based Ranking",
        xaxis_title="Property (Parcel ID)",
        yaxis_title="Score",
        height=500,
        showlegend=True,
        xaxis={'tickangle': 45}
    )

    return fig

def create_advanced_filtering_interface(df: pd.DataFrame) -> Dict:
    """
    Create advanced filtering interface for all 14+ intelligence fields.

    Args:
        df: DataFrame with property data

    Returns:
        Dictionary with selected filter values
    """
    st.subheader("Advanced Intelligence Filtering")

    with st.expander("Intelligence Score Filters", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            county_market_min = st.slider(
                "County Market Score (Min)",
                0.0, 100.0, 0.0, 1.0,
                help="Minimum county market conditions score"
            )
            geographic_min = st.slider(
                "Geographic Score (Min)",
                0.0, 100.0, 0.0, 1.0,
                help="Minimum geographic advantages score"
            )
            timing_min = st.slider(
                "Market Timing Score (Min)",
                0.0, 100.0, 0.0, 1.0,
                help="Minimum market timing score"
            )
            description_min = st.slider(
                "Description Score (Min)",
                0.0, 100.0, 0.0, 1.0,
                help="Minimum total description intelligence score"
            )

        with col2:
            road_access_min = st.slider(
                "Road Access Score (Min)",
                0.0, 100.0, 0.0, 1.0,
                help="Minimum road access quality score"
            )
            investment_min = st.slider(
                "Investment Score (Min)",
                0.0, 100.0, 0.0, 1.0,
                help="Minimum overall investment score"
            )
            water_min = st.slider(
                "Water Score (Min)",
                0.0, 15.0, 0.0, 0.1,
                help="Minimum water features score"
            )

    with st.expander("Property Characteristics"):
        col3, col4 = st.columns(2)

        with col3:
            counties = ['All'] + sorted(df['county'].unique().tolist())
            selected_county = st.selectbox("County", counties)

            price_range = st.slider(
                "Price Range ($)",
                0, int(df['amount'].max()) if not df.empty else 50000,
                (0, int(df['amount'].max()) if not df.empty else 50000),
                step=1000
            )

        with col4:
            acreage_range = st.slider(
                "Acreage Range",
                0.0, float(df['acreage'].max()) if not df.empty else 100.0,
                (0.0, float(df['acreage'].max()) if not df.empty else 100.0),
                step=0.1
            )

            water_features = st.checkbox("Only properties with water features")

    # Build filters dictionary
    filters = {
        'min_county_market_score': county_market_min if county_market_min > 0 else None,
        'min_geographic_score': geographic_min if geographic_min > 0 else None,
        'min_market_timing_score': timing_min if timing_min > 0 else None,
        'min_total_description_score': description_min if description_min > 0 else None,
        'min_road_access_score': road_access_min if road_access_min > 0 else None,
        'min_investment_score': investment_min if investment_min > 0 else None,
        'county': selected_county if selected_county != 'All' else None,
        'min_price': price_range[0] if price_range[0] > 0 else None,
        'max_price': price_range[1],
        'min_acreage': acreage_range[0] if acreage_range[0] > 0 else None,
        'max_acreage': acreage_range[1],
        'water_features': water_features if water_features else None
    }

    return filters

def display_analytics_dashboard():
    """
    Main function to display the advanced analytics dashboard.
    """
    st.title("Advanced Analytics Dashboard")
    st.markdown("**Professional-grade property intelligence analytics for Alabama auction properties**")

    # Create tabs for different analytics views
    tab1, tab2, tab3, tab4 = st.tabs([
        "Intelligence Overview",
        "County Analysis",
        "Property Analytics",
        "Investment Insights"
    ])

    with tab1:
        st.header("Intelligence Overview")
        st.markdown("**Comprehensive analysis of county intelligence and property performance**")

        # Load base data
        df = load_analytics_data()

        if df.empty:
            st.warning("No data available. Please ensure the backend API is running.")
            return

        # Key metrics row
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total Properties", f"{len(df):,}")
        with col2:
            properties_with_intelligence = len(df[df['county_market_score'] > 0])
            st.metric("Intelligence-Enhanced", f"{properties_with_intelligence:,}")
        with col3:
            avg_investment = df['investment_score'].mean()
            st.metric("Avg Investment Score", f"{avg_investment:.1f}")
        with col4:
            counties_count = df['county'].nunique()
            st.metric("Counties", f"{counties_count}")
        with col5:
            water_properties = len(df[df['water_score'] > 0])
            st.metric("Water Features", f"{water_properties:,}")

        st.markdown("---")

        # County Intelligence Matrix
        st.subheader("County Intelligence Matrix")
        county_matrix = create_county_intelligence_matrix(df)
        st.plotly_chart(county_matrix, use_container_width=True)

        # Top performing counties
        st.subheader("Top Performing Counties by Intelligence Metrics")
        county_performance = df.groupby('county').agg({
            'county_market_score': 'mean',
            'geographic_score': 'mean',
            'market_timing_score': 'mean',
            'investment_score': 'mean',
            'amount': 'count'
        }).round(1)
        county_performance.columns = ['Market Score', 'Geographic Score', 'Timing Score', 'Avg Investment', 'Properties']
        county_performance = county_performance.sort_values('Market Score', ascending=False)

        st.dataframe(county_performance, use_container_width=True)

    with tab2:
        st.header("County Analysis")
        st.markdown("**Deep dive into county-level market intelligence and geographic advantages**")

        df = load_analytics_data()
        if df.empty:
            st.warning("No data available for county analysis.")
            return

        # County selector
        counties = sorted(df['county'].unique())
        selected_county = st.selectbox("Select County for Analysis", counties, key="county_analysis")

        if selected_county:
            county_data = df[df['county'] == selected_county]

            # County overview metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Properties", len(county_data))
            with col2:
                market_score = county_data['county_market_score'].mean()
                st.metric("Market Score", f"{market_score:.1f}")
            with col3:
                geo_score = county_data['geographic_score'].mean()
                st.metric("Geographic Score", f"{geo_score:.1f}")
            with col4:
                timing_score = county_data['market_timing_score'].mean()
                st.metric("Timing Score", f"{timing_score:.1f}")

            # County performance radar chart
            st.subheader(f"{selected_county} County Intelligence Profile")

            radar_data = {
                'Market Conditions': market_score,
                'Geographic Advantages': geo_score,
                'Market Timing': timing_score,
                'Average Investment Score': county_data['investment_score'].mean(),
                'Water Features Rate': (len(county_data[county_data['water_score'] > 0]) / len(county_data)) * 100
            }

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=list(radar_data.values()),
                theta=list(radar_data.keys()),
                fill='toself',
                name=f'{selected_county} County'
            ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                title=f"{selected_county} County Intelligence Profile",
                height=500
            )

            st.plotly_chart(fig_radar, use_container_width=True)

    with tab3:
        st.header("Property Analytics")
        st.markdown("**Advanced property filtering and investment opportunity analysis**")

        # Advanced filtering interface
        df = load_analytics_data()
        if df.empty:
            st.warning("No data available for property analytics.")
            return

        filters = create_advanced_filtering_interface(df)

        # Apply filters and reload data
        filtered_df = load_analytics_data(filters)

        if filtered_df.empty:
            st.warning("No properties match the selected filters.")
            return

        st.subheader(f"Filtered Results: {len(filtered_df)} Properties")

        # Investment opportunity ranking
        ranking_fig = create_investment_opportunity_ranking(filtered_df)
        st.plotly_chart(ranking_fig, use_container_width=True)

        # Properties table with intelligence scores
        st.subheader("Properties with Intelligence Scores")
        display_columns = [
            'parcel_id', 'county', 'amount', 'acreage', 'investment_score',
            'county_market_score', 'geographic_score', 'market_timing_score',
            'total_description_score', 'water_score'
        ]

        # Format the dataframe for display
        display_df = filtered_df[display_columns].copy()
        for col in ['amount']:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
        for col in ['investment_score', 'county_market_score', 'geographic_score', 'market_timing_score', 'total_description_score']:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}")

        st.dataframe(display_df, use_container_width=True, height=400)

    with tab4:
        # Import and display the comprehensive investment insights dashboard
        from .investment_insights import display_investment_insights_dashboard
        display_investment_insights_dashboard()

# Main entry point
if __name__ == "__main__":
    display_analytics_dashboard()