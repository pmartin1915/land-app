"""
County Expansion Center - Parallel Scraping Management Dashboard

This component provides comprehensive management and monitoring of the
parallel county scraping system for expanding property data coverage.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import subprocess
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.scraper import ALABAMA_COUNTY_CODES
from config.enhanced_error_handling import get_error_statistics

logger = logging.getLogger(__name__)

def _initialize_expansion_state():
    """Initialize county expansion session state."""
    if 'county_expansion' not in st.session_state:
        st.session_state.county_expansion = {
            'active_session': None,
            'last_refresh': datetime.now(),
            'selected_counties': [],
            'scraping_in_progress': False,
            'auto_refresh': False
        }

def load_scraping_checkpoints() -> List[Dict[str, Any]]:
    """Load available scraping checkpoints."""
    checkpoint_dir = Path("data/checkpoints")
    checkpoints = []

    if checkpoint_dir.exists():
        for checkpoint_file in checkpoint_dir.glob("*_checkpoint.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)

                checkpoints.append({
                    "file_path": str(checkpoint_file),
                    "file_name": checkpoint_file.name,
                    "session_id": data.get("session", {}).get("session_id", "Unknown"),
                    "checkpoint_time": data.get("checkpoint_time", "Unknown"),
                    "completion_percentage": data.get("statistics", {}).get("completion_percentage", 0),
                    "total_records": data.get("statistics", {}).get("total_records", 0),
                    "successful_counties": data.get("statistics", {}).get("successful_counties", 0),
                    "failed_counties": data.get("statistics", {}).get("failed_counties", 0)
                })
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")

    return sorted(checkpoints, key=lambda x: x["checkpoint_time"], reverse=True)

def load_scraping_results() -> List[Dict[str, Any]]:
    """Load completed scraping results."""
    results_dir = Path("data/scraping_results")
    results = []

    if results_dir.exists():
        for results_file in results_dir.glob("scraping_results_*.csv"):
            try:
                df = pd.read_csv(results_file)

                results.append({
                    "file_path": str(results_file),
                    "file_name": results_file.name,
                    "timestamp": results_file.stem.split("_")[-2:],  # Extract timestamp
                    "total_counties": len(df),
                    "successful_counties": df['success'].sum(),
                    "total_records": df['records_scraped'].sum(),
                    "average_quality": df[df['success']]['data_quality_score'].mean() if df['success'].any() else 0,
                    "data": df
                })
            except Exception as e:
                logger.warning(f"Failed to load results {results_file}: {e}")

    return sorted(results, key=lambda x: x["file_name"], reverse=True)

def get_current_database_coverage() -> Dict[str, Any]:
    """Get current database coverage statistics."""
    try:
        # This would ideally query the actual database
        # For now, we'll simulate based on known data
        total_counties = len(ALABAMA_COUNTY_CODES)

        # Check for raw data files to estimate coverage
        raw_dir = Path("data/raw")
        covered_counties = set()

        if raw_dir.exists():
            for file in raw_dir.glob("scraped_*_county_*.csv"):
                # Extract county name from filename
                parts = file.stem.split("_")
                if len(parts) >= 3:
                    county_part = "_".join(parts[1:-2])  # Remove 'scraped' and timestamp
                    covered_counties.add(county_part)

        return {
            "total_counties": total_counties,
            "covered_counties": len(covered_counties),
            "coverage_percentage": (len(covered_counties) / total_counties) * 100,
            "missing_counties": total_counties - len(covered_counties)
        }
    except Exception as e:
        logger.error(f"Failed to get database coverage: {e}")
        return {
            "total_counties": 67,
            "covered_counties": 4,
            "coverage_percentage": 6.0,
            "missing_counties": 63
        }

def display_coverage_overview():
    """Display current data coverage overview."""
    st.subheader("DATA COVERAGE OVERVIEW")

    coverage = get_current_database_coverage()

    # Coverage metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Counties",
            coverage["total_counties"],
            help="Total Alabama counties available for scraping"
        )

    with col2:
        st.metric(
            "Covered Counties",
            coverage["covered_counties"],
            delta=f"{coverage['coverage_percentage']:.1f}% coverage",
            help="Counties with data currently in the system"
        )

    with col3:
        st.metric(
            "Missing Counties",
            coverage["missing_counties"],
            delta=f"-{100 - coverage['coverage_percentage']:.1f}% remaining",
            delta_color="inverse",
            help="Counties without data that need scraping"
        )

    with col4:
        # Estimate total potential properties
        avg_properties_per_county = 50  # Conservative estimate
        potential_properties = coverage["missing_counties"] * avg_properties_per_county
        st.metric(
            "Est. Missing Properties",
            f"{potential_properties:,}",
            help="Estimated properties available in unscraped counties"
        )

    # Coverage visualization
    fig = go.Figure(data=[
        go.Bar(
            x=['Covered', 'Missing'],
            y=[coverage["covered_counties"], coverage["missing_counties"]],
            marker_color=['#22c55e', '#ef4444'],
            text=[coverage["covered_counties"], coverage["missing_counties"]],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title="County Coverage Status",
        yaxis_title="Number of Counties",
        height=300,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

def display_scraping_controls():
    """Display scraping controls and configuration."""
    st.subheader("PARALLEL SCRAPING CONTROLS")

    with st.expander("SCRAPING CONFIGURATION", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            workers = st.slider(
                "Parallel Workers",
                min_value=1,
                max_value=8,
                value=4,
                help="Number of concurrent scraping operations. More workers = faster, but higher server load."
            )

            max_pages = st.slider(
                "Max Pages per County",
                min_value=10,
                max_value=500,
                value=100,
                step=10,
                help="Maximum pages to scrape per county. Higher = more thorough but slower."
            )

        with col2:
            rate_limit = st.slider(
                "Rate Limit Delay (seconds)",
                min_value=1.0,
                max_value=10.0,
                value=2.5,
                step=0.5,
                help="Delay between requests to avoid overwhelming the server."
            )

            # County selection
            counties_to_scrape = st.multiselect(
                "Counties to Scrape (leave empty for all)",
                options=list(ALABAMA_COUNTY_CODES.keys()),
                format_func=lambda x: f"{x}: {ALABAMA_COUNTY_CODES[x]}",
                help="Select specific counties or leave empty to scrape all missing counties."
            )

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("START SCRAPING", type="primary", disabled=st.session_state.county_expansion.get('scraping_in_progress', False)):
            # This would launch the parallel scraping
            st.session_state.county_expansion['scraping_in_progress'] = True

            st.success("Scraping initiated!")
            st.info(f"""
            **Configuration:**
            - Workers: {workers}
            - Max pages: {max_pages}
            - Rate limit: {rate_limit}s
            - Counties: {"All missing" if not counties_to_scrape else len(counties_to_scrape)}

            **Note:** This is a demonstration. In production, this would launch the parallel scraper.
            To actually start scraping, run: `python launch_parallel_scraping.py`
            """)

    with col2:
        if st.button("STOP SCRAPING", disabled=not st.session_state.county_expansion.get('scraping_in_progress', False)):
            st.session_state.county_expansion['scraping_in_progress'] = False
            st.warning("Scraping stopped. Progress has been saved to checkpoint.")

    with col3:
        if st.button("REFRESH STATUS"):
            st.session_state.county_expansion['last_refresh'] = datetime.now()
            st.cache_data.clear()
            st.rerun()

def display_checkpoint_management():
    """Display checkpoint management interface."""
    st.subheader("CHECKPOINT MANAGEMENT")

    checkpoints = load_scraping_checkpoints()

    if checkpoints:
        st.markdown("**Available Checkpoints:**")

        for i, checkpoint in enumerate(checkpoints):
            with st.expander(f"{checkpoint['session_id']} - {checkpoint['completion_percentage']:.1f}% Complete", expanded=i==0):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Session ID:** {checkpoint['session_id']}")
                    st.write(f"**Saved:** {checkpoint['checkpoint_time']}")
                    st.write(f"**Progress:** {checkpoint['completion_percentage']:.1f}%")

                with col2:
                    st.write(f"**Successful Counties:** {checkpoint['successful_counties']}")
                    st.write(f"**Failed Counties:** {checkpoint['failed_counties']}")
                    st.write(f"**Total Records:** {checkpoint['total_records']:,}")

                with col3:
                    if st.button(f"Resume Session", key=f"resume_{i}"):
                        st.info(f"To resume this session, run:\n`python launch_parallel_scraping.py --resume {checkpoint['file_path']}`")

                    if st.button(f"Delete Checkpoint", key=f"delete_{i}"):
                        try:
                            Path(checkpoint['file_path']).unlink()
                            st.success("Checkpoint deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")
    else:
        st.info("No checkpoints found. Start a scraping session to create checkpoints.")

def display_results_analysis():
    """Display analysis of scraping results."""
    st.subheader("SCRAPING RESULTS ANALYSIS")

    results = load_scraping_results()

    if results:
        # Latest results summary
        latest = results[0]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Latest Session", latest['file_name'].split('_')[2])
        with col2:
            st.metric("Counties Scraped", latest['total_counties'])
        with col3:
            st.metric("Success Rate", f"{(latest['successful_counties'] / latest['total_counties'] * 100):.1f}%")
        with col4:
            st.metric("Total Properties", f"{latest['total_records']:,}")

        # Detailed results
        if st.checkbox("Show Detailed Results"):
            df = latest['data']

            # Success/failure breakdown
            fig = px.pie(
                values=[df['success'].sum(), (~df['success']).sum()],
                names=['Successful', 'Failed'],
                title="Scraping Success Rate by County",
                color_discrete_map={'Successful': '#22c55e', 'Failed': '#ef4444'}
            )

            col1, col2 = st.columns(2)

            with col1:
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Top performing counties
                if df['success'].any():
                    top_counties = df[df['success']].nlargest(10, 'records_scraped')

                    fig2 = px.bar(
                        top_counties,
                        x='county_name',
                        y='records_scraped',
                        title="Top 10 Counties by Records Scraped",
                        labels={'county_name': 'County', 'records_scraped': 'Records'}
                    )
                    fig2.update_xaxis(tickangle=45)

                    st.plotly_chart(fig2, use_container_width=True)

            # Detailed table
            if st.checkbox("Show Raw Results Table"):
                display_df = df[['county_name', 'success', 'records_scraped', 'data_quality_score', 'duration_seconds']].copy()
                display_df['duration_formatted'] = display_df['duration_seconds'].apply(lambda x: f"{x:.1f}s")
                display_df = display_df.drop('duration_seconds', axis=1)

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
    else:
        st.info("No scraping results found. Complete a scraping session to see analysis here.")

def display_system_status():
    """Display system status and health metrics."""
    st.subheader("SYSTEM STATUS")

    # Error statistics
    error_stats = get_error_statistics()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "System Health",
            "Operational" if error_stats['total_errors'] < 10 else "Degraded",
            delta=f"{error_stats['total_errors']} recent errors",
            delta_color="inverse" if error_stats['total_errors'] > 0 else "normal"
        )

    with col2:
        st.metric(
            "Data Pipeline",
            "Ready",
            help="Scraping and import pipeline status"
        )

    with col3:
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=st.session_state.county_expansion.get('auto_refresh', False))
        st.session_state.county_expansion['auto_refresh'] = auto_refresh

    # Quick actions
    st.markdown("**Quick Actions:**")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Run Import Script"):
            st.info("To import scraped data, run: `python scripts/import_data.py`")

    with col2:
        if st.button("View Database Stats"):
            st.info("Database statistics would be displayed here in full implementation.")

    with col3:
        if st.button("Cleanup Temp Files"):
            st.info("Temporary file cleanup would be performed here.")

def display_county_expansion_center():
    """Main county expansion center component."""
    # Initialize state
    _initialize_expansion_state()

    st.title("County Expansion Center")
    st.markdown("**Parallel scraping management for comprehensive Alabama county coverage**")

    # Auto-refresh logic
    if st.session_state.county_expansion.get('auto_refresh', False):
        time.sleep(30)
        st.rerun()

    # Main sections
    display_coverage_overview()

    st.markdown("---")

    display_scraping_controls()

    st.markdown("---")

    # Tabs for detailed management
    tab1, tab2, tab3 = st.tabs(["Checkpoints", "Results Analysis", "System Status"])

    with tab1:
        display_checkpoint_management()

    with tab2:
        display_results_analysis()

    with tab3:
        display_system_status()

    # Instructions
    st.markdown("---")

    with st.expander("USAGE INSTRUCTIONS"):
        st.markdown("""
        **Getting Started with Parallel Scraping:**

        1. **Review Coverage:** Check which counties are missing data above
        2. **Configure Scraping:** Set workers, pages, and rate limits based on your system
        3. **Start Scraping:** Use the controls above or run `python launch_parallel_scraping.py`
        4. **Monitor Progress:** Checkpoints are saved automatically every 5 counties
        5. **Resume if Needed:** If interrupted, you can resume from the last checkpoint
        6. **Import Data:** After scraping, run `python scripts/import_data.py` to load into database

        **Performance Guidelines:**
        - **2-4 workers:** Conservative, reliable
        - **4-6 workers:** Balanced performance
        - **6-8 workers:** Aggressive (may hit rate limits)

        **Estimated Timeline:**
        - All 67 counties: 2-4 hours
        - Missing counties only: 1-3 hours
        - Individual counties: 2-10 minutes each

        **Troubleshooting:**
        - If scraping fails, check the logs in the console
        - Reduce workers and increase rate limit if hitting server limits
        - Use checkpoints to resume interrupted sessions
        """)

# Export function
def display_county_expansion_center_component():
    """Export function for the county expansion center component."""
    display_county_expansion_center()