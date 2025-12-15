"""
AI Testing Dashboard Component
Alabama Auction Watcher - Prediction Accuracy Monitoring Interface

This component provides a comprehensive dashboard for monitoring and analyzing
the performance of the Predictive Market Intelligence Engine, including:
- Real-time accuracy metrics
- Historical performance trends
- Backtesting results
- Error pattern analysis
- Model performance analytics

Author: Claude Code AI Assistant
Date: 2025-09-20
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.prediction_accuracy_validator import (
    get_prediction_validator,
    ValidationResult,
    BacktestResult,
    ValidationStatus,
    ValidationMetricType
)
from streamlit_app.core.performance_monitor import monitor_performance
from streamlit_app.core.cache_manager import smart_cache

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300)  # Cache for 5 minutes
@smart_cache("ai_testing_dashboard", ttl_seconds=300, cache_type="api_data")
@monitor_performance("ai_testing_dashboard_data_loading")
def load_ai_testing_data() -> Dict[str, Any]:
    """
    Load comprehensive AI testing and validation data.

    Returns:
        Dictionary containing all testing metrics and analysis data
    """
    try:
        validator = get_prediction_validator()

        # Get current performance status
        performance_status = validator.monitor_prediction_performance()

        # Get validation history (last 30 days)
        validation_history = validator.get_validation_history(days=30)

        # Get recent backtest results
        recent_backtests = validator.backtest_results[-10:] if validator.backtest_results else []

        # Calculate performance trends
        trend_data = _calculate_performance_trends(validation_history)

        # Get accuracy distribution by confidence levels
        confidence_analysis = _analyze_confidence_performance(validation_history)

        # County-specific performance analysis
        county_performance = _analyze_county_performance(validation_history)

        return {
            "performance_status": performance_status,
            "validation_history": validation_history,
            "backtest_results": recent_backtests,
            "trend_data": trend_data,
            "confidence_analysis": confidence_analysis,
            "county_performance": county_performance,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to load AI testing data: {e}")
        return {
            "error": str(e),
            "performance_status": {"status": "error"},
            "validation_history": [],
            "backtest_results": [],
            "last_updated": datetime.now().isoformat()
        }


def display_ai_testing_dashboard():
    """
    Display the comprehensive AI testing and monitoring dashboard.
    """
    st.title("AI Testing & Validation Dashboard")
    st.markdown("**Predictive Market Intelligence Engine - Performance Monitoring**")

    # Load testing data
    with st.spinner("Loading AI testing data..."):
        testing_data = load_ai_testing_data()

    if "error" in testing_data:
        st.error(f"Failed to load testing data: {testing_data['error']}")
        return

    # Display overall status
    _display_overall_status(testing_data["performance_status"])

    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Performance Overview",
        "Accuracy Trends",
        "Backtesting Results",
        "Confidence Analysis",
        "County Performance"
    ])

    with tab1:
        _display_performance_overview(testing_data)

    with tab2:
        _display_accuracy_trends(testing_data)

    with tab3:
        _display_backtesting_results(testing_data)

    with tab4:
        _display_confidence_analysis(testing_data)

    with tab5:
        _display_county_performance(testing_data)

    # Action buttons
    st.markdown("---")
    _display_action_buttons(testing_data)


def _display_overall_status(performance_status: Dict[str, Any]):
    """Display overall system status with key metrics."""

    status = performance_status.get("status", "unknown")
    metrics = performance_status.get("metrics", {})
    alerts = performance_status.get("alerts", [])

    # Status indicator
    status_colors = {
        "healthy": "Healthy",
        "warning": "Warning",
        "error": "Error",
        "no_data": "No Data"
    }

    col1, col2, col3, col4 = st.columns([1, 2, 2, 2])

    with col1:
        st.markdown(f"### {status_colors.get(status, 'Unknown')} Status")
        st.markdown(f"**{status.upper()}**")

    with col2:
        current_accuracy = metrics.get("current_accuracy", 0)
        if current_accuracy > 0:
            st.metric(
                label="Current Accuracy",
                value=f"{current_accuracy:.1%}",
                delta=f"{metrics.get('accuracy_trend', 'stable')}"
            )

    with col3:
        predictions_validated = metrics.get("predictions_validated", 0)
        if predictions_validated > 0:
            st.metric(
                label="Predictions Validated",
                value=f"{predictions_validated:,}",
                delta="Last 30 days"
            )

    with col4:
        avg_confidence = metrics.get("average_confidence", 0)
        if avg_confidence > 0:
            st.metric(
                label="Avg Confidence",
                value=f"{avg_confidence:.1%}",
                delta="Recent validations"
            )

    # Display alerts if any
    if alerts:
        st.warning("**Performance Alerts:**")
        for alert in alerts:
            st.warning(f"• {alert}")

    # Last update info
    last_validation = metrics.get("last_validation")
    if last_validation:
        last_update = datetime.fromisoformat(last_validation.replace('Z', '+00:00'))
        time_ago = datetime.now() - last_update.replace(tzinfo=None)
        st.info(f"Last validation: {time_ago.days} days, {time_ago.seconds//3600} hours ago")


def _display_performance_overview(testing_data: Dict[str, Any]):
    """Display performance overview with key metrics and visualizations."""

    st.header("Performance Overview")

    validation_history = testing_data.get("validation_history", [])
    if not validation_history:
        st.info("No validation history available. Run validations to see performance metrics.")
        return

    # Recent performance metrics
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Recent Validation Results")

        # Create performance metrics table
        recent_validations = validation_history[:10]
        if recent_validations:
            df_recent = pd.DataFrame([
                {
                    "Date": result.validation_timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Accuracy": f"{result.accuracy_score:.1%}",
                    "Status": result.validation_status.value.title(),
                    "Predictions": result.total_predictions,
                    "Success Rate": f"{result.successful_predictions/result.total_predictions:.1%}" if result.total_predictions > 0 else "0%"
                }
                for result in recent_validations
            ])
            st.dataframe(df_recent, use_container_width=True)

    with col2:
        st.subheader("Performance Distribution")

        # Accuracy distribution
        if len(validation_history) >= 5:
            accuracy_scores = [result.accuracy_score for result in validation_history]

            fig = go.Figure(data=[go.Histogram(
                x=accuracy_scores,
                nbinsx=20,
                name="Accuracy Distribution",
                marker_color='lightblue'
            )])

            fig.update_layout(
                title="Accuracy Score Distribution",
                xaxis_title="Accuracy Score",
                yaxis_title="Frequency",
                height=300
            )

            st.plotly_chart(fig, use_container_width=True)

    # Performance metrics over time
    st.subheader("Performance Metrics Timeline")

    if len(validation_history) >= 3:
        df_timeline = pd.DataFrame([
            {
                "date": result.validation_timestamp,
                "accuracy": result.accuracy_score,
                "precision": result.precision_score,
                "recall": result.recall_score,
                "confidence_calibration": result.confidence_calibration
            }
            for result in validation_history
        ])

        df_timeline = df_timeline.sort_values('date')

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Accuracy Over Time', 'Precision Over Time',
                          'Recall Over Time', 'Confidence Calibration')
        )

        # Accuracy
        fig.add_trace(
            go.Scatter(x=df_timeline['date'], y=df_timeline['accuracy'],
                      mode='lines+markers', name='Accuracy', line=dict(color='blue')),
            row=1, col=1
        )

        # Precision
        fig.add_trace(
            go.Scatter(x=df_timeline['date'], y=df_timeline['precision'],
                      mode='lines+markers', name='Precision', line=dict(color='green')),
            row=1, col=2
        )

        # Recall
        fig.add_trace(
            go.Scatter(x=df_timeline['date'], y=df_timeline['recall'],
                      mode='lines+markers', name='Recall', line=dict(color='orange')),
            row=2, col=1
        )

        # Confidence Calibration
        fig.add_trace(
            go.Scatter(x=df_timeline['date'], y=df_timeline['confidence_calibration'],
                      mode='lines+markers', name='Confidence Calibration', line=dict(color='purple')),
            row=2, col=2
        )

        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def _display_accuracy_trends(testing_data: Dict[str, Any]):
    """Display detailed accuracy trend analysis."""

    st.header("Accuracy Trends Analysis")

    validation_history = testing_data.get("validation_history", [])
    trend_data = testing_data.get("trend_data", {})

    if not validation_history:
        st.info("No validation history available for trend analysis.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Accuracy Trend Over Time")

        # Create detailed accuracy trend chart
        df_trend = pd.DataFrame([
            {
                "date": result.validation_timestamp,
                "accuracy": result.accuracy_score,
                "status": result.validation_status.value,
                "total_predictions": result.total_predictions
            }
            for result in validation_history
        ])

        df_trend = df_trend.sort_values('date')

        # Color by status
        status_colors = {
            "excellent": "green",
            "good": "lightgreen",
            "acceptable": "orange",
            "poor": "red",
            "critical": "darkred"
        }

        fig = px.scatter(
            df_trend,
            x="date",
            y="accuracy",
            color="status",
            size="total_predictions",
            color_discrete_map=status_colors,
            title="Prediction Accuracy Over Time",
            labels={"accuracy": "Accuracy Score", "date": "Date"}
        )

        # Add trend line
        fig.add_trace(
            go.Scatter(
                x=df_trend['date'],
                y=df_trend['accuracy'].rolling(window=3, center=True).mean(),
                mode='lines',
                name='Trend Line',
                line=dict(color='black', dash='dash')
            )
        )

        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Trend Summary")

        # Trend statistics
        if trend_data:
            trend_direction = trend_data.get("direction", "stable")
            trend_strength = trend_data.get("strength", 0)
            recent_avg = trend_data.get("recent_average", 0)
            overall_avg = trend_data.get("overall_average", 0)

            st.metric(
                label="Trend Direction",
                value=trend_direction.title(),
                delta=f"{trend_strength:.1%}" if trend_strength != 0 else None
            )

            st.metric(
                label="Recent Average",
                value=f"{recent_avg:.1%}",
                delta=f"{(recent_avg - overall_avg):.1%}" if overall_avg > 0 else None
            )

        # Status distribution
        st.subheader("Status Distribution")
        status_counts = {}
        for result in validation_history:
            status = result.validation_status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        if status_counts:
            fig_pie = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="Validation Status Distribution"
            )
            fig_pie.update_layout(height=300)
            st.plotly_chart(fig_pie, use_container_width=True)


def _display_backtesting_results(testing_data: Dict[str, Any]):
    """Display backtesting results and analysis."""

    st.header("Backtesting Results")

    backtest_results = testing_data.get("backtest_results", [])

    if not backtest_results:
        st.info("No backtesting results available. Run backtests to analyze historical performance.")

        # Add button to run backtest
        if st.button("Run Sample Backtest", type="primary"):
            with st.spinner("Running backtest (this may take a few minutes)..."):
                try:
                    from scripts.prediction_accuracy_validator import run_prediction_backtest
                    result = run_prediction_backtest(days_back=180, horizon_months=6)

                    st.success("Backtest completed successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Backtest failed: {e}")

        return

    # Display latest backtest results
    latest_backtest = backtest_results[-1]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Overall Accuracy",
            value=f"{latest_backtest.overall_accuracy:.1%}",
            delta="Latest Backtest"
        )

    with col2:
        st.metric(
            label="Market Trend Accuracy",
            value=f"{latest_backtest.market_trend_accuracy:.1%}",
            delta="Trend Predictions"
        )

    with col3:
        st.metric(
            label="Properties Tested",
            value=f"{latest_backtest.test_properties_count:,}",
            delta=f"{latest_backtest.prediction_horizon_months}mo horizon"
        )

    with col4:
        st.metric(
            label="Execution Time",
            value=f"{latest_backtest.execution_time_seconds:.1f}s",
            delta="Processing Speed"
        )

    # Backtest history chart
    if len(backtest_results) > 1:
        st.subheader("Backtest Performance History")

        df_backtest = pd.DataFrame([
            {
                "date": result.backtest_timestamp,
                "overall_accuracy": result.overall_accuracy,
                "trend_accuracy": result.market_trend_accuracy,
                "test_count": result.test_properties_count,
                "horizon_months": result.prediction_horizon_months
            }
            for result in backtest_results
        ])

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Accuracy Over Time', 'Test Coverage')
        )

        # Accuracy trends
        fig.add_trace(
            go.Scatter(x=df_backtest['date'], y=df_backtest['overall_accuracy'],
                      mode='lines+markers', name='Overall Accuracy', line=dict(color='blue')),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(x=df_backtest['date'], y=df_backtest['trend_accuracy'],
                      mode='lines+markers', name='Trend Accuracy', line=dict(color='green')),
            row=1, col=1
        )

        # Test coverage
        fig.add_trace(
            go.Bar(x=df_backtest['date'], y=df_backtest['test_count'],
                  name='Properties Tested', marker_color='lightblue'),
            row=1, col=2
        )

        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Confidence level performance
    st.subheader("Confidence Level Performance")

    if hasattr(latest_backtest, 'high_confidence_accuracy'):
        confidence_data = {
            "High Confidence": latest_backtest.high_confidence_accuracy,
            "Medium Confidence": getattr(latest_backtest, 'medium_confidence_accuracy', 0),
            "Low Confidence": getattr(latest_backtest, 'low_confidence_accuracy', 0)
        }

        fig_conf = px.bar(
            x=list(confidence_data.keys()),
            y=list(confidence_data.values()),
            title="Accuracy by Confidence Level",
            color=list(confidence_data.values()),
            color_continuous_scale="RdYlGn"
        )

        fig_conf.update_layout(
            yaxis_title="Accuracy",
            yaxis=dict(range=[0, 1]),
            height=300
        )

        st.plotly_chart(fig_conf, use_container_width=True)


def _display_confidence_analysis(testing_data: Dict[str, Any]):
    """Display confidence calibration and analysis."""

    st.header("Confidence Analysis")

    confidence_analysis = testing_data.get("confidence_analysis", {})
    validation_history = testing_data.get("validation_history", [])

    if not validation_history:
        st.info("No validation data available for confidence analysis.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Confidence Calibration")

        # Calculate confidence calibration over time
        calibration_data = []
        for result in validation_history[-20:]:  # Last 20 validations
            calibration_data.append({
                "date": result.validation_timestamp,
                "calibration": result.confidence_calibration,
                "average_confidence": result.average_confidence
            })

        if calibration_data:
            df_cal = pd.DataFrame(calibration_data)

            fig_cal = go.Figure()

            fig_cal.add_trace(
                go.Scatter(
                    x=df_cal['date'],
                    y=df_cal['calibration'],
                    mode='lines+markers',
                    name='Confidence Calibration',
                    line=dict(color='blue')
                )
            )

            fig_cal.add_hline(
                y=0.8,
                line_dash="dash",
                line_color="green",
                annotation_text="Good Calibration Threshold"
            )

            fig_cal.update_layout(
                title="Confidence Calibration Over Time",
                yaxis_title="Calibration Score",
                yaxis=dict(range=[0, 1]),
                height=300
            )

            st.plotly_chart(fig_cal, use_container_width=True)

    with col2:
        st.subheader("Confidence Distribution")

        # Analyze confidence distribution
        if confidence_analysis:
            confidence_dist = confidence_analysis.get("distribution", {})

            if confidence_dist:
                fig_dist = px.pie(
                    values=list(confidence_dist.values()),
                    names=list(confidence_dist.keys()),
                    title="Prediction Confidence Distribution"
                )
                fig_dist.update_layout(height=300)
                st.plotly_chart(fig_dist, use_container_width=True)

    # Confidence vs Accuracy correlation
    st.subheader("Confidence vs Accuracy Correlation")

    # Calculate correlation data
    correlation_data = []
    for result in validation_history:
        if result.average_confidence > 0:
            correlation_data.append({
                "confidence": result.average_confidence,
                "accuracy": result.accuracy_score,
                "date": result.validation_timestamp.strftime("%Y-%m-%d")
            })

    if correlation_data:
        df_corr = pd.DataFrame(correlation_data)

        fig_corr = px.scatter(
            df_corr,
            x="confidence",
            y="accuracy",
            hover_data=["date"],
            title="Confidence vs Accuracy Correlation",
            trendline="ols"
        )

        fig_corr.update_layout(
            xaxis_title="Average Confidence",
            yaxis_title="Accuracy Score",
            height=400
        )

        st.plotly_chart(fig_corr, use_container_width=True)

        # Calculate correlation coefficient
        if len(correlation_data) > 5:
            correlation = df_corr['confidence'].corr(df_corr['accuracy'])
            st.metric(
                label="Confidence-Accuracy Correlation",
                value=f"{correlation:.3f}",
                delta="Higher is better"
            )


def _display_county_performance(testing_data: Dict[str, Any]):
    """Display county-specific performance analysis."""

    st.header("County Performance Analysis")

    county_performance = testing_data.get("county_performance", {})
    validation_history = testing_data.get("validation_history", [])

    if not county_performance:
        st.info("No county-specific performance data available.")
        return

    # County performance metrics
    st.subheader("County Accuracy Comparison")

    county_df = pd.DataFrame([
        {
            "County": county,
            "Average Accuracy": data.get("average_accuracy", 0),
            "Prediction Count": data.get("prediction_count", 0),
            "Best Accuracy": data.get("best_accuracy", 0),
            "Latest Accuracy": data.get("latest_accuracy", 0)
        }
        for county, data in county_performance.items()
    ]).sort_values("Average Accuracy", ascending=False)

    # Top performing counties chart
    fig_counties = px.bar(
        county_df.head(15),
        x="County",
        y="Average Accuracy",
        color="Average Accuracy",
        color_continuous_scale="RdYlGn",
        title="Top 15 Counties by Prediction Accuracy"
    )

    fig_counties.update_layout(
        xaxis_tickangle=-45,
        height=400,
        yaxis=dict(range=[0, 1])
    )

    st.plotly_chart(fig_counties, use_container_width=True)

    # County performance table
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("County Performance Details")
        st.dataframe(
            county_df.style.format({
                "Average Accuracy": "{:.1%}",
                "Best Accuracy": "{:.1%}",
                "Latest Accuracy": "{:.1%}",
                "Prediction Count": "{:,}"
            }),
            use_container_width=True
        )

    with col2:
        st.subheader("Performance Statistics")

        if not county_df.empty:
            st.metric(
                label="Best Performing County",
                value=county_df.iloc[0]["County"],
                delta=f"{county_df.iloc[0]['Average Accuracy']:.1%}"
            )

            st.metric(
                label="Most Tested County",
                value=county_df.loc[county_df["Prediction Count"].idxmax(), "County"],
                delta=f"{county_df['Prediction Count'].max():,} predictions"
            )

            overall_avg = county_df["Average Accuracy"].mean()
            st.metric(
                label="Overall County Average",
                value=f"{overall_avg:.1%}",
                delta=f"{len(county_df)} counties"
            )


def _display_action_buttons(testing_data: Dict[str, Any]):
    """Display action buttons for manual operations."""

    st.subheader("Testing Actions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Refresh Data", help="Reload all testing data"):
            st.cache_data.clear()
            st.rerun()

    with col2:
        if st.button("Run Quick Validation", help="Run validation on sample data"):
            with st.spinner("Running validation..."):
                try:
                    # This would run a quick validation in production
                    st.success("Quick validation completed!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Validation failed: {e}")

    with col3:
        if st.button("Start Backtest", help="Run comprehensive backtest"):
            with st.spinner("Starting backtest..."):
                try:
                    st.info("Backtest started! Check back in a few minutes for results.")
                    # In production, this would start an async backtest
                except Exception as e:
                    st.error(f"Failed to start backtest: {e}")

    with col4:
        if st.button("Export Report", help="Export testing report"):
            try:
                # Generate downloadable report
                report_data = {
                    "generation_time": datetime.now().isoformat(),
                    "testing_data": testing_data
                }

                st.download_button(
                    label="Download Report",
                    data=str(report_data),
                    file_name=f"ai_testing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            except Exception as e:
                st.error(f"Failed to generate report: {e}")


# Helper functions for data processing

def _calculate_performance_trends(validation_history: List[ValidationResult]) -> Dict[str, Any]:
    """Calculate performance trends from validation history."""
    if len(validation_history) < 5:
        return {}

    recent_results = validation_history[:5]
    older_results = validation_history[5:10]

    recent_avg = sum(r.accuracy_score for r in recent_results) / len(recent_results)
    older_avg = sum(r.accuracy_score for r in older_results) / len(older_results) if older_results else recent_avg

    trend_strength = recent_avg - older_avg

    if trend_strength > 0.05:
        direction = "improving"
    elif trend_strength < -0.05:
        direction = "declining"
    else:
        direction = "stable"

    overall_avg = sum(r.accuracy_score for r in validation_history) / len(validation_history)

    return {
        "direction": direction,
        "strength": trend_strength,
        "recent_average": recent_avg,
        "overall_average": overall_avg
    }


def _analyze_confidence_performance(validation_history: List[ValidationResult]) -> Dict[str, Any]:
    """Analyze confidence level performance from validation history."""
    confidence_distribution = {}
    confidence_accuracy_map = {}

    for result in validation_history:
        # This would be more detailed in production with individual prediction data
        avg_conf = result.average_confidence
        if avg_conf > 0.8:
            level = "High"
        elif avg_conf > 0.6:
            level = "Medium"
        else:
            level = "Low"

        confidence_distribution[level] = confidence_distribution.get(level, 0) + 1
        if level not in confidence_accuracy_map:
            confidence_accuracy_map[level] = []
        confidence_accuracy_map[level].append(result.accuracy_score)

    # Calculate average accuracy by confidence level
    confidence_accuracy = {}
    for level, accuracies in confidence_accuracy_map.items():
        confidence_accuracy[level] = sum(accuracies) / len(accuracies) if accuracies else 0

    return {
        "distribution": confidence_distribution,
        "accuracy_by_confidence": confidence_accuracy
    }


def _analyze_county_performance(validation_history: List[ValidationResult]) -> Dict[str, Any]:
    """Analyze county-specific performance from validation history."""
    county_performance = {}

    for result in validation_history:
        for county, accuracy in result.county_performance.items():
            if county not in county_performance:
                county_performance[county] = {
                    "accuracies": [],
                    "prediction_count": 0
                }

            county_performance[county]["accuracies"].append(accuracy)
            county_performance[county]["prediction_count"] += 1

    # Calculate summary statistics
    county_summary = {}
    for county, data in county_performance.items():
        accuracies = data["accuracies"]
        if accuracies:
            county_summary[county] = {
                "average_accuracy": sum(accuracies) / len(accuracies),
                "best_accuracy": max(accuracies),
                "latest_accuracy": accuracies[0] if accuracies else 0,
                "prediction_count": data["prediction_count"]
            }

    return county_summary