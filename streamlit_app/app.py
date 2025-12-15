"""
Alabama Auction Watcher - Optimized Streamlit Dashboard

High-performance interactive dashboard with AI testability for browsing and analyzing
tax delinquent properties from the Alabama Department of Revenue.

Features:
- Advanced caching with multi-tier strategy
- Asynchronous data loading
- Memory optimization
- Performance monitoring
- AI-driven testing and error detection

Usage:
    streamlit run streamlit_app/app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import threading
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import (
    DEFAULT_PRICE_RANGE, DEFAULT_ACREAGE_RANGE, CHART_COLORS
)
from config.security import get_security_config, create_secure_headers

from scripts.utils import format_currency, format_acreage, format_score
from streamlit_app.components.visualizations import create_radar_chart, create_county_heatmap, create_correlation_heatmap
from streamlit_app.components.county_view import county_deep_dive_view
from streamlit_app.components.comparison_view import display_comparison_view
from streamlit_app.components.analytics_dashboard import display_analytics_dashboard
from streamlit_app.components.predictive_analytics import display_predictive_analytics_dashboard
from streamlit_app.components.enhanced_market_intelligence import display_enhanced_market_intelligence_component
from streamlit_app.components.ai_testing_dashboard import display_ai_testing_dashboard
from streamlit_app.components.application_assistant import display_application_assistant_component
from streamlit_app.components.investment_portfolio import display_investment_portfolio_component
from streamlit_app.components.statewide_command_center import display_statewide_command_center_component
from streamlit_app.components.county_expansion_center import display_county_expansion_center_component
from streamlit_app.components.healthcare_land_banking import display_healthcare_land_banking_component

# Import optimization systems
from streamlit_app.core.performance_monitor import (
    get_performance_monitor, monitor_performance, performance_context, display_performance_metrics
)
from streamlit_app.core.cache_manager import (
    get_cache_manager, smart_cache, invalidate_cache_on_filter_change, display_cache_info
)
from streamlit_app.core.async_loader import (
    get_streamlit_loader, async_load_properties, DataLoadingProgress
)
from streamlit_app.core.memory_optimizer import (
    get_memory_manager, optimize_dataframe, check_memory_and_optimize, display_memory_info
)
from streamlit_app.testing.ai_testability import (
    get_test_executor, ai_test_decorator, test_component_with_ai
)


# Page configuration
st.set_page_config(
    page_title="Alabama Auction Watcher",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Import professional fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global styles */
    .main > div {
        padding: 0rem 1rem;
        font-family: 'Inter', sans-serif;
    }

    /* Header improvements */
    h1 {
        color: #1f2937;
        font-weight: 700;
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem !important;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 0.5rem;
    }

    h2, h3 {
        color: #374151;
        font-weight: 600;
        letter-spacing: 0.025em;
    }

    /* Professional color scheme */
    .stAlert {
        margin: 1rem 0;
        border-radius: 0.5rem;
    }

    .metric-card {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin: 0.5rem 0;
        border: 1px solid #cbd5e1;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }

    .disclaimer-banner {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border: 1px solid #f59e0b;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        color: #92400e;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }

    /* Data table improvements */
    .data-table {
        font-size: 0.9rem;
        font-family: 'Inter', monospace;
    }

    /* Sidebar improvements */
    .css-1d391kg {
        background-color: #f8fafc;
        border-right: 2px solid #e2e8f0;
    }

    /* Button improvements */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 0.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px 0 rgba(59, 130, 246, 0.3);
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px 0 rgba(59, 130, 246, 0.4);
    }

    /* Tab improvements */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        color: #64748b;
        font-weight: 500;
        border-radius: 0.5rem 0.5rem 0 0;
        padding: 0.75rem 1.5rem;
        border: 1px solid #e2e8f0;
    }

    .stTabs [aria-selected="true"] {
        background-color: #3b82f6;
        color: white;
        border-color: #3b82f6;
    }

    /* Metric improvements */
    [data-testid="metric-container"] {
        background: white;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }

    [data-testid="metric-container"] > div {
        font-weight: 600;
        color: #1f2937;
    }

    /* Professional footer */
    .footer-style {
        text-align: center;
        color: #6b7280;
        font-size: 0.875rem;
        font-weight: 400;
        margin-top: 2rem;
        padding: 1rem;
        border-top: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """
    Initialize session state with proper namespacing to prevent conflicts.
    This prevents the table from disappearing after comparison operations.
    """
    # Initialize main application state namespace
    if 'app_state' not in st.session_state:
        st.session_state.app_state = {
            'table_data': None,
            'selected_properties': {},
            'last_filter_hash': None,
            'comparison_active': False,
            'table_version': 0
        }

    # Initialize table state namespace
    if 'table_state' not in st.session_state:
        st.session_state.table_state = {
            'selection_state': {},
            'last_interaction': time.time(),
            'stable_key_version': 1
        }

    # Initialize comparison state namespace
    if 'comparison_state' not in st.session_state:
        st.session_state.comparison_state = {
            'active_comparison': False,
            'compared_properties': [],
            'comparison_data': None
        }


def get_stable_table_key():
    """
    Generate a stable key for the data editor that persists across reruns.
    This prevents the table from losing its state during app reruns.
    Enhanced with filter isolation to prevent interference from other components.
    """
    # Use a combination of table version and current filters for true stability
    version = st.session_state.table_state.get('stable_key_version', 1)

    # Include filter hash to ensure stability for current filter state
    current_filters = st.session_state.get('filters', {})
    filter_hash = str(hash(str(sorted(current_filters.items()))))[-6:]  # Last 6 chars of hash

    # Ensure single property analysis doesn't interfere
    analysis_isolation = st.session_state.get('single_analysis_state', {}).get('last_selection_time', 0)

    return f"property_table_v{version}_{filter_hash}_isolated"


def preserve_table_selection(edited_df: pd.DataFrame, original_df: pd.DataFrame):
    """
    Preserve table selection state across app reruns and component interactions.
    Enhanced with robust state isolation to prevent interference.
    """
    if edited_df is not None and not edited_df.empty:
        # Store current selection in stable session state with isolation
        selected_indices = edited_df[edited_df.get('Select', False)].index.tolist()

        # Extract selected property data for Application Assistant integration
        property_data = {}
        if selected_indices and not original_df.empty:
            selected_rows = original_df.iloc[selected_indices]
            for _, row in selected_rows.iterrows():
                property_id = row.get('id')
                if property_id:
                    property_data[property_id] = {
                        'parcel_id': row.get('parcel_id'),
                        'county': row.get('county'),
                        'amount': row.get('amount'),
                        'acreage': row.get('acreage'),
                        'investment_score': row.get('investment_score'),
                        'estimated_all_in_cost': row.get('estimated_all_in_cost'),
                        'description': row.get('description', ''),
                        'water_score': row.get('water_score'),
                        'selected_at': time.time()
                    }

        # Create a more robust state structure
        current_time = time.time()
        st.session_state.app_state['selected_properties'] = {
            'indices': selected_indices,
            'count': len(selected_indices),
            'timestamp': current_time,
            'preserved_from': 'main_table',
            'filter_context': str(hash(str(sorted(st.session_state.get('filters', {}).items())))),
            'property_data': property_data  # Added for Application Assistant integration
        }

        # Update interaction timestamp with isolation marker
        st.session_state.table_state['last_interaction'] = current_time
        st.session_state.table_state['interaction_source'] = 'main_table'

        # Prevent single property analysis from affecting this state
        if 'single_analysis_state' in st.session_state:
            st.session_state.single_analysis_state['last_table_interaction'] = current_time


@monitor_performance("load_watchlist_data", include_memory=True)
@smart_cache("properties_data", ttl_seconds=300, cache_type="api_data")
def load_watchlist_data(filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Optimized data loading with advanced caching, async loading, and memory optimization.

    Args:
        filters: A dictionary of filters to apply to the API query.

    Returns:
        Optimized DataFrame with watchlist data.
    """
    try:
        # Check memory before loading large datasets
        check_memory_and_optimize()

        # Use async loader for better performance
        with DataLoadingProgress("Loading property data...") as progress:
            progress.update(20, "Initializing data loader...")

            loader = get_streamlit_loader()
            progress.update(50, "Fetching data from API...")

            # Load data with async optimization
            df = loader.load_properties_with_ui(filters)
            progress.update(80, "Optimizing data structure...")

            if not df.empty:
                # Memory optimization
                df = optimize_dataframe(df, aggressive=False)

                # Store in session state for other components
                if 'current_data' not in st.session_state:
                    st.session_state.current_data = {}
                st.session_state.current_data['properties'] = df

            progress.update(100, "Data loading complete!")

        return df

    except Exception as e:
        # Enhanced error handling with AI logging
        performance_monitor = get_performance_monitor()
        performance_monitor.record_metric("load_watchlist_data", "error", 1, {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "filters": filters
        })

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


@monitor_performance("create_sidebar_filters")
def create_sidebar_filters() -> Dict:
    """
    Create optimized sidebar filters with intelligent caching and filter change detection.

    Returns:
        Dictionary with filter values
    """
    with performance_context("sidebar", "filter_creation"):
        st.sidebar.header("FILTERS")

        # Check for previous filters to detect changes
        previous_filters = st.session_state.get('previous_filters', {})
        filters = {}

        # Price range filter
        filters['price_range'] = st.sidebar.slider(
            "Price Range ($)",
            min_value=0.0,
            max_value=50000.0,
            value=DEFAULT_PRICE_RANGE,
            step=100.0,
            format="$%.0f",
            key="price_range_slider"
        )

        # Acreage range filter
        filters['acreage_range'] = st.sidebar.slider(
            "Acreage Range",
            min_value=0.0,
            max_value=100.0,
            value=DEFAULT_ACREAGE_RANGE,
            step=0.1,
            format="%.1f",
            key="acreage_range_slider"
        )

        # Water features filter
        filters['water_only'] = st.sidebar.checkbox(
            "Show only properties with water features",
            value=False,
            key="water_only_checkbox"
        )

        # County filter - cached for performance
        all_counties = ['All', 'Autauga', 'Baldwin', 'Barbour', 'Bibb', 'Blount', 'Bullock', 'Butler', 'Calhoun', 'Chambers', 'Cherokee', 'Chilton', 'Choctaw', 'Clarke', 'Clay', 'Cleburne', 'Coffee', 'Colbert', 'Conecuh', 'Coosa', 'Covington', 'Crenshaw', 'Cullman', 'Dale', 'Dallas', 'DeKalb', 'Elmore', 'Escambia', 'Etowah', 'Fayette', 'Franklin', 'Geneva', 'Greene', 'Hale', 'Henry', 'Houston', 'Jackson', 'Jefferson', 'Lamar', 'Lauderdale', 'Lawrence', 'Lee', 'Limestone', 'Lowndes', 'Macon', 'Madison', 'Marengo', 'Marion', 'Marshall', 'Monroe', 'Montgomery', 'Morgan', 'Perry', 'Pickens', 'Pike', 'Randolph', 'Russell', 'St. Clair', 'Shelby', 'Sumter', 'Talladega', 'Tallapoosa', 'Tuscaloosa', 'Walker', 'Washington', 'Wilcox', 'Winston']
        filters['county'] = st.sidebar.selectbox(
            "County",
            options=all_counties,
            index=0,
            key="county_selectbox"
        )

        # Investment score threshold
        filters['min_investment_score'] = st.sidebar.slider(
            "Minimum Investment Score",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            format="%.1f",
            key="min_investment_score_slider"
        )

        st.sidebar.markdown("---")
        st.sidebar.subheader("INTELLIGENCE SCORES")

        filters['min_county_market_score'] = st.sidebar.slider(
            "Min County Market Score", 0.0, 100.0, 0.0, 1.0, key="county_market_slider")
        filters['min_geographic_score'] = st.sidebar.slider(
            "Min Geographic Score", 0.0, 100.0, 0.0, 1.0, key="geographic_slider")
        filters['min_market_timing_score'] = st.sidebar.slider(
            "Min Market Timing Score", 0.0, 100.0, 0.0, 1.0, key="timing_slider")
        filters['min_total_description_score'] = st.sidebar.slider(
            "Min Description Score", 0.0, 100.0, 0.0, 1.0, key="description_slider")
        filters['min_road_access_score'] = st.sidebar.slider(
            "Min Road Access Score", 0.0, 100.0, 0.0, 1.0, key="road_access_slider")

        # Detect filter changes and invalidate cache if needed
        if filters != previous_filters:
            invalidate_cache_on_filter_change()
            st.session_state.previous_filters = filters

        st.sidebar.markdown("---")

        # Performance and cache controls
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("↻ Refresh", type="primary", key="refresh_button"):
                # Clear all caches and refresh
                cache_manager = get_cache_manager()
                cache_manager.memory_cache.clear()
                st.rerun()

        with col2:
            if st.button("▲ Optimize", key="optimize_button"):
                # Trigger memory optimization
                check_memory_and_optimize()
                st.success("Optimized!")

        # Debug information (collapsible)
        if st.sidebar.checkbox("Show Debug Info", value=False, key="debug_checkbox"):
            with st.sidebar.expander("Performance Metrics"):
                display_performance_metrics()

            with st.sidebar.expander("Cache Info"):
                display_cache_info()

            with st.sidebar.expander("Memory Info"):
                display_memory_info()

        # Store current filters for next comparison
        st.session_state.filters = filters

        return filters


@monitor_performance("display_summary_metrics", include_memory=True)
@smart_cache("summary_metrics", ttl_seconds=180, cache_type="calculation")
@ai_test_decorator("summary_metrics", "calculation")
def display_summary_metrics(df: pd.DataFrame):
    """
    Optimized display of summary metrics cards with advanced caching and AI testability.

    Args:
        df: Filtered DataFrame
    """
    try:
        if len(df) == 0:
            st.warning("No properties match the current filters.")
            return

        # Check memory before processing large datasets
        check_memory_and_optimize()

        with performance_context("summary_metrics", "calculation"):
            st.subheader("SUMMARY METRICS")

            # Optimize DataFrame for calculations if large
            if len(df) > 5000:
                df_optimized = optimize_dataframe(df, aggressive=False)
            else:
                df_optimized = df

            # Batch calculate all metrics for efficiency
            metrics_data = _calculate_batch_metrics(df_optimized)

            # Create metrics columns
            col1, col2, col3, col4 = st.columns(4)

            with performance_context("summary_metrics", "display_row1"):
                with col1:
                    st.metric(
                        label="Total Properties",
                        value=f"{metrics_data['total_properties']:,}"
                    )

                with col2:
                    if metrics_data['avg_price'] is not None:
                        st.metric(
                            label="Average Price",
                            value=format_currency(metrics_data['avg_price'])
                        )

                with col3:
                    if metrics_data['avg_price_per_acre'] is not None:
                        st.metric(
                            label="Avg Price/Acre",
                            value=format_currency(metrics_data['avg_price_per_acre'])
                        )

                with col4:
                    if metrics_data['water_count'] is not None:
                        st.metric(
                            label="Water Features",
                            value=f"{metrics_data['water_count']} ({metrics_data['water_percentage']:.1f}%)"
                        )

            # Additional metrics row
            col5, col6, col7, col8 = st.columns(4)

            with performance_context("summary_metrics", "display_row2"):
                with col5:
                    if metrics_data['total_investment'] is not None:
                        st.metric(
                            label="Total Investment",
                            value=format_currency(metrics_data['total_investment'])
                        )

                with col6:
                    if metrics_data['total_acreage'] is not None:
                        st.metric(
                            label="Total Acreage",
                            value=format_acreage(metrics_data['total_acreage'])
                        )

                with col7:
                    if metrics_data['avg_score'] is not None:
                        st.metric(
                            label="Avg Investment Score",
                            value=format_score(metrics_data['avg_score'])
                        )

                with col8:
                    if metrics_data['avg_all_in'] is not None:
                        st.metric(
                            label="Avg All-in Cost",
                            value=format_currency(metrics_data['avg_all_in'])
                        )

    except Exception as e:
        # Enhanced error handling with AI logging
        performance_monitor = get_performance_monitor()
        performance_monitor.record_metric("display_summary_metrics", "error", 1, {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "dataframe_shape": df.shape if df is not None else None
        })

        st.error(f"Error displaying summary metrics: {e}")


@smart_cache("batch_metrics_calculation", ttl_seconds=300, cache_type="calculation")
def _calculate_batch_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Efficiently calculate all summary metrics in a single batch operation.

    Args:
        df: DataFrame to calculate metrics for

    Returns:
        Dictionary containing all calculated metrics
    """
    with performance_context("summary_metrics", "batch_calculation"):
        metrics = {
            'total_properties': len(df),
            'avg_price': None,
            'avg_price_per_acre': None,
            'water_count': None,
            'water_percentage': None,
            'total_investment': None,
            'total_acreage': None,
            'avg_score': None,
            'avg_all_in': None
        }

        # Calculate metrics only if columns exist
        if 'amount' in df.columns:
            metrics['avg_price'] = df['amount'].mean()
            metrics['total_investment'] = df['amount'].sum()

        if 'price_per_acre' in df.columns:
            metrics['avg_price_per_acre'] = df['price_per_acre'].mean()

        if 'water_score' in df.columns:
            water_count = (df['water_score'] > 0).sum()
            metrics['water_count'] = water_count
            metrics['water_percentage'] = (water_count / len(df)) * 100 if len(df) > 0 else 0

        if 'acreage' in df.columns:
            metrics['total_acreage'] = df['acreage'].sum()

        if 'investment_score' in df.columns:
            metrics['avg_score'] = df['investment_score'].mean()

        if 'estimated_all_in_cost' in df.columns:
            metrics['avg_all_in'] = df['estimated_all_in_cost'].mean()

        return metrics


@monitor_performance("display_properties_table", include_memory=True)
@smart_cache("properties_table", ttl_seconds=240, cache_type="ui_component")
@ai_test_decorator("properties_table", "ui_component")
def display_properties_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimized display of properties data table with advanced performance monitoring,
    memory optimization, and AI testability for large datasets.

    Args:
        df: Filtered DataFrame

    Returns:
        DataFrame with selected properties.
    """
    try:
        if len(df) == 0:
            return pd.DataFrame()

        # Memory optimization for large datasets
        check_memory_and_optimize()

        with performance_context("properties_table", "initialization"):
            st.subheader("PROPERTIES")
            st.info("Select properties using the checkboxes to compare them below.")

            # Progressive loading for very large datasets
            if len(df) > 10000:
                st.warning(f"Large dataset detected ({len(df):,} properties). Loading optimized view...")
                df_display = _prepare_large_dataset_for_display(df)
            else:
                df_display = df

            # Optimize DataFrame for table operations
            with performance_context("properties_table", "dataframe_optimization"):
                df_optimized = optimize_dataframe(df_display, aggressive=False)

                # Add a 'Select' column for checkboxes
                df_copy = df_optimized.copy()
                df_copy.insert(0, "Select", False)

            # Build column configuration efficiently
            with performance_context("properties_table", "column_configuration"):
                display_columns, column_config = _build_table_column_config(df_copy)

        # Render table with performance monitoring and stable state management
        with performance_context("properties_table", "table_rendering"):
            # Initialize session state before rendering table
            initialize_session_state()

            # Use stable key to prevent state loss during reruns
            stable_key = get_stable_table_key()

            # Use st.data_editor to make the table interactive
            edited_df = st.data_editor(
                df_copy[display_columns],
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                key=stable_key
            )

        # Process selected rows efficiently
        with performance_context("properties_table", "selection_processing"):
            selected_rows = edited_df[edited_df.Select] if edited_df is not None else pd.DataFrame()

            # Preserve selection state across reruns to prevent table disappearing
            preserve_table_selection(edited_df, df)

            # Drop the 'Select' column before returning
            selected_df = df.loc[selected_rows.index] if not selected_rows.empty else pd.DataFrame()

        # Export functionality with performance tracking
        with performance_context("properties_table", "export_functionality"):
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("↓ Export Current View as CSV"):
                    with st.spinner("Generating CSV..."):
                        csv_data = df[display_columns[1:]].to_csv(index=False)  # Exclude 'Select'
                        st.download_button(
                            label="Download CSV",
                            data=csv_data,
                            file_name="filtered_watchlist.csv",
                            mime="text/csv"
                        )
                        st.success("CSV ready for download!")

            with col2:
                # Display table performance info if enabled
                if st.session_state.get('debug_checkbox', False):
                    table_info = {
                        'Total Rows': len(df),
                        'Displayed Rows': len(df_display),
                        'Selected Rows': len(selected_df),
                        'Memory Usage': f"{df.memory_usage().sum() / 1024 / 1024:.1f} MB"
                    }
                    st.caption(f"Table Info: {table_info}")

        return selected_df

    except Exception as e:
        # Enhanced error handling with AI logging
        performance_monitor = get_performance_monitor()
        performance_monitor.record_metric("display_properties_table", "error", 1, {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "dataframe_shape": df.shape if df is not None else None
        })

        st.error(f"Error displaying properties table: {e}")
        return pd.DataFrame()


@smart_cache("large_dataset_preparation", ttl_seconds=600, cache_type="data_processing")
def _prepare_large_dataset_for_display(df: pd.DataFrame, max_rows: int = 5000) -> pd.DataFrame:
    """
    Optimize large datasets for table display with intelligent sampling.

    Args:
        df: Large DataFrame to optimize
        max_rows: Maximum rows to display

    Returns:
        Optimized DataFrame for display
    """
    with performance_context("properties_table", "large_dataset_prep"):
        if len(df) <= max_rows:
            return df

        # Intelligent sampling - prioritize high-scoring properties
        if 'investment_score' in df.columns:
            # Sort by investment score and take top portion + random sample
            top_portion = int(max_rows * 0.7)  # 70% top performers
            random_portion = max_rows - top_portion  # 30% random sample

            df_sorted = df.sort_values('investment_score', ascending=False)
            top_properties = df_sorted.head(top_portion)

            remaining_df = df_sorted.tail(len(df) - top_portion)
            if len(remaining_df) > random_portion:
                random_properties = remaining_df.sample(n=random_portion, random_state=42)
            else:
                random_properties = remaining_df

            return pd.concat([top_properties, random_properties]).sort_index()
        else:
            # Fallback to random sampling if no score column
            return df.sample(n=max_rows, random_state=42)


@smart_cache("table_column_config", ttl_seconds=300, cache_type="ui_configuration")
def _build_table_column_config(df: pd.DataFrame) -> Tuple[List[str], Dict[str, Any]]:
    """
    Efficiently build table column configuration.

    Args:
        df: DataFrame to build configuration for

    Returns:
        Tuple of (display_columns, column_config)
    """
    with performance_context("properties_table", "column_config_build"):
        display_columns = ["Select"]
        column_config = {
            "Select": st.column_config.CheckboxColumn(required=True)
        }

        # Column configuration mapping for performance
        column_mappings = {
            'rank': st.column_config.NumberColumn("Rank", format="%d", width="small"),
            'parcel_id': st.column_config.TextColumn("Parcel ID", width="medium"),
            'county': st.column_config.TextColumn("County", width="small"),
            'amount': st.column_config.NumberColumn("Price", format="$%.2f", width="small"),
            'acreage': st.column_config.NumberColumn("Acres", format="%.2f", width="small"),
            'price_per_acre': st.column_config.NumberColumn("$/Acre", format="$%.2f", width="small"),
            'water_score': st.column_config.NumberColumn("Water", format="%.1f", width="small"),
            'investment_score': st.column_config.NumberColumn("Score", format="%.1f", width="small"),
            'description': st.column_config.TextColumn("Description", width="large")
        }

        # Dynamically add columns that exist in DataFrame
        for col, config in column_mappings.items():
            if col in df.columns:
                display_columns.append(col)
                column_config[col] = config

        return display_columns, column_config


@monitor_performance("create_visualizations", include_memory=True)
@smart_cache("visualizations", ttl_seconds=300, cache_type="chart_data")
@ai_test_decorator("visualizations", "chart_generation")
def create_visualizations(df: pd.DataFrame):
    """
    Optimized visualization creation with advanced caching, progressive loading,
    and AI testability for complex chart generation.

    Args:
        df: Filtered DataFrame
    """
    try:
        if len(df) == 0:
            return

        # Memory optimization for large datasets
        check_memory_and_optimize()

        with performance_context("visualizations", "initialization"):
            st.subheader("ANALYTICS")

            # Optimize data for visualization
            df_viz = _prepare_data_for_visualization(df)

            # Progressive chart loading with loading indicators
            total_charts = 6
            chart_progress = st.progress(0)
            status_text = st.empty()

        # Create two columns for charts
        col1, col2 = st.columns(2)

        # Chart 1: Scatter plot
        with col1:
            with performance_context("visualizations", "scatter_plot"):
                chart_progress.progress(1/total_charts)
                status_text.text("Creating scatter plot...")

                fig_scatter = _create_scatter_plot(df_viz)
                if fig_scatter:
                    st.plotly_chart(fig_scatter, use_container_width=True)

        # Chart 2: Histogram
        with col2:
            with performance_context("visualizations", "histogram"):
                chart_progress.progress(2/total_charts)
                status_text.text("Creating price distribution...")

                fig_hist = _create_price_histogram(df_viz)
                if fig_hist:
                    st.plotly_chart(fig_hist, use_container_width=True)

        # Second row of visualizations
        col3, col4 = st.columns(2)

        # Chart 3: Bar chart
        with col3:
            with performance_context("visualizations", "county_bar_chart"):
                chart_progress.progress(3/total_charts)
                status_text.text("Creating county distribution...")

                fig_county = _create_county_bar_chart(df_viz)
                if fig_county:
                    st.plotly_chart(fig_county, use_container_width=True)

        # Chart 4: Box plot
        with col4:
            with performance_context("visualizations", "box_plot"):
                chart_progress.progress(4/total_charts)
                status_text.text("Creating score distribution...")

                fig_box = _create_investment_score_box_plot(df_viz)
                if fig_box:
                    st.plotly_chart(fig_box, use_container_width=True)

        # Third row for advanced charts
        st.markdown("---")
        st.subheader("Intelligence Analysis")
        col5, col6 = st.columns(2)

        # Chart 5: County heatmap
        with col5:
            with performance_context("visualizations", "county_heatmap"):
                chart_progress.progress(5/total_charts)
                status_text.text("Creating county heatmap...")

                heatmap_fig = create_county_heatmap(df_viz)
                st.plotly_chart(heatmap_fig, use_container_width=True)

        # Chart 6: Correlation heatmap
        with col6:
            with performance_context("visualizations", "correlation_heatmap"):
                chart_progress.progress(6/total_charts)
                status_text.text("Creating correlation analysis...")

                correlation_fig = create_correlation_heatmap(df_viz)
                st.plotly_chart(correlation_fig, use_container_width=True)

        # Complete progress
        chart_progress.progress(1.0)
        status_text.text("All visualizations loaded successfully!")
        time.sleep(0.5)  # Brief pause to show completion
        chart_progress.empty()
        status_text.empty()

        # Show visualization performance info if debug enabled
        if st.session_state.get('debug_checkbox', False):
            viz_info = {
                'Total Charts': total_charts,
                'Data Points': len(df_viz),
                'Memory Usage': f"{df_viz.memory_usage().sum() / 1024 / 1024:.1f} MB"
            }
            st.caption(f"Visualization Info: {viz_info}")

    except Exception as e:
        # Enhanced error handling with AI logging
        performance_monitor = get_performance_monitor()
        performance_monitor.record_metric("create_visualizations", "error", 1, {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "dataframe_shape": df.shape if df is not None else None
        })

        st.error(f"Error creating visualizations: {e}")


@smart_cache("visualization_data_prep", ttl_seconds=600, cache_type="data_processing")
def _prepare_data_for_visualization(df: pd.DataFrame, max_points: int = 2000) -> pd.DataFrame:
    """
    Optimize DataFrame for visualization performance by sampling large datasets.

    Args:
        df: DataFrame to optimize
        max_points: Maximum data points for optimal chart performance

    Returns:
        Optimized DataFrame for visualization
    """
    with performance_context("visualizations", "data_preparation"):
        if len(df) <= max_points:
            return optimize_dataframe(df, aggressive=False)

        # Intelligent sampling for visualizations
        if 'investment_score' in df.columns:
            # Stratified sampling to maintain distribution
            high_score = df[df['investment_score'] >= df['investment_score'].quantile(0.8)]
            mid_score = df[(df['investment_score'] >= df['investment_score'].quantile(0.4)) &
                          (df['investment_score'] < df['investment_score'].quantile(0.8))]
            low_score = df[df['investment_score'] < df['investment_score'].quantile(0.4)]

            # Sample proportionally
            n_high = min(len(high_score), int(max_points * 0.4))
            n_mid = min(len(mid_score), int(max_points * 0.4))
            n_low = min(len(low_score), max_points - n_high - n_mid)

            sampled_df = pd.concat([
                high_score.sample(n=n_high, random_state=42) if n_high > 0 else pd.DataFrame(),
                mid_score.sample(n=n_mid, random_state=42) if n_mid > 0 else pd.DataFrame(),
                low_score.sample(n=n_low, random_state=42) if n_low > 0 else pd.DataFrame()
            ])
        else:
            # Random sampling fallback
            sampled_df = df.sample(n=max_points, random_state=42)

        return optimize_dataframe(sampled_df, aggressive=False)


@smart_cache("scatter_plot_chart", ttl_seconds=300, cache_type="chart_generation")
def _create_scatter_plot(df: pd.DataFrame):
    """Create optimized scatter plot."""
    if 'price_per_acre' not in df.columns or 'acreage' not in df.columns:
        return None

    try:
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
        return fig_scatter
    except Exception:
        return None


@smart_cache("price_histogram_chart", ttl_seconds=300, cache_type="chart_generation")
def _create_price_histogram(df: pd.DataFrame):
    """Create optimized price distribution histogram."""
    if 'amount' not in df.columns:
        return None

    try:
        fig_hist = px.histogram(
            df,
            x='amount',
            nbins=20,
            title="Price Distribution",
            labels={'amount': 'Price ($)', 'count': 'Number of Properties'},
            color_discrete_sequence=[CHART_COLORS['primary']]
        )
        fig_hist.update_layout(height=400)
        return fig_hist
    except Exception:
        return None


@smart_cache("county_bar_chart", ttl_seconds=300, cache_type="chart_generation")
def _create_county_bar_chart(df: pd.DataFrame):
    """Create optimized county distribution bar chart."""
    if 'county' not in df.columns or df['county'].nunique() <= 1:
        return None

    try:
        county_counts = df['county'].value_counts().head(10)
        fig_county = px.bar(
            x=county_counts.index,
            y=county_counts.values,
            title="Properties by County (Top 10)",
            labels={'x': 'County', 'y': 'Number of Properties'},
            color_discrete_sequence=[CHART_COLORS['secondary']]
        )
        fig_county.update_layout(height=400)
        return fig_county
    except Exception:
        return None


@smart_cache("investment_box_plot_chart", ttl_seconds=300, cache_type="chart_generation")
def _create_investment_score_box_plot(df: pd.DataFrame):
    """Create optimized investment score box plot."""
    if 'investment_score' not in df.columns:
        return None

    try:
        water_label = df['water_score'].apply(
            lambda x: 'With Water Features' if x > 0 else 'No Water Features'
        ) if 'water_score' in df.columns else 'All Properties'

        fig_box = px.box(
            df,
            y='investment_score',
            x=water_label if 'water_score' in df.columns else None,
            title="Investment Score Distribution",
            labels={'investment_score': 'Investment Score'},
            color_discrete_sequence=[CHART_COLORS['water_features'], CHART_COLORS['no_water']]
        )
        fig_box.update_layout(height=400)
        return fig_box
    except Exception:
        return None


def main():
    """Main Streamlit application."""

    # Initialize session state early to prevent conflicts
    initialize_session_state()

    # Page title and description
    st.title("Alabama Auction Watcher")
    st.markdown("**Interactive dashboard for analyzing Alabama tax delinquent property auctions**")

    # Display legal disclaimer
    display_legal_disclaimer()

    # Create sidebar filters first
    filters = create_sidebar_filters()

    # Load data based on filters
    df = load_watchlist_data(filters)

    if len(df) == 0:
        st.warning("No properties match the current filters. Try adjusting the search criteria.")
        # Optionally, show a message encouraging to check the backend if the initial load is empty
        if not any(v for k, v in filters.items() if k not in ['price_range', 'acreage_range', 'min_investment_score'] and v):
             st.info(f"""
                If you expected data, please ensure the backend server is running.
                - **Backend URL:** `http://localhost:8001/api/v1/properties/`
                - **To start the backend:** `python start_backend_api.py`
             """)
        st.stop()

    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(["Dashboard", "Statewide Command", "Healthcare Banking", "Investment Portfolio", "County Expansion", "County Deep Dive", "Advanced Analytics", "Market Intelligence", "Application Assistant", "AI Testing"])

    with tab1:
        # Display results
        display_summary_metrics(df)

        # Add some spacing
        st.markdown("---")

        selected_df = display_properties_table(df)

        # Add some spacing
        st.markdown("---")

        # Display comparison view if properties are selected
        if not selected_df.empty:
            display_comparison_view(selected_df)
            st.markdown("---")

        create_visualizations(df)

        # Add some spacing
        st.markdown("---")

        # Single Property Analysis - Isolated in expander to prevent table interference
        with st.expander("SINGLE PROPERTY ANALYSIS", expanded=False):
            # Show table state preservation indicator
            selected_props = st.session_state.app_state.get('selected_properties', {})
            if selected_props.get('count', 0) > 0:
                st.success(f"✅ Table Selection Preserved: {selected_props['count']} properties selected")
                st.info("💡 **Tip:** Go to the **Application Assistant** tab to add these selected properties to your application queue for government form assistance.")

            if len(df) > 0:
                # Use unique key and isolated state to prevent table interference
                analysis_key = "single_property_analysis_selector"

                # Initialize analysis state separately
                if 'single_analysis_state' not in st.session_state:
                    st.session_state.single_analysis_state = {
                        'selected_parcel': None,
                        'last_selection_time': time.time()
                    }

                selected_parcel = st.selectbox(
                    "Select a Parcel for Detailed Analysis",
                    options=df['parcel_id'].unique(),
                    index=0,
                    key=analysis_key,
                    help="Select a property to view detailed radar chart analysis"
                )

                # Only update if selection actually changed to minimize reruns
                if selected_parcel != st.session_state.single_analysis_state.get('selected_parcel'):
                    st.session_state.single_analysis_state['selected_parcel'] = selected_parcel
                    st.session_state.single_analysis_state['last_selection_time'] = time.time()

                if selected_parcel:
                    # Create analysis in isolated container
                    with st.container():
                        property_data = df[df['parcel_id'] == selected_parcel].iloc[0]

                        # Display basic property info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Price", format_currency(property_data.get('amount', 0)))
                        with col2:
                            st.metric("Acreage", format_acreage(property_data.get('acreage', 0)))
                        with col3:
                            st.metric("Investment Score", format_score(property_data.get('investment_score', 0)))

                        # Radar chart
                        radar_chart = create_radar_chart(property_data)
                        st.plotly_chart(radar_chart, use_container_width=True)

                        # Additional property details
                        st.markdown("**Property Details:**")
                        st.write(f"**County:** {property_data.get('county', 'Unknown')}")
                        st.write(f"**Description:** {property_data.get('description', 'No description available')}")
                        if property_data.get('water_score', 0) > 0:
                            st.success(f"Water Features Score: {property_data.get('water_score', 0):.1f}")
            else:
                st.info("No properties to analyze in the current selection.")

    with tab2:
        display_statewide_command_center_component()

    with tab3:
        display_healthcare_land_banking_component()

    with tab4:
        display_investment_portfolio_component()

    with tab5:
        display_county_expansion_center_component()

    with tab6:
        county_deep_dive_view(df)

    with tab7:
        display_analytics_dashboard()

    with tab8:
        display_enhanced_market_intelligence_component()

    with tab9:
        display_application_assistant_component()

    with tab10:
        display_ai_testing_dashboard()


    # Footer information
    st.markdown("""
    <div class='footer-style'>
        <p><strong>Alabama Auction Watcher</strong> | Professional Property Investment Platform</p>
        <p>Always consult with legal and real estate professionals before investing</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
