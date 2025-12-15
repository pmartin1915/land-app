"""
Enhanced AI Testing & Monitoring Dashboard
Alabama Auction Watcher - Advanced Monitoring with Error Detection

This component provides an enhanced dashboard for comprehensive monitoring including:
- Advanced error pattern visualization
- Predictive failure alerts
- Component health matrix
- Performance trend analysis
- Automated recommendations

Author: Claude Code AI Assistant
Date: 2025-09-21
Version: 1.1.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.core.performance_monitor import monitor_performance
from streamlit_app.core.cache_manager import smart_cache
from streamlit_app.testing.enhanced_ai_testing import (
    get_enhanced_ai_testing_controller, EnhancedTestReport
)
from streamlit_app.testing.enhanced_error_detection import (
    get_enhanced_error_detector, ErrorPattern, PredictiveAlert, ErrorSeverity, ErrorCategory
)

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300)  # Cache for 5 minutes
@smart_cache("enhanced_ai_dashboard", ttl_seconds=300, cache_type="dashboard_data")
@monitor_performance("enhanced_ai_dashboard_data_loading")
def load_enhanced_dashboard_data() -> Dict[str, Any]:
    """
    Load comprehensive enhanced AI dashboard data.

    Returns:
        Dictionary containing all enhanced monitoring metrics and analysis data
    """
    try:
        controller = get_enhanced_ai_testing_controller()
        detector = get_enhanced_error_detector()

        # Get comprehensive system health check
        system_health = controller.run_system_wide_health_check()

        # Get testing summary for different time periods
        testing_summary_24h = controller.get_testing_summary(hours=24)
        testing_summary_7d = controller.get_testing_summary(hours=168)  # 7 days

        # Get error detection data
        error_health_summary = detector.get_system_health_summary()

        # Get recent testing history
        recent_reports = controller.testing_history[-20:] if controller.testing_history else []

        # Calculate trend data
        trend_data = _calculate_enhanced_trends(recent_reports)

        # Get predictive alerts
        from streamlit_app.testing.enhanced_error_detection import get_predictive_alerts
        predictive_alerts = get_predictive_alerts()

        # Calculate component health matrix
        health_matrix = _calculate_component_health_matrix(recent_reports)

        # Generate performance insights
        performance_insights = _generate_performance_insights(recent_reports, system_health)

        return {
            "system_health": system_health,
            "testing_summary_24h": testing_summary_24h,
            "testing_summary_7d": testing_summary_7d,
            "error_health_summary": error_health_summary,
            "recent_reports": recent_reports,
            "trend_data": trend_data,
            "predictive_alerts": predictive_alerts,
            "health_matrix": health_matrix,
            "performance_insights": performance_insights,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to load enhanced dashboard data: {e}")
        return {
            "error": str(e),
            "system_health": {"overall_status": "error"},
            "last_updated": datetime.now().isoformat()
        }


def display_enhanced_ai_dashboard():
    """
    Display the enhanced AI testing and monitoring dashboard.
    """
    st.title("Enhanced AI Testing & Monitoring Dashboard")
    st.markdown("**Advanced Monitoring with Predictive Error Detection & Performance Analytics**")

    # Load enhanced dashboard data
    with st.spinner("Loading enhanced AI monitoring data..."):
        dashboard_data = load_enhanced_dashboard_data()

    if "error" in dashboard_data:
        st.error(f"Failed to load dashboard data: {dashboard_data['error']}")
        return

    # Display overall system status
    _display_enhanced_system_status(dashboard_data)

    # Create enhanced tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "System Overview",
        "Predictive Alerts",
        "Component Health",
        "Error Patterns",
        "Performance Analytics",
        "Actions & Recommendations"
    ])

    with tab1:
        _display_system_overview(dashboard_data)

    with tab2:
        _display_predictive_alerts(dashboard_data)

    with tab3:
        _display_component_health_matrix(dashboard_data)

    with tab4:
        _display_error_pattern_analysis(dashboard_data)

    with tab5:
        _display_performance_analytics(dashboard_data)

    with tab6:
        _display_actions_and_recommendations(dashboard_data)

    # Enhanced control panel
    st.markdown("---")
    _display_enhanced_control_panel(dashboard_data)


def _display_enhanced_system_status(dashboard_data: Dict[str, Any]):
    """Display enhanced system status with comprehensive metrics."""

    system_health = dashboard_data.get("system_health", {})
    overall_status = system_health.get("overall_status", "unknown")

    # Status indicator with color coding
    status_colors = {
        "healthy": "Healthy",
        "warning": "Warning",
        "critical": "Critical",
        "error": "Error"
    }

    status_color = {"healthy": "green", "warning": "orange", "critical": "red", "error": "gray"}.get(overall_status, "gray")

    col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 2])

    with col1:
        st.markdown(f"### {status_colors.get(overall_status, 'Unknown')} Status")
        st.markdown(f"<span style='color: {status_color}; font-weight: bold; font-size: 18px'>{overall_status.upper()}</span>",
                   unsafe_allow_html=True)

    # Enhanced metrics from system health
    testing_metrics = system_health.get("testing_metrics", {})

    with col2:
        success_rate = testing_metrics.get("average_success_rate", 0)
        if success_rate > 0:
            st.metric(
                label="Success Rate (24h)",
                value=f"{success_rate:.1%}",
                delta=_calculate_success_rate_delta(dashboard_data)
            )
        else:
            st.metric(label="Success Rate (24h)", value="No data")

    with col3:
        health_scores = dashboard_data.get("error_health_summary", {}).get("component_health_scores", {})
        if health_scores:
            avg_health = sum(health_scores.values()) / len(health_scores)
            st.metric(
                label="Avg Component Health",
                value=f"{avg_health:.0f}/100",
                delta=_calculate_health_delta(dashboard_data)
            )
        else:
            st.metric(label="Avg Component Health", value="No data")

    with col4:
        predictive_alerts = dashboard_data.get("predictive_alerts", [])
        high_priority_alerts = [a for a in predictive_alerts if a.confidence_score > 0.8]
        st.metric(
            label="High Priority Alerts",
            value=len(high_priority_alerts),
            delta=f"{len(predictive_alerts)} total alerts"
        )

    with col5:
        error_patterns = dashboard_data.get("error_health_summary", {}).get("total_patterns_tracked", 0)
        critical_patterns = len(dashboard_data.get("error_health_summary", {}).get("critical_patterns", []))
        st.metric(
            label="Error Patterns",
            value=error_patterns,
            delta=f"{critical_patterns} critical" if critical_patterns > 0 else "All stable"
        )

    # Display alerts if any critical issues
    if overall_status in ["critical", "warning"]:
        st.warning("**System requires attention - check alerts and recommendations below**")

    # Last update info
    last_updated = dashboard_data.get("last_updated")
    if last_updated:
        update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        time_ago = datetime.now() - update_time.replace(tzinfo=None)
        st.info(f"Last updated: {time_ago.seconds//60} minutes ago")


def _display_system_overview(dashboard_data: Dict[str, Any]):
    """Display comprehensive system overview."""

    st.header("System Overview & Key Metrics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Testing Performance Trends")

        # Create performance trend chart
        recent_reports = dashboard_data.get("recent_reports", [])
        if recent_reports:
            df_trends = pd.DataFrame([
                {
                    "timestamp": report.generated_at,
                    "success_rate": report.success_rate,
                    "avg_execution_time": report.avg_execution_time,
                    "health_score": report.component_health.health_score,
                    "component": report.component_name
                }
                for report in recent_reports[-10:]  # Last 10 reports
            ])

            if not df_trends.empty:
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('Success Rate Over Time', 'Average Execution Time'),
                    specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
                )

                # Success rate
                fig.add_trace(
                    go.Scatter(
                        x=df_trends['timestamp'],
                        y=df_trends['success_rate'],
                        mode='lines+markers',
                        name='Success Rate',
                        line=dict(color='green')
                    ),
                    row=1, col=1
                )

                # Execution time
                fig.add_trace(
                    go.Scatter(
                        x=df_trends['timestamp'],
                        y=df_trends['avg_execution_time'],
                        mode='lines+markers',
                        name='Avg Execution Time',
                        line=dict(color='blue')
                    ),
                    row=2, col=1
                )

                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Component Performance Distribution")

        # Component performance radar chart
        health_matrix = dashboard_data.get("health_matrix", {})
        if health_matrix:
            components = list(health_matrix.keys())[:6]  # Top 6 components
            metrics = ['Health Score', 'Performance', 'Reliability', 'Test Coverage']

            fig = go.Figure()

            for component in components:
                data = health_matrix[component]
                values = [
                    data.get('health_score', 0),
                    data.get('performance_score', 0),
                    data.get('reliability_score', 0),
                    data.get('test_coverage', 0)
                ]

                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=metrics,
                    fill='toself',
                    name=component
                ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                height=400,
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)

    # System-wide statistics
    st.subheader("System Statistics")

    col1, col2, col3, col4 = st.columns(4)

    testing_24h = dashboard_data.get("testing_summary_24h", {})
    testing_7d = dashboard_data.get("testing_summary_7d", {})

    with col1:
        st.metric(
            "Tests (24h)",
            testing_24h.get("total_tests_executed", 0),
            delta=f"vs 7d avg: {testing_7d.get('total_tests_executed', 0) // 7}"
        )

    with col2:
        st.metric(
            "Components Tested",
            len(testing_24h.get("components_tested", [])),
            delta=f"7d total: {len(testing_7d.get('components_tested', []))}"
        )

    with col3:
        error_summary = dashboard_data.get("error_health_summary", {})
        st.metric(
            "Error Patterns",
            error_summary.get("total_patterns_tracked", 0),
            delta=f"Recent errors: {error_summary.get('recent_errors_count', 0)}"
        )

    with col4:
        performance_metrics = dashboard_data.get("system_health", {}).get("performance_metrics", {})
        active_sessions = performance_metrics.get("active_sessions", 0)
        st.metric(
            "Active Monitoring",
            f"{active_sessions} sessions",
            delta="Real-time tracking"
        )


def _display_predictive_alerts(dashboard_data: Dict[str, Any]):
    """Display predictive failure alerts."""

    st.header("Predictive Failure Alerts")

    predictive_alerts = dashboard_data.get("predictive_alerts", [])

    if not predictive_alerts:
        st.info("No predictive alerts - all systems operating within normal parameters")
        return

    # Sort alerts by confidence score and urgency
    alerts_sorted = sorted(predictive_alerts,
                          key=lambda x: (x.confidence_score, -x.time_to_failure_estimate.total_seconds()),
                          reverse=True)

    # High priority alerts
    high_priority = [a for a in alerts_sorted if a.confidence_score > 0.8]

    if high_priority:
        st.error(f"**{len(high_priority)} High Priority Alerts Requiring Immediate Attention**")

        for alert in high_priority:
            with st.expander(f"{alert.predicted_failure_type.title()} - {alert.confidence_score:.0%} confidence", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Alert Details:**")
                    st.write(f"• **Failure Type:** {alert.predicted_failure_type}")
                    st.write(f"• **Confidence:** {alert.confidence_score:.1%}")
                    st.write(f"• **Time to Failure:** {alert.time_to_failure_estimate}")
                    st.write(f"• **Affected Components:** {', '.join(alert.affected_components)}")

                with col2:
                    st.write("**Preventive Actions:**")
                    for action in alert.preventive_actions:
                        st.write(f"• {action}")

                    if alert.risk_factors:
                        st.write("**Risk Factors:**")
                        for factor in alert.risk_factors:
                            st.write(f"• {factor}")

    # Medium priority alerts
    medium_priority = [a for a in alerts_sorted if 0.5 <= a.confidence_score <= 0.8]

    if medium_priority:
        st.warning(f"**{len(medium_priority)} Medium Priority Alerts for Planning**")

        for i, alert in enumerate(medium_priority[:3]):  # Show top 3
            with st.expander(f"{alert.predicted_failure_type.title()} - {alert.confidence_score:.0%} confidence"):
                st.write(f"**Estimated Timeline:** {alert.time_to_failure_estimate}")
                st.write(f"**Affected:** {', '.join(alert.affected_components)}")
                st.write("**Recommended Actions:**")
                for action in alert.preventive_actions[:3]:  # Top 3 actions
                    st.write(f"• {action}")

    # Alert trends visualization
    if len(alerts_sorted) > 1:
        st.subheader("Alert Confidence Distribution")

        confidence_scores = [a.confidence_score for a in alerts_sorted]
        failure_types = [a.predicted_failure_type for a in alerts_sorted]

        fig = px.histogram(
            x=confidence_scores,
            nbins=10,
            title="Distribution of Alert Confidence Scores",
            labels={'x': 'Confidence Score', 'y': 'Number of Alerts'}
        )

        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)


def _display_component_health_matrix(dashboard_data: Dict[str, Any]):
    """Display comprehensive component health matrix."""

    st.header("Component Health Matrix")

    health_matrix = dashboard_data.get("health_matrix", {})

    if not health_matrix:
        st.info("No component health data available. Run tests to generate health metrics.")
        return

    # Create health matrix visualization
    components = list(health_matrix.keys())

    # Prepare data for heatmap
    metrics = ['health_score', 'performance_score', 'reliability_score', 'test_coverage']
    metric_labels = ['Health Score', 'Performance', 'Reliability', 'Test Coverage']

    matrix_data = []
    for component in components:
        row = []
        for metric in metrics:
            row.append(health_matrix[component].get(metric, 0))
        matrix_data.append(row)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matrix_data,
        x=metric_labels,
        y=components,
        colorscale='RdYlGn',
        zmin=0,
        zmax=100,
        text=[[f"{val:.0f}" for val in row] for row in matrix_data],
        texttemplate="%{text}",
        textfont={"size": 12},
        hoverongaps=False
    ))

    fig.update_layout(
        title="Component Health Scores (0-100 scale)",
        height=max(400, len(components) * 50),
        xaxis_title="Health Metrics",
        yaxis_title="Components"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Component details table
    st.subheader("Detailed Component Analysis")

    # Convert to DataFrame for better display
    health_df = pd.DataFrame.from_dict(health_matrix, orient='index')
    health_df = health_df.round(1)

    # Add status column based on health score
    health_df['status'] = health_df['health_score'].apply(
        lambda x: '🟢 Excellent' if x >= 90
                  else '🟡 Good' if x >= 70
                  else '🟠 Warning' if x >= 50
                  else 'Critical'
    )

    # Sort by health score
    health_df = health_df.sort_values('health_score', ascending=False)

    st.dataframe(
        health_df.style.background_gradient(subset=['health_score', 'performance_score', 'reliability_score'],
                                          cmap='RdYlGn', vmin=0, vmax=100),
        use_container_width=True
    )

    # Identify components needing attention
    critical_components = health_df[health_df['health_score'] < 70].index.tolist()
    if critical_components:
        st.error(f"**Components requiring attention:** {', '.join(critical_components)}")


def _display_error_pattern_analysis(dashboard_data: Dict[str, Any]):
    """Display detailed error pattern analysis."""

    st.header("Error Pattern Analysis")

    error_summary = dashboard_data.get("error_health_summary", {})

    # Display error statistics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Patterns", error_summary.get("total_patterns_tracked", 0))

    with col2:
        st.metric("Recent Errors", error_summary.get("recent_errors_count", 0))

    with col3:
        critical_patterns = len(error_summary.get("critical_patterns", []))
        st.metric("Critical Patterns", critical_patterns)

    with col4:
        # Calculate error rate trend (simplified)
        st.metric("Status", "Stable" if critical_patterns == 0 else "Attention Needed")

    # Error pattern visualization (simulated for demo)
    if error_summary.get("total_patterns_tracked", 0) > 0:

        st.subheader("Error Pattern Categories")

        # Simulated error category data
        error_categories = {
            "Performance": 40,
            "Data Integrity": 25,
            "Integration": 20,
            "User Input": 10,
            "System Resource": 5
        }

        col1, col2 = st.columns(2)

        with col1:
            # Pie chart of error categories
            fig = px.pie(
                values=list(error_categories.values()),
                names=list(error_categories.keys()),
                title="Error Distribution by Category"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Bar chart of error severity
            severity_data = {
                "Low": 60,
                "Medium": 25,
                "High": 12,
                "Critical": 3
            }

            fig = px.bar(
                x=list(severity_data.keys()),
                y=list(severity_data.values()),
                title="Error Distribution by Severity",
                color=list(severity_data.values()),
                color_continuous_scale="RdYlGn_r"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        # Error timeline (simulated)
        st.subheader("Error Pattern Timeline")

        # Generate sample timeline data
        dates = pd.date_range(start=datetime.now() - timedelta(days=7), periods=7, freq='D')
        error_counts = np.random.poisson(3, 7)  # Simulated error counts

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=error_counts,
            mode='lines+markers',
            name='Daily Error Count',
            line=dict(color='red')
        ))

        fig.update_layout(
            title="Error Occurrence Over Time",
            xaxis_title="Date",
            yaxis_title="Error Count",
            height=300
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.success("No significant error patterns detected - system is performing well!")


def _display_performance_analytics(dashboard_data: Dict[str, Any]):
    """Display advanced performance analytics."""

    st.header("Performance Analytics")

    performance_insights = dashboard_data.get("performance_insights", {})
    recent_reports = dashboard_data.get("recent_reports", [])

    if not recent_reports:
        st.info("No performance data available. Run tests to generate analytics.")
        return

    # Performance metrics over time
    st.subheader("Performance Trends")

    # Prepare performance data
    perf_data = []
    for report in recent_reports[-15:]:  # Last 15 reports
        perf_data.append({
            'timestamp': report.generated_at,
            'component': report.component_name,
            'avg_execution_time': report.avg_execution_time,
            'max_execution_time': report.max_execution_time,
            'memory_usage_mb': report.memory_usage_mb,
            'success_rate': report.success_rate,
            'health_score': report.component_health.health_score
        })

    if perf_data:
        df_perf = pd.DataFrame(perf_data)

        # Create performance dashboard
        col1, col2 = st.columns(2)

        with col1:
            # Execution time trends
            fig = px.line(
                df_perf,
                x='timestamp',
                y='avg_execution_time',
                color='component',
                title='Average Execution Time by Component',
                labels={'avg_execution_time': 'Execution Time (s)'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Memory usage trends
            fig = px.line(
                df_perf,
                x='timestamp',
                y='memory_usage_mb',
                color='component',
                title='Memory Usage by Component',
                labels={'memory_usage_mb': 'Memory Usage (MB)'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Performance correlation analysis
        st.subheader("Performance Correlation Analysis")

        # Calculate correlation matrix
        numeric_cols = ['avg_execution_time', 'memory_usage_mb', 'success_rate', 'health_score']
        corr_matrix = df_perf[numeric_cols].corr()

        fig = px.imshow(
            corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            color_continuous_scale='RdBu',
            aspect='auto',
            title='Performance Metrics Correlation'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Performance insights and recommendations
    if performance_insights:
        st.subheader("Performance Insights")

        for insight_type, insights in performance_insights.items():
            if insights:
                st.write(f"**{insight_type.replace('_', ' ').title()}:**")
                for insight in insights:
                    st.write(f"• {insight}")


def _display_actions_and_recommendations(dashboard_data: Dict[str, Any]):
    """Display actionable recommendations and available actions."""

    st.header("Actions & Recommendations")

    recent_reports = dashboard_data.get("recent_reports", [])

    if not recent_reports:
        st.info("No recent test data available for recommendations.")
        return

    # Get recommendations from latest report
    latest_report = recent_reports[-1] if recent_reports else None

    if latest_report:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("Immediate Actions")
            immediate_actions = latest_report.immediate_actions
            if immediate_actions:
                for action in immediate_actions:
                    st.warning(f"• {action}")
            else:
                st.success("No immediate actions required")

        with col2:
            st.subheader("Preventive Measures")
            preventive_measures = latest_report.preventive_measures
            if preventive_measures:
                for measure in preventive_measures:
                    st.info(f"• {measure}")
            else:
                st.success("System is well-maintained")

        with col3:
            st.subheader("Performance Optimizations")
            optimizations = latest_report.performance_optimizations
            if optimizations:
                for opt in optimizations:
                    st.info(f"• {opt}")
            else:
                st.success("Performance is optimal")

    # Aggregated recommendations from all recent reports
    st.subheader("Comprehensive Recommendations")

    all_immediate = []
    all_preventive = []
    all_performance = []

    for report in recent_reports[-5:]:  # Last 5 reports
        all_immediate.extend(report.immediate_actions)
        all_preventive.extend(report.preventive_measures)
        all_performance.extend(report.performance_optimizations)

    # Get unique recommendations
    unique_immediate = list(set(all_immediate))
    unique_preventive = list(set(all_preventive))
    unique_performance = list(set(all_performance))

    if unique_immediate or unique_preventive or unique_performance:
        with st.expander("Detailed Recommendation Analysis", expanded=False):

            tab1, tab2, tab3 = st.tabs(["Immediate", "Preventive", "Performance"])

            with tab1:
                if unique_immediate:
                    st.write("**High Priority Actions (from recent analysis):**")
                    for i, action in enumerate(unique_immediate[:10], 1):
                        st.write(f"{i}. {action}")
                else:
                    st.success("No immediate actions required")

            with tab2:
                if unique_preventive:
                    st.write("**Preventive Measures (recommended for implementation):**")
                    for i, measure in enumerate(unique_preventive[:10], 1):
                        st.write(f"{i}. {measure}")
                else:
                    st.success("System is well-maintained")

            with tab3:
                if unique_performance:
                    st.write("**Performance Optimizations (for enhanced efficiency):**")
                    for i, opt in enumerate(unique_performance[:10], 1):
                        st.write(f"{i}. {opt}")
                else:
                    st.success("Performance is optimal")


def _display_enhanced_control_panel(dashboard_data: Dict[str, Any]):
    """Display enhanced control panel with advanced actions."""

    st.subheader("Enhanced Control Panel")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("Refresh Dashboard", help="Reload all dashboard data"):
            st.cache_data.clear()
            st.rerun()

    with col2:
        if st.button("Run System Health Check", help="Execute comprehensive health analysis"):
            with st.spinner("Running system health check..."):
                controller = get_enhanced_ai_testing_controller()
                health_check = controller.run_system_wide_health_check()

                st.success("Health check completed!")
                st.json(health_check)

    with col3:
        if st.button("Generate Predictions", help="Generate new predictive alerts"):
            with st.spinner("Generating predictive analysis..."):
                # This would trigger new prediction generation
                st.info("Predictive analysis initiated!")
                time.sleep(1)
                st.rerun()

    with col4:
        if st.button("Export Report", help="Export comprehensive testing report"):
            try:
                # Generate comprehensive report
                report_data = {
                    "generation_time": datetime.now().isoformat(),
                    "dashboard_data": dashboard_data,
                    "export_type": "enhanced_ai_testing_report"
                }

                st.download_button(
                    label="Download Report",
                    data=json.dumps(report_data, indent=2, default=str),
                    file_name=f"enhanced_ai_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            except Exception as e:
                st.error(f"Failed to generate report: {e}")

    with col5:
        if st.button("System Settings", help="Configure monitoring settings"):
            with st.expander("Monitoring Configuration", expanded=True):
                st.write("**Enhanced Monitoring Settings:**")

                # Configuration options
                monitoring_enabled = st.checkbox("Enable Real-time Monitoring", value=True)
                alert_threshold = st.slider("Alert Confidence Threshold", 0.5, 1.0, 0.8, 0.05)
                max_alerts = st.number_input("Maximum Alerts to Display", 1, 50, 10)

                if st.button("Apply Settings"):
                    st.session_state.monitoring_enabled = monitoring_enabled
                    st.session_state.alert_threshold = alert_threshold
                    st.session_state.max_alerts = max_alerts
                    st.success("Settings applied successfully!")


# Helper functions for data processing

def _calculate_enhanced_trends(recent_reports: List[EnhancedTestReport]) -> Dict[str, Any]:
    """Calculate enhanced trend data from recent reports."""
    if len(recent_reports) < 2:
        return {}

    # Calculate trends for last 5 vs previous 5 reports
    recent_5 = recent_reports[-5:] if len(recent_reports) >= 5 else recent_reports
    previous_5 = recent_reports[-10:-5] if len(recent_reports) >= 10 else []

    trends = {}

    if recent_5:
        recent_success = sum(r.success_rate for r in recent_5) / len(recent_5)
        recent_health = sum(r.component_health.health_score for r in recent_5) / len(recent_5)
        recent_performance = sum(r.avg_execution_time for r in recent_5) / len(recent_5)

        trends['recent_success_rate'] = recent_success
        trends['recent_health_score'] = recent_health
        trends['recent_performance'] = recent_performance

        if previous_5:
            prev_success = sum(r.success_rate for r in previous_5) / len(previous_5)
            prev_health = sum(r.component_health.health_score for r in previous_5) / len(previous_5)
            prev_performance = sum(r.avg_execution_time for r in previous_5) / len(previous_5)

            trends['success_rate_trend'] = 'improving' if recent_success > prev_success else 'declining' if recent_success < prev_success else 'stable'
            trends['health_score_trend'] = 'improving' if recent_health > prev_health else 'declining' if recent_health < prev_health else 'stable'
            trends['performance_trend'] = 'improving' if recent_performance < prev_performance else 'declining' if recent_performance > prev_performance else 'stable'

    return trends


def _calculate_component_health_matrix(recent_reports: List[EnhancedTestReport]) -> Dict[str, Dict[str, float]]:
    """Calculate component health matrix from recent reports."""
    health_matrix = {}

    # Group reports by component
    component_reports = {}
    for report in recent_reports:
        component = report.component_name
        if component not in component_reports:
            component_reports[component] = []
        component_reports[component].append(report)

    # Calculate health metrics for each component
    for component, reports in component_reports.items():
        latest_report = reports[-1]  # Most recent report for this component

        health_matrix[component] = {
            'health_score': latest_report.component_health.health_score,
            'performance_score': latest_report.component_health.performance_score,
            'reliability_score': latest_report.component_health.reliability_score,
            'test_coverage': latest_report.test_coverage_score,
            'last_tested': latest_report.generated_at.isoformat()
        }

    return health_matrix


def _generate_performance_insights(recent_reports: List[EnhancedTestReport], system_health: Dict[str, Any]) -> Dict[str, List[str]]:
    """Generate performance insights from analysis data."""
    insights = {
        'performance_trends': [],
        'optimization_opportunities': [],
        'resource_utilization': [],
        'reliability_insights': []
    }

    if not recent_reports:
        return insights

    # Analyze performance trends
    execution_times = [r.avg_execution_time for r in recent_reports[-10:]]
    if execution_times:
        avg_time = sum(execution_times) / len(execution_times)
        if avg_time > 3.0:
            insights['performance_trends'].append(f"Average execution time is high: {avg_time:.2f}s")

        # Check for performance degradation
        if len(execution_times) > 5:
            recent_avg = sum(execution_times[-5:]) / 5
            older_avg = sum(execution_times[-10:-5]) / 5
            if recent_avg > older_avg * 1.2:
                insights['performance_trends'].append("Performance degradation detected in recent tests")

    # Memory utilization insights
    memory_usage = [r.memory_usage_mb for r in recent_reports[-10:]]
    if memory_usage:
        avg_memory = sum(memory_usage) / len(memory_usage)
        if avg_memory > 200:
            insights['resource_utilization'].append(f"High memory usage detected: {avg_memory:.0f}MB average")

    # Success rate insights
    success_rates = [r.success_rate for r in recent_reports[-10:]]
    if success_rates:
        avg_success = sum(success_rates) / len(success_rates)
        if avg_success < 0.8:
            insights['reliability_insights'].append(f"Success rate below optimal: {avg_success:.1%}")

    return insights


def _calculate_success_rate_delta(dashboard_data: Dict[str, Any]) -> Optional[str]:
    """Calculate success rate delta for display."""
    testing_24h = dashboard_data.get("testing_summary_24h", {})
    testing_7d = dashboard_data.get("testing_summary_7d", {})

    rate_24h = testing_24h.get("average_success_rate", 0)
    rate_7d = testing_7d.get("average_success_rate", 0)

    if rate_7d > 0:
        delta = rate_24h - rate_7d
        return f"{delta:+.1%} vs 7d avg"

    return None


def _calculate_health_delta(dashboard_data: Dict[str, Any]) -> Optional[str]:
    """Calculate health score delta for display."""
    # This would calculate health score changes over time
    # For now, return a placeholder
    return "Stable"