"""
Predictive Analytics Dashboard Component
Alabama Auction Watcher - Market Intelligence Interface

This component provides an interactive dashboard for the Predictive Market Intelligence Engine,
featuring property appreciation forecasts, market timing analysis, and emerging opportunities.

Author: Claude Code AI Assistant
Date: 2025-09-20
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Any
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.predictive_market_engine import (
    get_predictive_engine,
    PropertyAppreciationForecast,
    MarketTimingAnalysis,
    EmergingOpportunity,
    PredictionConfidence,
    MarketTrend
)
from streamlit_app.core.performance_monitor import monitor_performance
from streamlit_app.core.cache_manager import smart_cache

logger = logging.getLogger(__name__)


@st.cache_data(ttl=1800)  # Cache for 30 minutes
@smart_cache(cache_type="computed_result", ttl_seconds=1800, key_prefix="predictive_dashboard")
@monitor_performance("predictive_dashboard_data_loading")
def load_predictive_analytics_data(properties_data: List[Dict]) -> Dict[str, Any]:
    """
    Load and process data for predictive analytics dashboard.

    Args:
        properties_data: List of property data from the main app

    Returns:
        Dictionary containing processed analytics data
    """

    if not properties_data:
        return {
            "appreciation_forecasts": [],
            "market_timing": {},
            "opportunities": [],
            "county_insights": {},
            "performance_metrics": {}
        }

    engine = get_predictive_engine()

    # Process appreciation forecasts for top properties
    forecasts = []
    for prop in properties_data[:50]:  # Limit to top 50 for performance
        county = prop.get("county", "")
        if county:
            try:
                forecast = engine.predict_property_appreciation(
                    prop, county, prop.get("investment_score", 50)
                )

                forecasts.append({
                    "property_id": prop.get("id", ""),
                    "county": county,
                    "current_score": prop.get("investment_score", 50),
                    "price_per_acre": prop.get("price_per_acre", 0),
                    "acreage": prop.get("acreage", 0),
                    "one_year": forecast.one_year_appreciation,
                    "three_year": forecast.three_year_appreciation,
                    "five_year": forecast.five_year_appreciation,
                    "confidence": forecast.confidence_level.value,
                    "risk_score": forecast.risk_score,
                    "market_trend": forecast.market_trend.value
                })
            except Exception as e:
                logger.warning(f"Failed to generate forecast for property {prop.get('id')}: {e}")

    # Analyze market timing by county
    counties = list(set(prop.get("county", "") for prop in properties_data if prop.get("county")))
    market_timing = {}

    for county in counties[:10]:  # Limit to top 10 counties
        try:
            timing = engine.analyze_market_timing(county)
            market_timing[county] = {
                "market_phase": timing.current_market_phase,
                "buy_window": timing.optimal_buy_window,
                "sell_window": timing.optimal_sell_window,
                "price_momentum": timing.price_momentum,
                "volatility": timing.market_volatility,
                "confidence": timing.confidence_score
            }
        except Exception as e:
            logger.warning(f"Failed to analyze market timing for {county}: {e}")

    # Detect emerging opportunities
    opportunities = []
    try:
        opportunities_data = engine.detect_emerging_opportunities(properties_data, top_n=20)
        for opp in opportunities_data:
            opportunities.append({
                "property_id": opp.property_id,
                "county": opp.county,
                "opportunity_type": opp.opportunity_type,
                "score": opp.opportunity_score,
                "potential_appreciation": opp.potential_appreciation,
                "risk_adjusted_return": opp.risk_adjusted_return,
                "timeline_months": opp.expected_timeline_months,
                "confidence": opp.confidence_level.value,
                "primary_drivers": opp.primary_drivers,
                "risk_factors": opp.risk_factors
            })
    except Exception as e:
        logger.warning(f"Failed to detect opportunities: {e}")

    return {
        "appreciation_forecasts": forecasts,
        "market_timing": market_timing,
        "opportunities": opportunities,
        "county_insights": _analyze_county_insights(forecasts, market_timing),
        "performance_metrics": _calculate_performance_metrics(forecasts)
    }


def _analyze_county_insights(forecasts: List[Dict], market_timing: Dict) -> Dict[str, Any]:
    """Analyze county-level insights from forecasts and timing data."""

    county_data = {}

    # Aggregate forecasts by county
    for forecast in forecasts:
        county = forecast["county"]
        if county not in county_data:
            county_data[county] = {
                "property_count": 0,
                "avg_appreciation_3yr": 0,
                "avg_confidence": 0,
                "avg_risk": 0,
                "market_phase": market_timing.get(county, {}).get("market_phase", "unknown")
            }

        county_data[county]["property_count"] += 1
        county_data[county]["avg_appreciation_3yr"] += forecast["three_year"]
        county_data[county]["avg_risk"] += forecast["risk_score"]

    # Calculate averages
    for county, data in county_data.items():
        if data["property_count"] > 0:
            data["avg_appreciation_3yr"] /= data["property_count"]
            data["avg_risk"] /= data["property_count"]

    return county_data


def _calculate_performance_metrics(forecasts: List[Dict]) -> Dict[str, Any]:
    """Calculate performance metrics for the predictive analytics."""

    if not forecasts:
        return {}

    appreciation_values = [f["three_year"] for f in forecasts]
    confidence_scores = [f["confidence"] for f in forecasts]
    risk_scores = [f["risk_score"] for f in forecasts]

    return {
        "total_properties_analyzed": len(forecasts),
        "avg_3yr_appreciation": sum(appreciation_values) / len(appreciation_values),
        "max_3yr_appreciation": max(appreciation_values),
        "min_3yr_appreciation": min(appreciation_values),
        "high_confidence_pct": len([c for c in confidence_scores if c in ["high", "very_high"]]) / len(confidence_scores) * 100,
        "avg_risk_score": sum(risk_scores) / len(risk_scores),
        "low_risk_properties": len([r for r in risk_scores if r < 0.3])
    }


@monitor_performance("predictive_dashboard_appreciation_chart")
def create_appreciation_forecast_chart(forecasts: List[Dict]) -> go.Figure:
    """Create appreciation forecast visualization."""

    if not forecasts:
        fig = go.Figure()
        fig.add_annotation(text="No forecast data available",
                          xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    df = pd.DataFrame(forecasts)

    # Create subplot with appreciation forecasts
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "3-Year Appreciation by County",
            "Risk vs Appreciation Analysis",
            "Confidence Distribution",
            "Market Trend Analysis"
        ),
        specs=[[{"type": "bar"}, {"type": "scatter"}],
               [{"type": "pie"}, {"type": "bar"}]]
    )

    # County appreciation averages
    county_avg = df.groupby("county")["three_year"].mean().reset_index()
    county_avg = county_avg.sort_values("three_year", ascending=False).head(10)

    fig.add_trace(
        go.Bar(
            x=county_avg["county"],
            y=county_avg["three_year"] * 100,  # Convert to percentage
            name="Avg 3-Year Appreciation (%)",
            marker_color="lightblue"
        ),
        row=1, col=1
    )

    # Risk vs Appreciation scatter
    fig.add_trace(
        go.Scatter(
            x=df["risk_score"],
            y=df["three_year"] * 100,
            mode="markers",
            name="Properties",
            marker=dict(
                size=8,
                color=df["current_score"],
                colorscale="Viridis",
                colorbar=dict(title="Investment Score"),
                showscale=True
            ),
            text=df["county"],
            hovertemplate="<b>%{text}</b><br>" +
                         "Risk Score: %{x:.2f}<br>" +
                         "3-Year Appreciation: %{y:.1f}%<br>" +
                         "<extra></extra>"
        ),
        row=1, col=2
    )

    # Confidence distribution
    confidence_counts = df["confidence"].value_counts()
    fig.add_trace(
        go.Pie(
            labels=confidence_counts.index,
            values=confidence_counts.values,
            name="Confidence Levels"
        ),
        row=2, col=1
    )

    # Market trend analysis
    trend_counts = df["market_trend"].value_counts()
    fig.add_trace(
        go.Bar(
            x=trend_counts.index,
            y=trend_counts.values,
            name="Market Trends",
            marker_color="lightgreen"
        ),
        row=2, col=2
    )

    fig.update_layout(
        height=800,
        title_text="Property Appreciation Forecasts Analysis",
        showlegend=False
    )

    return fig


@monitor_performance("predictive_dashboard_market_timing_chart")
def create_market_timing_heatmap(market_timing: Dict[str, Any]) -> go.Figure:
    """Create market timing heatmap visualization."""

    if not market_timing:
        fig = go.Figure()
        fig.add_annotation(text="No market timing data available",
                          xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    counties = list(market_timing.keys())
    metrics = ["price_momentum", "volatility", "confidence"]

    # Create heatmap data
    heatmap_data = []
    for metric in metrics:
        row = []
        for county in counties:
            value = market_timing[county].get(metric, 0)
            row.append(value)
        heatmap_data.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=counties,
        y=metrics,
        colorscale="RdYlBu_r",
        hoverongaps=False,
        hovertemplate="<b>%{x}</b><br>" +
                     "%{y}: %{z:.2f}<br>" +
                     "<extra></extra>"
    ))

    fig.update_layout(
        title="Market Timing Analysis by County",
        xaxis_title="County",
        yaxis_title="Market Metrics",
        height=400
    )

    return fig


@monitor_performance("predictive_dashboard_opportunities_display")
def display_emerging_opportunities(opportunities: List[Dict]) -> None:
    """Display emerging opportunities in an interactive format."""

    if not opportunities:
        st.warning("No emerging opportunities detected in current dataset.")
        return

    st.subheader(f"🎯 Top {len(opportunities)} Emerging Opportunities")

    # Create opportunities DataFrame
    df = pd.DataFrame(opportunities)

    # Sort by opportunity score
    df = df.sort_values("score", ascending=False)

    # Display in expandable cards
    for i, (_, opp) in enumerate(df.head(10).iterrows(), 1):
        with st.expander(f"#{i} {opp['county']} County - {opp['opportunity_type'].replace('_', ' ').title()} (Score: {opp['score']:.1f})"):

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Potential Appreciation",
                    f"{opp['potential_appreciation']:.1%}",
                    delta=f"Timeline: {opp['timeline_months']} months"
                )

            with col2:
                st.metric(
                    "Risk-Adjusted Return",
                    f"{opp['risk_adjusted_return']:.1%}",
                    delta=f"Confidence: {opp['confidence']}"
                )

            with col3:
                st.metric(
                    "Opportunity Score",
                    f"{opp['score']:.1f}/100",
                    delta=f"Type: {opp['opportunity_type']}"
                )

            if opp['primary_drivers']:
                st.write("**Primary Drivers:**")
                for driver in opp['primary_drivers']:
                    st.write(f"• {driver}")

            if opp['risk_factors']:
                st.write("**Risk Factors:**")
                for risk in opp['risk_factors']:
                    st.write(f"⚠️ {risk}")


@monitor_performance("predictive_analytics_dashboard")
def display_predictive_analytics_dashboard(properties_data: List[Dict]) -> None:
    """
    Main function to display the predictive analytics dashboard.

    Args:
        properties_data: List of property data from the main application
    """

    st.title("🔮 Market Intelligence Dashboard")
    st.markdown("Advanced predictive analytics for Alabama property investments")

    # Load analytics data
    with st.spinner("Generating market intelligence predictions..."):
        analytics_data = load_predictive_analytics_data(properties_data)

    if not analytics_data["appreciation_forecasts"]:
        st.error("Unable to generate predictive analytics. Please ensure property data is available.")
        return

    # Display performance metrics
    metrics = analytics_data["performance_metrics"]
    if metrics:
        st.subheader("📊 Analytics Overview")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Properties Analyzed",
                f"{metrics['total_properties_analyzed']:,}"
            )

        with col2:
            st.metric(
                "Avg 3-Year Appreciation",
                f"{metrics['avg_3yr_appreciation']:.1%}",
                delta=f"Max: {metrics['max_3yr_appreciation']:.1%}"
            )

        with col3:
            st.metric(
                "High Confidence Predictions",
                f"{metrics['high_confidence_pct']:.1f}%",
                delta=f"Low Risk Properties: {metrics['low_risk_properties']}"
            )

        with col4:
            st.metric(
                "Average Risk Score",
                f"{metrics['avg_risk_score']:.2f}",
                delta="Lower is better"
            )

    # Create tabs for different analytics views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Appreciation Forecasts",
        "⏰ Market Timing",
        "💎 Emerging Opportunities",
        "🗺️ County Insights"
    ])

    with tab1:
        st.subheader("Property Appreciation Forecasts")
        if analytics_data["appreciation_forecasts"]:
            fig = create_appreciation_forecast_chart(analytics_data["appreciation_forecasts"])
            st.plotly_chart(fig, use_container_width=True)

            # Show detailed forecast table
            with st.expander("View Detailed Forecasts"):
                df = pd.DataFrame(analytics_data["appreciation_forecasts"])
                st.dataframe(
                    df[["county", "current_score", "one_year", "three_year", "five_year", "confidence", "risk_score"]],
                    use_container_width=True
                )

    with tab2:
        st.subheader("Market Timing Analysis")
        if analytics_data["market_timing"]:
            fig = create_market_timing_heatmap(analytics_data["market_timing"])
            st.plotly_chart(fig, use_container_width=True)

            # Show market phases
            st.subheader("Current Market Phases by County")
            for county, timing in analytics_data["market_timing"].items():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**{county}**")
                with col2:
                    phase_color = {
                        "buyer_market": "🟢",
                        "seller_market": "🔴",
                        "balanced": "🟡"
                    }
                    st.write(f"{phase_color.get(timing['market_phase'], '⚪')} {timing['market_phase'].replace('_', ' ').title()}")
                with col3:
                    st.write(f"Buy: {timing['buy_window'][0]}-{timing['buy_window'][1]}")

    with tab3:
        display_emerging_opportunities(analytics_data["opportunities"])

    with tab4:
        st.subheader("County Intelligence Summary")
        county_insights = analytics_data["county_insights"]

        if county_insights:
            # Create county comparison chart
            county_df = pd.DataFrame.from_dict(county_insights, orient="index").reset_index()
            county_df.columns = ["County"] + list(county_df.columns[1:])

            fig = px.scatter(
                county_df,
                x="avg_risk",
                y="avg_appreciation_3yr",
                size="property_count",
                color="market_phase",
                hover_name="County",
                title="County Risk vs Appreciation Analysis",
                labels={
                    "avg_risk": "Average Risk Score",
                    "avg_appreciation_3yr": "Average 3-Year Appreciation",
                    "property_count": "Property Count"
                }
            )

            st.plotly_chart(fig, use_container_width=True)

            # Show county rankings
            st.subheader("County Rankings")
            county_df_sorted = county_df.sort_values("avg_appreciation_3yr", ascending=False)
            st.dataframe(county_df_sorted, use_container_width=True)

    # Add refresh button
    if st.button("🔄 Refresh Predictions", type="primary"):
        st.cache_data.clear()
        st.rerun()

    # Display generation timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# Export the main function for easy import
__all__ = ["display_predictive_analytics_dashboard"]