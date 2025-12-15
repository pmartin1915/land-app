"""
Investment Insights Component for Alabama Auction Watcher
Advanced AI-driven investment recommendations and market intelligence analysis
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
import requests
import logging

# Import enhanced visualizations
from .visualizations import (
    create_investment_bubble_chart,
    create_multi_county_radar_comparison,
    create_intelligence_distribution_analysis,
    create_county_performance_heatmap,
    create_investment_timeline_analysis
)

# Import utility functions
from scripts.utils import format_currency
from config.security import get_security_config, create_secure_headers

logger = logging.getLogger(__name__)

@st.cache_data(ttl=300)
def load_investment_data() -> pd.DataFrame:
    """
    Load comprehensive property data for investment analysis.

    Returns:
        DataFrame with all property and intelligence data
    """
    # Use secure configuration for API access
    security_config = get_security_config()
    API_URL = f"{security_config.api_base_url}/properties/"
    headers = create_secure_headers()

    params = {
        "page_size": 10000,
        "sort_by": "investment_score",
        "sort_order": "desc"
    }

    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        properties_list = data.get('properties', [])
        df = pd.DataFrame(properties_list)

        if df.empty:
            return pd.DataFrame()

        # Ensure all intelligence columns exist
        intelligence_columns = {
            'county_market_score': 0.0,
            'geographic_score': 0.0,
            'market_timing_score': 0.0,
            'total_description_score': 0.0,
            'road_access_score': 0.0,
            'investment_score': 0.0,
            'water_score': 0.0,
            'amount': 0.0,
            'acreage': 0.0,
            'price_per_acre': 0.0,
            'county': 'Unknown',
            'parcel_id': 'Unknown'
        }

        for col, default in intelligence_columns.items():
            if col not in df.columns:
                df[col] = default

        return df

    except Exception as e:
        logger.error(f"Failed to load investment data: {e}")
        return pd.DataFrame()

def calculate_compound_investment_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate a compound investment score using multiple intelligence factors.

    Args:
        df: DataFrame with property data

    Returns:
        DataFrame with added compound score
    """
    if df.empty:
        return df

    df = df.copy()

    # Calculate compound score with weighted intelligence factors
    df['compound_score'] = (
        df['investment_score'] * 0.35 +           # Base investment score
        df['county_market_score'] * 0.25 +       # County market conditions
        df['geographic_score'] * 0.20 +          # Geographic advantages
        df['market_timing_score'] * 0.15 +       # Market timing
        df['total_description_score'] * 0.05     # Property description quality
    )

    # Add risk-adjusted score (penalize extreme high/low values)
    df['risk_adjusted_score'] = df['compound_score'] * (
        1 - abs(df['compound_score'] - df['compound_score'].mean()) / (2 * df['compound_score'].std() + 0.1)
    )

    return df

def identify_top_opportunities(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Identify top investment opportunities using compound intelligence scoring.

    Args:
        df: DataFrame with property data
        top_n: Number of top opportunities to return

    Returns:
        DataFrame with top opportunities
    """
    if df.empty:
        return pd.DataFrame()

    # Calculate compound scores
    df_scored = calculate_compound_investment_score(df)

    # Filter to properties with intelligence data
    df_intel = df_scored[df_scored['county_market_score'] > 0]

    if df_intel.empty:
        return pd.DataFrame()

    # Get top opportunities by compound score
    top_opportunities = df_intel.nlargest(top_n, 'compound_score')

    return top_opportunities

def analyze_market_segments(df: pd.DataFrame) -> Dict:
    """
    Analyze different market segments and investment strategies.

    Args:
        df: DataFrame with property data

    Returns:
        Dictionary with market segment analysis
    """
    if df.empty:
        return {}

    df_intel = df[df['county_market_score'] > 0].copy()

    if df_intel.empty:
        return {}

    # Define market segments
    segments = {
        'High Value Markets': df_intel[df_intel['county_market_score'] >= 80],
        'Emerging Markets': df_intel[
            (df_intel['county_market_score'] >= 40) &
            (df_intel['county_market_score'] < 80) &
            (df_intel['market_timing_score'] >= 50)
        ],
        'Value Opportunities': df_intel[
            (df_intel['investment_score'] >= 60) &
            (df_intel['amount'] <= df_intel['amount'].median())
        ],
        'Premium Properties': df_intel[
            (df_intel['geographic_score'] >= 75) &
            (df_intel['water_score'] > 0)
        ],
        'Development Ready': df_intel[
            (df_intel['road_access_score'] >= 70) &
            (df_intel['total_description_score'] >= 60)
        ]
    }

    # Calculate segment statistics
    segment_stats = {}
    for segment_name, segment_data in segments.items():
        if not segment_data.empty:
            segment_stats[segment_name] = {
                'count': len(segment_data),
                'avg_price': segment_data['amount'].mean(),
                'avg_investment_score': segment_data['investment_score'].mean(),
                'avg_compound_score': segment_data.get('compound_score', pd.Series([0])).mean(),
                'counties': segment_data['county'].unique().tolist()
            }

    return segment_stats

def generate_investment_recommendations(df: pd.DataFrame) -> List[Dict]:
    """
    Generate AI-driven investment recommendations based on intelligence analysis.

    Args:
        df: DataFrame with property data

    Returns:
        List of investment recommendations
    """
    if df.empty:
        return []

    recommendations = []

    # Market segment analysis
    segments = analyze_market_segments(df)

    # Recommendation 1: High-value market opportunities
    if 'High Value Markets' in segments and segments['High Value Markets']['count'] > 0:
        recommendations.append({
            'type': 'High Value Markets',
            'title': 'Focus on High-Value County Markets',
            'description': f"Counties with market scores ≥80 show strong economic fundamentals. "
                          f"{segments['High Value Markets']['count']} properties available with "
                          f"average investment score of {segments['High Value Markets']['avg_investment_score']:.1f}.",
            'priority': 'High',
            'action': 'Consider immediate investment in these stable markets'
        })

    # Recommendation 2: Emerging market timing
    if 'Emerging Markets' in segments and segments['Emerging Markets']['count'] > 0:
        recommendations.append({
            'type': 'Emerging Markets',
            'title': 'Capitalize on Emerging Market Timing',
            'description': f"Emerging markets with good timing scores offer growth potential. "
                          f"{segments['Emerging Markets']['count']} opportunities identified.",
            'priority': 'Medium',
            'action': 'Monitor for optimal entry points in the next 6-12 months'
        })

    # Recommendation 3: Value opportunities
    if 'Value Opportunities' in segments and segments['Value Opportunities']['count'] > 0:
        recommendations.append({
            'type': 'Value Opportunities',
            'title': 'Value Investment Strategy',
            'description': f"High-scoring properties below median price offer value opportunities. "
                          f"Average price: {format_currency(segments['Value Opportunities']['avg_price'])}",
            'priority': 'Medium',
            'action': 'Ideal for value-focused investment strategies'
        })

    # Recommendation 4: Premium properties
    if 'Premium Properties' in segments and segments['Premium Properties']['count'] > 0:
        recommendations.append({
            'type': 'Premium Properties',
            'title': 'Premium Geographic Advantages',
            'description': f"Properties with high geographic scores and water features command premium values. "
                          f"{segments['Premium Properties']['count']} properties available.",
            'priority': 'High',
            'action': 'Consider for long-term appreciation and premium positioning'
        })

    # Recommendation 5: County diversification
    df_intel = df[df['county_market_score'] > 0]
    if not df_intel.empty:
        county_scores = df_intel.groupby('county')['compound_score'].mean().sort_values(ascending=False)
        top_counties = county_scores.head(3).index.tolist()

        recommendations.append({
            'type': 'Diversification',
            'title': 'Geographic Diversification Strategy',
            'description': f"Diversify across top-performing counties: {', '.join(top_counties)} "
                          f"for optimal risk-adjusted returns.",
            'priority': 'Medium',
            'action': 'Build portfolio across multiple high-scoring counties'
        })

    return recommendations

def display_investment_insights_dashboard():
    """
    Display the main investment insights dashboard.
    """
    st.header("Investment Insights Dashboard")
    st.markdown("**AI-driven investment recommendations and advanced market intelligence**")

    # Load investment data
    df = load_investment_data()

    if df.empty:
        st.warning("No investment data available. Please ensure the backend API is running.")
        return

    # Calculate compound scores
    df_scored = calculate_compound_investment_score(df)

    # Key metrics overview
    st.subheader("Market Intelligence Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_properties = len(df_scored)
        st.metric("Total Properties", f"{total_properties:,}")

    with col2:
        intel_properties = len(df_scored[df_scored['county_market_score'] > 0])
        st.metric("Intelligence Enhanced", f"{intel_properties:,}")

    with col3:
        avg_compound = df_scored['compound_score'].mean()
        st.metric("Avg Compound Score", f"{avg_compound:.1f}")

    with col4:
        high_value_count = len(df_scored[df_scored['compound_score'] >= 70])
        st.metric("High-Value Opportunities", f"{high_value_count:,}")

    with col5:
        counties_analyzed = df_scored['county'].nunique()
        st.metric("Counties Analyzed", f"{counties_analyzed}")

    st.markdown("---")

    # Top Investment Opportunities
    st.subheader("Top Investment Opportunities")

    top_opportunities = identify_top_opportunities(df_scored, 10)

    if not top_opportunities.empty:
        # Display top opportunities in expandable cards
        for i, (_, opportunity) in enumerate(top_opportunities.iterrows()):
            with st.expander(
                f"#{i+1} - {opportunity['parcel_id']} ({opportunity['county']} County) - "
                f"Score: {opportunity['compound_score']:.1f}"
            ):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Price", format_currency(opportunity['amount']))
                    st.metric("Investment Score", f"{opportunity['investment_score']:.1f}")

                with col2:
                    st.metric("County Market", f"{opportunity['county_market_score']:.1f}")
                    st.metric("Geographic", f"{opportunity['geographic_score']:.1f}")

                with col3:
                    st.metric("Market Timing", f"{opportunity['market_timing_score']:.1f}")
                    st.metric("Water Score", f"{opportunity['water_score']:.1f}")

                # Investment rationale
                rationale = []
                if opportunity['county_market_score'] >= 80:
                    rationale.append("Strong county market fundamentals")
                if opportunity['geographic_score'] >= 75:
                    rationale.append("Excellent geographic advantages")
                if opportunity['market_timing_score'] >= 60:
                    rationale.append("Favorable market timing")
                if opportunity['water_score'] > 0:
                    rationale.append("Water features premium")

                if rationale:
                    st.markdown("**Investment Rationale:** " + " • ".join(rationale))

    st.markdown("---")

    # Advanced Visualizations
    st.subheader("Advanced Market Analysis")

    # Create tabs for different analysis views
    viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
        "Investment Bubble Chart",
        "County Performance",
        "Market Timing Analysis",
        "Intelligence Distribution"
    ])

    with viz_tab1:
        bubble_chart = create_investment_bubble_chart(df_scored)
        st.plotly_chart(bubble_chart, use_container_width=True)
        st.markdown("""
        **Chart Explanation:** This bubble chart shows investment opportunities across multiple dimensions:
        - **X-axis:** County Market Score (economic conditions)
        - **Y-axis:** Investment Score (overall attractiveness)
        - **Bubble Size:** Property acreage
        - **Color:** Geographic Score (natural advantages)
        """)

    with viz_tab2:
        performance_heatmap = create_county_performance_heatmap(df_scored)
        st.plotly_chart(performance_heatmap, use_container_width=True)

        # County comparison radar
        st.subheader("County Intelligence Comparison")
        counties_with_data = df_scored[df_scored['county_market_score'] > 0]['county'].unique()
        selected_counties = st.multiselect(
            "Select counties to compare (max 5):",
            counties_with_data,
            default=counties_with_data[:3] if len(counties_with_data) >= 3 else counties_with_data
        )

        if selected_counties:
            radar_comparison = create_multi_county_radar_comparison(df_scored, selected_counties[:5])
            st.plotly_chart(radar_comparison, use_container_width=True)

    with viz_tab3:
        timing_analysis = create_investment_timeline_analysis(df_scored)
        st.plotly_chart(timing_analysis, use_container_width=True)

        st.markdown("""
        **Market Timing Categories:**
        - **Emerging Market (0-33):** Early development phase, higher risk/reward
        - **Growth Phase (34-66):** Active development, balanced opportunity
        - **Peak Opportunity (67-100):** Optimal conditions, stable investment
        """)

    with viz_tab4:
        distribution_analysis = create_intelligence_distribution_analysis(df_scored)
        st.plotly_chart(distribution_analysis, use_container_width=True)

    st.markdown("---")

    # AI Investment Recommendations
    st.subheader("AI Investment Recommendations")

    recommendations = generate_investment_recommendations(df_scored)

    if recommendations:
        for rec in recommendations:
            priority_color = {
                'High': 'High',
                'Medium': '🟡',
                'Low': '🟢'
            }.get(rec['priority'], 'Normal')

            st.markdown(f"""
            ### {priority_color} {rec['title']} ({rec['priority']} Priority)
            **{rec['description']}**

            **Recommended Action:** {rec['action']}
            """)
            st.markdown("---")

    # Market Segment Analysis
    st.subheader("Market Segment Analysis")

    segments = analyze_market_segments(df_scored)

    if segments:
        segment_cols = st.columns(len(segments))

        for i, (segment_name, stats) in enumerate(segments.items()):
            with segment_cols[i % len(segment_cols)]:
                st.markdown(f"**{segment_name}**")
                st.metric("Properties", stats['count'])
                st.metric("Avg Price", format_currency(stats['avg_price']))
                st.metric("Avg Score", f"{stats['avg_investment_score']:.1f}")
                st.markdown(f"**Counties:** {', '.join(stats['counties'][:3])}")

    # Export functionality
    st.markdown("---")
    st.subheader("Export Investment Analysis")

    if st.button("Generate Investment Report"):
        # Create comprehensive report
        report_data = {
            'top_opportunities': top_opportunities,
            'market_segments': segments,
            'recommendations': recommendations
        }

        # Convert top opportunities to CSV format
        if not top_opportunities.empty:
            csv_data = top_opportunities[[
                'parcel_id', 'county', 'amount', 'acreage', 'investment_score',
                'compound_score', 'county_market_score', 'geographic_score',
                'market_timing_score', 'water_score'
            ]].to_csv(index=False)

            st.download_button(
                label="Download Top Opportunities CSV",
                data=csv_data,
                file_name="investment_opportunities.csv",
                mime="text/csv"
            )

    st.markdown("---")
    st.info("""
    **Investment Intelligence System**: This dashboard leverages 14+ intelligence factors
    across county market conditions, geographic advantages, and property-specific metrics to
    provide sophisticated investment analysis and recommendations.
    """)

# Main entry point
if __name__ == "__main__":
    display_investment_insights_dashboard()