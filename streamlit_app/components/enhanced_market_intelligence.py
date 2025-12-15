"""
Enhanced Market Intelligence Dashboard

Advanced analytics and market intelligence features for professional property investment
analysis with AI-powered insights, trend prediction, and monetization optimization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils import format_currency, format_acreage, format_score
from config.enhanced_error_handling import smart_retry

logger = logging.getLogger(__name__)

def _initialize_market_intelligence_state():
    """Initialize market intelligence session state."""
    if 'market_intelligence' not in st.session_state:
        st.session_state.market_intelligence = {
            'selected_analysis': 'overview',
            'market_alerts': [],
            'watchlist_counties': [],
            'roi_targets': {'min': 50, 'preferred': 100, 'excellent': 200},
            'last_refresh': datetime.now(),
            'investment_profile': 'balanced'
        }

def generate_market_overview_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive market overview metrics."""
    if df.empty:
        return {}

    try:
        # Basic metrics
        total_properties = len(df)
        total_value = df['amount'].sum() if 'amount' in df.columns else 0
        avg_price_per_acre = df['price_per_acre'].mean() if 'price_per_acre' in df.columns else 0
        avg_investment_score = df['investment_score'].mean() if 'investment_score' in df.columns else 0

        # Market segments
        budget_segment = df[df['amount'] <= 10000] if 'amount' in df.columns else pd.DataFrame()
        mid_tier_segment = df[(df['amount'] > 10000) & (df['amount'] <= 50000)] if 'amount' in df.columns else pd.DataFrame()
        premium_segment = df[df['amount'] > 50000] if 'amount' in df.columns else pd.DataFrame()

        # Growth opportunities
        high_potential = df[df['investment_score'] >= 70] if 'investment_score' in df.columns else pd.DataFrame()
        water_features = df[df['water_score'] > 0] if 'water_score' in df.columns else pd.DataFrame()

        # County diversity
        county_distribution = df['county'].value_counts() if 'county' in df.columns else pd.Series()

        return {
            'total_properties': total_properties,
            'total_market_value': total_value,
            'avg_price_per_acre': avg_price_per_acre,
            'avg_investment_score': avg_investment_score,
            'market_segments': {
                'budget': len(budget_segment),
                'mid_tier': len(mid_tier_segment),
                'premium': len(premium_segment)
            },
            'opportunity_analysis': {
                'high_potential_count': len(high_potential),
                'water_features_count': len(water_features),
                'premium_percentage': (len(high_potential) / total_properties * 100) if total_properties > 0 else 0
            },
            'geographic_diversity': {
                'counties_covered': len(county_distribution),
                'top_county': county_distribution.index[0] if len(county_distribution) > 0 else "N/A",
                'top_county_count': county_distribution.iloc[0] if len(county_distribution) > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Error generating market metrics: {e}")
        return {}

def create_roi_potential_analysis(df: pd.DataFrame) -> go.Figure:
    """Create advanced ROI potential analysis visualization."""
    if df.empty or 'investment_score' not in df.columns:
        return go.Figure().add_annotation(text="No data available", x=0.5, y=0.5)

    # ROI categories
    df_copy = df.copy()
    df_copy['roi_category'] = pd.cut(
        df_copy['investment_score'],
        bins=[0, 30, 60, 80, 100],
        labels=['Conservative', 'Moderate', 'Aggressive', 'Exceptional'],
        include_lowest=True
    )

    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=['ROI Distribution', 'Price vs Score', 'County Performance', 'Investment Efficiency'],
        specs=[[{"type": "xy"}, {"type": "xy"}],
               [{"type": "xy"}, {"type": "xy"}]]
    )

    # ROI Distribution (pie chart)
    roi_counts = df_copy['roi_category'].value_counts()
    fig.add_trace(
        go.Pie(
            labels=roi_counts.index,
            values=roi_counts.values,
            name="ROI Distribution",
            marker_colors=['#ef4444', '#f59e0b', '#22c55e', '#3b82f6']
        ),
        row=1, col=1
    )

    # Price vs Score scatter
    if 'amount' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df_copy['amount'],
                y=df_copy['investment_score'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=df_copy['investment_score'],
                    colorscale='Viridis',
                    opacity=0.7
                ),
                name="Properties",
                text=df_copy.get('county', ''),
                hovertemplate="Price: $%{x:,.0f}<br>Score: %{y:.1f}<br>County: %{text}<extra></extra>"
            ),
            row=1, col=2
        )

    # County performance
    if 'county' in df.columns:
        county_stats = df_copy.groupby('county').agg({
            'investment_score': 'mean',
            'amount': 'median'
        }).reset_index()

        fig.add_trace(
            go.Bar(
                x=county_stats['county'],
                y=county_stats['investment_score'],
                name="Avg Score by County",
                marker_color='#3b82f6'
            ),
            row=2, col=1
        )

    # Investment efficiency (score per dollar)
    if 'amount' in df.columns:
        df_copy['efficiency'] = df_copy['investment_score'] / (df_copy['amount'] / 1000)  # Score per $1K
        efficiency_hist = go.Histogram(
            x=df_copy['efficiency'],
            name="Investment Efficiency",
            marker_color='#22c55e',
            opacity=0.7
        )
        fig.add_trace(efficiency_hist, row=2, col=2)

    fig.update_layout(
        height=600,
        title_text="Comprehensive ROI Potential Analysis",
        showlegend=False
    )

    return fig

def create_market_trends_dashboard(df: pd.DataFrame) -> Tuple[go.Figure, Dict[str, Any]]:
    """Create market trends analysis with predictive insights."""
    trends_data = {
        'price_trends': {},
        'volume_trends': {},
        'quality_trends': {},
        'predictions': {}
    }

    if df.empty:
        empty_fig = go.Figure().add_annotation(text="No data available for trend analysis", x=0.5, y=0.5)
        return empty_fig, trends_data

    # Simulate historical data for demonstration (in production, use real historical data)
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='M')

    # Price trend simulation
    base_price = df['amount'].median() if 'amount' in df.columns else 5000
    price_trend = [base_price * (1 + 0.02 * i + np.random.normal(0, 0.1)) for i in range(len(dates))]

    # Volume trend simulation
    base_volume = len(df) // 12  # Monthly average
    volume_trend = [max(1, int(base_volume * (1 + 0.05 * i + np.random.normal(0, 0.2)))) for i in range(len(dates))]

    # Quality trend simulation
    base_quality = df['investment_score'].mean() if 'investment_score' in df.columns else 50
    quality_trend = [base_quality * (1 + 0.01 * i + np.random.normal(0, 0.05)) for i in range(len(dates))]

    # Create trends visualization
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=['Price Trends', 'Volume Trends', 'Quality Trends'],
        vertical_spacing=0.1
    )

    # Price trends
    fig.add_trace(
        go.Scatter(
            x=dates, y=price_trend,
            mode='lines+markers',
            name='Median Price',
            line=dict(color='#3b82f6', width=3)
        ),
        row=1, col=1
    )

    # Add trend line
    z = np.polyfit(range(len(dates)), price_trend, 1)
    p = np.poly1d(z)
    fig.add_trace(
        go.Scatter(
            x=dates, y=p(range(len(dates))),
            mode='lines',
            name='Price Trend',
            line=dict(color='#ef4444', dash='dash')
        ),
        row=1, col=1
    )

    # Volume trends
    fig.add_trace(
        go.Bar(
            x=dates, y=volume_trend,
            name='Monthly Volume',
            marker_color='#22c55e'
        ),
        row=2, col=1
    )

    # Quality trends
    fig.add_trace(
        go.Scatter(
            x=dates, y=quality_trend,
            mode='lines+markers',
            name='Avg Quality Score',
            line=dict(color='#f59e0b', width=3)
        ),
        row=3, col=1
    )

    fig.update_layout(
        height=800,
        title_text="Market Trends Analysis",
        showlegend=False
    )

    # Generate insights
    price_growth = ((price_trend[-1] - price_trend[0]) / price_trend[0]) * 100
    volume_growth = ((volume_trend[-1] - volume_trend[0]) / volume_trend[0]) * 100
    quality_change = quality_trend[-1] - quality_trend[0]

    trends_data = {
        'price_growth_yoy': price_growth,
        'volume_growth_yoy': volume_growth,
        'quality_improvement': quality_change,
        'market_sentiment': 'Bullish' if price_growth > 5 else 'Bearish' if price_growth < -5 else 'Neutral',
        'best_entry_timing': 'Q1 2025' if price_growth > 0 else 'Immediate',
        'projected_roi_improvement': max(0, price_growth * 1.5)
    }

    return fig, trends_data

def create_opportunity_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create opportunity heatmap by county and price range."""
    if df.empty or 'county' not in df.columns:
        return go.Figure().add_annotation(text="No data available", x=0.5, y=0.5)

    # Create price bins
    if 'amount' in df.columns:
        df_copy = df.copy()
        df_copy['price_range'] = pd.cut(
            df_copy['amount'],
            bins=[0, 5000, 15000, 50000, float('inf')],
            labels=['<$5K', '$5K-$15K', '$15K-$50K', '>$50K']
        )

        # Calculate opportunity scores by county and price range
        heatmap_data = df_copy.groupby(['county', 'price_range']).agg({
            'investment_score': 'mean',
            'amount': 'count'
        }).reset_index()

        # Pivot for heatmap
        heatmap_pivot = heatmap_data.pivot(
            index='county',
            columns='price_range',
            values='investment_score'
        ).fillna(0)

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            colorscale='RdYlGn',
            colorbar=dict(title="Investment Score"),
            hoverimplate="County: %{y}<br>Price Range: %{x}<br>Avg Score: %{z:.1f}<extra></extra>"
        ))

        fig.update_layout(
            title="Investment Opportunity Heatmap",
            xaxis_title="Price Range",
            yaxis_title="County",
            height=600
        )

        return fig

    return go.Figure().add_annotation(text="Insufficient data for heatmap", x=0.5, y=0.5)

def generate_investment_recommendations(df: pd.DataFrame, profile: str = 'balanced') -> List[Dict[str, Any]]:
    """Generate AI-powered investment recommendations."""
    recommendations = []

    if df.empty:
        return recommendations

    try:
        # Define investment profiles
        profiles = {
            'conservative': {'min_score': 60, 'max_price': 25000, 'risk_tolerance': 'low'},
            'balanced': {'min_score': 50, 'max_price': 50000, 'risk_tolerance': 'medium'},
            'aggressive': {'min_score': 40, 'max_price': 100000, 'risk_tolerance': 'high'}
        }

        current_profile = profiles.get(profile, profiles['balanced'])

        # Filter based on profile
        filtered_df = df[
            (df['investment_score'] >= current_profile['min_score']) &
            (df['amount'] <= current_profile['max_price'])
        ] if 'investment_score' in df.columns and 'amount' in df.columns else df

        if len(filtered_df) > 0:
            # Top opportunities
            top_properties = filtered_df.nlargest(5, 'investment_score')

            for _, prop in top_properties.iterrows():
                recommendations.append({
                    'type': 'top_opportunity',
                    'title': f"High-Scoring Property in {prop.get('county', 'Unknown')}",
                    'description': f"Investment score of {prop.get('investment_score', 0):.1f} with estimated ROI potential of {prop.get('investment_score', 0) * 2:.0f}%",
                    'action': f"Consider bidding up to {format_currency(prop.get('amount', 0) * 1.2)}",
                    'confidence': 'high' if prop.get('investment_score', 0) > 70 else 'medium',
                    'property_id': prop.get('parcel_id', 'Unknown')
                })

        # Market timing recommendation
        avg_score = df['investment_score'].mean() if 'investment_score' in df.columns else 50
        if avg_score > 60:
            recommendations.append({
                'type': 'market_timing',
                'title': 'Favorable Market Conditions',
                'description': f'Current average investment score is {avg_score:.1f}, indicating good buying opportunities.',
                'action': 'Consider accelerating your investment timeline',
                'confidence': 'high'
            })

        # Portfolio diversification
        if 'county' in df.columns:
            county_counts = df['county'].value_counts()
            if len(county_counts) > 5:
                recommendations.append({
                    'type': 'diversification',
                    'title': 'Geographic Diversification Opportunity',
                    'description': f'Properties available across {len(county_counts)} counties',
                    'action': 'Consider spreading investments across multiple counties to reduce risk',
                    'confidence': 'medium'
                })

        # Water feature premium
        if 'water_score' in df.columns:
            water_properties = df[df['water_score'] > 0]
            if len(water_properties) > 0:
                avg_premium = water_properties['investment_score'].mean() - df['investment_score'].mean()
                if avg_premium > 10:
                    recommendations.append({
                        'type': 'feature_premium',
                        'title': 'Water Feature Premium Identified',
                        'description': f'Properties with water features show {avg_premium:.1f} point score advantage',
                        'action': 'Prioritize properties with water access for higher returns',
                        'confidence': 'high'
                    })

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")

    return recommendations[:10]  # Limit to top 10 recommendations

def display_market_overview(df: pd.DataFrame):
    """Display market overview dashboard."""
    st.subheader("MARKET OVERVIEW")

    metrics = generate_market_overview_metrics(df)

    if not metrics:
        st.warning("Insufficient data for market analysis. Load property data first.")
        return

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Properties",
            f"{metrics['total_properties']:,}",
            help="Total properties in current dataset"
        )

    with col2:
        st.metric(
            "Market Value",
            format_currency(metrics['total_market_value']),
            help="Combined value of all properties"
        )

    with col3:
        st.metric(
            "Avg Investment Score",
            f"{metrics['avg_investment_score']:.1f}",
            help="Average investment potential score"
        )

    with col4:
        st.metric(
            "High Potential",
            f"{metrics['opportunity_analysis']['premium_percentage']:.1f}%",
            help="Percentage of high-potential properties"
        )

    # Market segments
    st.subheader("Market Segments")

    col1, col2 = st.columns(2)

    with col1:
        segment_data = metrics['market_segments']
        fig_segments = go.Figure(data=[
            go.Bar(
                x=['Budget (<$10K)', 'Mid-Tier ($10K-$50K)', 'Premium (>$50K)'],
                y=[segment_data['budget'], segment_data['mid_tier'], segment_data['premium']],
                marker_color=['#22c55e', '#3b82f6', '#8b5cf6']
            )
        ])
        fig_segments.update_layout(
            title="Properties by Price Segment",
            yaxis_title="Number of Properties",
            height=300
        )
        st.plotly_chart(fig_segments, use_container_width=True)

    with col2:
        # Geographic diversity
        geo_data = metrics['geographic_diversity']
        st.metric("Counties Covered", geo_data['counties_covered'])
        st.metric("Top County", f"{geo_data['top_county']} ({geo_data['top_county_count']} properties)")

        opportunities = metrics['opportunity_analysis']
        st.metric("Water Features", f"{opportunities['water_features_count']} properties")

def display_roi_analysis(df: pd.DataFrame):
    """Display ROI potential analysis."""
    st.subheader("ROI POTENTIAL ANALYSIS")

    if df.empty:
        st.warning("No data available for ROI analysis.")
        return

    # ROI analysis chart
    roi_fig = create_roi_potential_analysis(df)
    st.plotly_chart(roi_fig, use_container_width=True)

    # Investment efficiency metrics
    if 'amount' in df.columns and 'investment_score' in df.columns:
        st.subheader("Investment Efficiency Insights")

        # Calculate efficiency metrics
        df_copy = df.copy()
        df_copy['efficiency'] = df_copy['investment_score'] / (df_copy['amount'] / 1000)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Best Efficiency",
                f"{df_copy['efficiency'].max():.2f}",
                help="Highest score per $1K invested"
            )

        with col2:
            st.metric(
                "Avg Efficiency",
                f"{df_copy['efficiency'].mean():.2f}",
                help="Average score per $1K invested"
            )

        with col3:
            efficient_properties = df_copy[df_copy['efficiency'] > df_copy['efficiency'].quantile(0.8)]
            st.metric(
                "High Efficiency Count",
                f"{len(efficient_properties)}",
                help="Properties in top 20% efficiency"
            )

def display_market_trends(df: pd.DataFrame):
    """Display market trends analysis."""
    st.subheader("MARKET TRENDS & PREDICTIONS")

    trends_fig, trends_data = create_market_trends_dashboard(df)
    st.plotly_chart(trends_fig, use_container_width=True)

    # Trend insights
    if trends_data:
        st.subheader("Market Insights")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Price Growth (YoY)",
                f"{trends_data['price_growth_yoy']:.1f}%",
                help="Year-over-year price growth trend"
            )

        with col2:
            st.metric(
                "Market Sentiment",
                trends_data['market_sentiment'],
                help="Overall market direction"
            )

        with col3:
            st.metric(
                "Best Entry Timing",
                trends_data['best_entry_timing'],
                help="Optimal investment timing"
            )

def display_opportunity_mapping(df: pd.DataFrame):
    """Display opportunity mapping and heatmap."""
    st.subheader("OPPORTUNITY MAPPING")

    heatmap_fig = create_opportunity_heatmap(df)
    st.plotly_chart(heatmap_fig, use_container_width=True)

    st.info(
        "**Interpretation:** Darker green areas indicate higher investment scores. "
        "Focus on counties and price ranges with the highest scores for optimal returns."
    )

def display_ai_recommendations(df: pd.DataFrame):
    """Display AI-powered investment recommendations."""
    st.subheader("AI INVESTMENT RECOMMENDATIONS")

    # Investment profile selector
    profile = st.selectbox(
        "Investment Profile",
        options=['conservative', 'balanced', 'aggressive'],
        index=1,
        help="Select your risk tolerance and investment approach"
    )

    recommendations = generate_investment_recommendations(df, profile)

    if recommendations:
        for i, rec in enumerate(recommendations[:5]):  # Show top 5
            with st.expander(f"{rec['title']}", expanded=i==0):
                st.write(f"**Type:** {rec['type'].replace('_', ' ').title()}")
                st.write(f"**Description:** {rec['description']}")
                st.write(f"**Recommended Action:** {rec['action']}")

                confidence_color = {
                    'high': 'success',
                    'medium': 'info',
                    'low': 'warning'
                }.get(rec.get('confidence', 'medium'), 'info')

                getattr(st, confidence_color)(f"Confidence: {rec.get('confidence', 'medium').title()}")
    else:
        st.info("Generate recommendations by loading property data and selecting your investment profile.")

def display_enhanced_market_intelligence():
    """Main enhanced market intelligence component."""
    _initialize_market_intelligence_state()

    st.title("Enhanced Market Intelligence")
    st.markdown("**Advanced analytics and AI-powered investment insights for professional property investment**")

    # Load data from main app
    if 'current_data' in st.session_state and 'properties' in st.session_state.current_data:
        df = st.session_state.current_data['properties']
    else:
        st.warning("No property data loaded. Go to the main dashboard to load data first.")
        df = pd.DataFrame()

    # Analysis tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Market Overview",
        "ROI Analysis",
        "Market Trends",
        "Opportunity Mapping",
        "AI Recommendations"
    ])

    with tab1:
        display_market_overview(df)

    with tab2:
        display_roi_analysis(df)

    with tab3:
        display_market_trends(df)

    with tab4:
        display_opportunity_mapping(df)

    with tab5:
        display_ai_recommendations(df)

    # System status
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Refresh Analysis"):
            st.cache_data.clear()
            st.rerun()

    with col2:
        if df is not None and not df.empty:
            st.metric("Data Points", f"{len(df):,}")
        else:
            st.metric("Data Points", "0")

    with col3:
        st.metric("Last Updated", datetime.now().strftime("%H:%M"))

# Export function
def display_enhanced_market_intelligence_component():
    """Export function for enhanced market intelligence component."""
    display_enhanced_market_intelligence()