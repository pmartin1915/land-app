"""
Statewide Property Command Center
The ultimate property discovery and selection engine for Alabama tax auctions

This component provides:
- Global ranking of ALL properties across all 67 counties
- Smart filter presets for instant property selection
- One-click selection tools (Top N, Fill Budget, Diversified Portfolio)
- Advanced power filtering and bulk operations
- Seamless integration with Investment Portfolio and Application Assistant
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import CHART_COLORS
from config.security import get_security_config, create_secure_headers
from scripts.utils import format_currency, format_acreage, format_score

logger = logging.getLogger(__name__)

def _initialize_command_center_state():
    """Initialize command center session state."""
    if 'statewide_command' not in st.session_state:
        st.session_state.statewide_command = {
            'selected_properties': {},
            'active_strategy': None,
            'filter_presets': {
                'current_preset': 'all',
                'custom_filters': {}
            },
            'bulk_selection': {
                'last_operation': None,
                'properties_selected': 0
            },
            'budget': 250000.0,
            'last_refresh': datetime.now()
        }

def get_api_headers() -> Dict[str, str]:
    """Get secure API headers for backend communication."""
    security_config = get_security_config()
    return create_secure_headers()

def get_api_base_url() -> str:
    """Get the API base URL for properties."""
    security_config = get_security_config()
    return f"{security_config.api_base_url}/properties"

@st.cache_data(ttl=300)
def load_all_properties_ranked() -> pd.DataFrame:
    """Load ALL properties from all counties, ranked by investment score."""
    try:
        url = get_api_base_url()
        headers = get_api_headers()

        # Get all properties without filters, sorted by investment score
        params = {
            'skip': 0,
            'limit': 20000,  # Very large limit to get everything
            'sort_by': 'investment_score',
            'sort_order': 'desc'
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        if data and len(data) > 0:
            df = pd.DataFrame(data)

            # Add global rank
            df['global_rank'] = range(1, len(df) + 1)

            # Ensure we have all necessary columns
            required_columns = [
                'id', 'parcel_id', 'county', 'amount', 'acreage', 'price_per_acre',
                'investment_score', 'water_score', 'estimated_all_in_cost', 'description'
            ]

            for col in required_columns:
                if col not in df.columns:
                    df[col] = None

            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"Failed to load all properties: {e}")
        st.error(f"Failed to load properties: {e}")
        return pd.DataFrame()

def calculate_statewide_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate comprehensive statewide statistics."""
    if df.empty:
        return {}

    stats = {
        'total_properties': len(df),
        'total_counties': df['county'].nunique(),
        'total_investment_value': df['estimated_all_in_cost'].sum(),
        'avg_investment_score': df['investment_score'].mean(),
        'top_10_percent_avg_score': df.head(int(len(df) * 0.1))['investment_score'].mean(),
        'properties_with_water': (df['water_score'] > 0).sum(),
        'water_percentage': ((df['water_score'] > 0).sum() / len(df)) * 100,
        'counties_represented': sorted(df['county'].unique()),
        'price_ranges': {
            'under_1k': (df['amount'] < 1000).sum(),
            'under_5k': (df['amount'] < 5000).sum(),
            'under_10k': (df['amount'] < 10000).sum(),
            'under_20k': (df['amount'] < 20000).sum()
        },
        'score_distribution': {
            'excellent': (df['investment_score'] >= 80).sum(),
            'very_good': ((df['investment_score'] >= 60) & (df['investment_score'] < 80)).sum(),
            'good': ((df['investment_score'] >= 40) & (df['investment_score'] < 60)).sum(),
            'fair': ((df['investment_score'] >= 20) & (df['investment_score'] < 40)).sum(),
            'poor': (df['investment_score'] < 20).sum()
        }
    }

    return stats

def display_statewide_header(stats: Dict[str, Any]):
    """Display the command center header with key statewide metrics."""
    st.title("Statewide Property Command Center")
    st.markdown("**The ultimate property discovery engine - ALL highest-scoring Alabama properties in one view**")

    if not stats:
        st.warning("No property data available. Ensure the backend is running and data is loaded.")
        return

    # Key metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total Properties",
            f"{stats['total_properties']:,}",
            help="All properties across Alabama counties"
        )

    with col2:
        st.metric(
            "Counties Covered",
            f"{stats['total_counties']}/67",
            help="Alabama counties with property data"
        )

    with col3:
        progress_to_3k = min(100, (stats['total_properties'] / 3000) * 100)
        st.metric(
            "Progress to 3K",
            f"{progress_to_3k:.1f}%",
            delta=f"{stats['total_properties'] - 3000} to goal" if stats['total_properties'] < 3000 else "Goal achieved!",
            help="Progress toward 3,000+ property goal"
        )

    with col4:
        st.metric(
            "Avg Score",
            f"{stats['avg_investment_score']:.1f}",
            delta=f"Top 10%: {stats['top_10_percent_avg_score']:.1f}",
            help="Average investment score across all properties"
        )

    with col5:
        st.metric(
            "Water Properties",
            f"{stats['properties_with_water']:,}",
            delta=f"{stats['water_percentage']:.1f}%",
            help="Properties with water features"
        )

def display_smart_filter_presets(df: pd.DataFrame) -> pd.DataFrame:
    """Display smart filter presets for instant property selection."""
    st.subheader("SMART FILTER PRESETS")
    st.markdown("**One-click filters to instantly find your ideal properties**")

    command_state = st.session_state.statewide_command

    # First row - General presets
    st.markdown("**General Presets**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Alabama's Top 50", type="primary", help="Highest scoring 50 properties statewide"):
            filtered_df = df.head(50)
            command_state['filter_presets']['current_preset'] = 'top_50'
            st.success(f"Selected top 50 properties (avg score: {filtered_df['investment_score'].mean():.1f})")
            return filtered_df

    with col2:
        if st.button("Water Properties", help="All properties with water features"):
            filtered_df = df[df['water_score'] > 0].copy()
            command_state['filter_presets']['current_preset'] = 'water_only'
            st.success(f"Found {len(filtered_df)} properties with water features")
            return filtered_df

    with col3:
        if st.button("Under $5K Steals", help="Best properties under $5,000"):
            filtered_df = df[df['amount'] < 5000].copy()
            command_state['filter_presets']['current_preset'] = 'under_5k'
            st.success(f"Found {len(filtered_df)} properties under $5,000")
            return filtered_df

    with col4:
        if st.button("Score 60+ Only", help="High-quality properties with score 60+"):
            filtered_df = df[df['investment_score'] >= 60].copy()
            command_state['filter_presets']['current_preset'] = 'high_score'
            st.success(f"Found {len(filtered_df)} high-scoring properties")
            return filtered_df

    # Second row - Land Banking Strategy
    st.markdown("**Land Banking Strategy (Perfect for Beginners)**")
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        if st.button("Beginner Land Banking", type="secondary", help="Conservative rural properties under $2K with water"):
            # Perfect for healthcare professional strategy
            filtered_df = df[
                (df['amount'] <= 2000) &
                (df['water_score'] > 0) &
                (df['acreage'] >= 2.0) &
                (df['investment_score'] >= 50) &
                (df['county'].isin(['Cullman', 'Walker', 'Talladega', 'DeKalb', 'Cherokee', 'Randolph']))
            ].copy()
            command_state['filter_presets']['current_preset'] = 'land_banking'
            st.success(f"Found {len(filtered_df)} beginner-friendly land banking opportunities!")
            if len(filtered_df) > 0:
                avg_price = filtered_df['amount'].mean()
                avg_acres = filtered_df['acreage'].mean()
                st.info(f"Avg price: ${avg_price:.0f} | Avg acreage: {avg_acres:.1f} acres")
            return filtered_df

    with col6:
        if st.button("Rural Water Gems", help="Rural properties 2-10 acres with water features"):
            filtered_df = df[
                (df['water_score'] > 0) &
                (df['acreage'] >= 2.0) &
                (df['acreage'] <= 10.0) &
                (df['amount'] <= 5000)
            ].copy()
            command_state['filter_presets']['current_preset'] = 'rural_water'
            st.success(f"Found {len(filtered_df)} rural water properties")
            return filtered_df

    with col7:
        if st.button("Healthcare Budget", help="Properties under $2K perfect for $5K-10K budget"):
            filtered_df = df[
                (df['amount'] <= 2000) &
                (df['investment_score'] >= 40) &
                (df['acreage'] >= 1.0)
            ].copy()
            command_state['filter_presets']['current_preset'] = 'healthcare_budget'
            st.success(f"Found {len(filtered_df)} budget-friendly properties")
            if len(filtered_df) > 0:
                total_for_5_props = filtered_df.head(5)['amount'].sum()
                st.info(f"Top 5 total cost: ${total_for_5_props:.0f} (fits in $5K budget!)")
            return filtered_df

    with col8:
        if st.button("Target Counties", help="Focus on Cullman, Walker, Talladega, DeKalb"):
            target_counties = ['Cullman', 'Walker', 'Talladega', 'DeKalb']
            filtered_df = df[df['county'].isin(target_counties)].copy()
            command_state['filter_presets']['current_preset'] = 'target_counties'
            st.success(f"Found {len(filtered_df)} properties in target counties")
            county_counts = filtered_df['county'].value_counts()
            st.info(f"Distribution: {dict(county_counts)}")
            return filtered_df

    # Third row - Investment Strategy
    st.markdown("**INVESTMENT STRATEGY**")
    col9, col10, col11, col12 = st.columns(4)

    with col9:
        if st.button("Quick Flips", help="High ROI potential under $10K"):
            filtered_df = df[(df['amount'] < 10000) & (df['investment_score'] >= 50)].copy()
            command_state['filter_presets']['current_preset'] = 'quick_flips'
            st.success(f"Found {len(filtered_df)} quick flip candidates")
            return filtered_df

    with col10:
        if st.button("Top 10%", help="Top 10% highest scoring properties"):
            top_10_count = max(1, int(len(df) * 0.1))
            filtered_df = df.head(top_10_count)
            command_state['filter_presets']['current_preset'] = 'top_10_percent'
            st.success(f"Selected top {top_10_count} properties (top 10%)")
            return filtered_df

    with col11:
        if st.button("Large Acreage", help="Properties with 5+ acres for land banking"):
            filtered_df = df[df['acreage'] >= 5.0].copy()
            command_state['filter_presets']['current_preset'] = 'large_acreage'
            st.success(f"Found {len(filtered_df)} properties with 5+ acres")
            return filtered_df

    with col12:
        if st.button("↻ Reset Filters", help="Reset to show all properties"):
            command_state['filter_presets']['current_preset'] = 'all'
            st.info("Showing all properties")
            return df

    # Current preset indicator
    current_preset = command_state['filter_presets'].get('current_preset', 'all')
    if current_preset != 'all':
        st.info(f"Active filter: {current_preset.replace('_', ' ').title()}")

    return df

def display_bulk_selection_tools(df: pd.DataFrame):
    """Display bulk selection tools for efficient property selection."""
    st.subheader("BULK SELECTION TOOLS")
    st.markdown("**Efficiently select multiple properties with smart tools**")

    command_state = st.session_state.statewide_command

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Select Top N Properties**")

        # Handle empty dataframe case
        df_len = len(df) if df is not None and not df.empty else 0
        max_properties = max(1, min(500, df_len))  # Ensure minimum of 1
        default_value = min(25, max_properties)  # Adjust default based on available data

        if df_len == 0:
            st.warning("No properties available. Load data first.")
            top_n = 1
        else:
            top_n = st.number_input(
                "Number of top properties",
                min_value=1,
                max_value=max_properties,
                value=default_value,
                step=5,
                help=f"Select the top N highest-scoring properties (max: {max_properties})"
            )

        if st.button(f"Select Top {top_n}", type="primary"):
            # Select top N properties
            selected_properties = {}
            for _, row in df.head(top_n).iterrows():
                prop_id = row['id']
                selected_properties[prop_id] = {
                    'parcel_id': row['parcel_id'],
                    'county': row['county'],
                    'amount': row['amount'],
                    'acreage': row['acreage'],
                    'investment_score': row['investment_score'],
                    'estimated_all_in_cost': row['estimated_all_in_cost'],
                    'global_rank': row['global_rank'],
                    'selected_at': datetime.now().isoformat(),
                    'selection_method': f'top_{top_n}'
                }

            command_state['selected_properties'] = selected_properties
            command_state['bulk_selection']['last_operation'] = f'top_{top_n}'
            command_state['bulk_selection']['properties_selected'] = len(selected_properties)

            total_cost = sum(prop.get('estimated_all_in_cost', 0) for prop in selected_properties.values())
            avg_score = sum(prop.get('investment_score', 0) for prop in selected_properties.values()) / len(selected_properties)

            st.success(f"Selected top {len(selected_properties)} properties!")
            st.info(f"Total investment: {format_currency(total_cost)} | Avg score: {avg_score:.1f}")

    with col2:
        st.markdown("**Fill Budget Optimally**")
        budget = st.number_input(
            "Available budget ($)",
            min_value=1000.0,
            max_value=2000000.0,
            value=command_state['budget'],
            step=5000.0,
            format="%.0f",
            help="Maximum amount you want to invest"
        )

        command_state['budget'] = budget

        if st.button("Fill Budget", type="primary"):
            # Greedy algorithm to fill budget with highest-scoring properties
            selected_properties = {}
            running_total = 0.0

            for _, row in df.iterrows():
                prop_cost = row.get('estimated_all_in_cost', 0) or row.get('amount', 0)
                if prop_cost and running_total + prop_cost <= budget:
                    prop_id = row['id']
                    selected_properties[prop_id] = {
                        'parcel_id': row['parcel_id'],
                        'county': row['county'],
                        'amount': row['amount'],
                        'acreage': row['acreage'],
                        'investment_score': row['investment_score'],
                        'estimated_all_in_cost': prop_cost,
                        'global_rank': row['global_rank'],
                        'selected_at': datetime.now().isoformat(),
                        'selection_method': 'budget_fill'
                    }
                    running_total += prop_cost

            command_state['selected_properties'] = selected_properties
            command_state['bulk_selection']['last_operation'] = 'budget_fill'
            command_state['bulk_selection']['properties_selected'] = len(selected_properties)

            avg_score = sum(prop.get('investment_score', 0) for prop in selected_properties.values()) / len(selected_properties) if selected_properties else 0
            budget_utilization = (running_total / budget) * 100

            st.success(f"Selected {len(selected_properties)} properties within budget!")
            st.info(f"Budget used: {format_currency(running_total)} ({budget_utilization:.1f}%) | Avg score: {avg_score:.1f}")

    with col3:
        st.markdown("**DIVERSIFIED PORTFOLIO**")
        min_counties = st.slider(
            "Minimum counties",
            min_value=2,
            max_value=min(10, df['county'].nunique()),
            value=4,
            help="Minimum number of counties for diversification"
        )

        max_per_county = st.slider(
            "Max % per county",
            min_value=10,
            max_value=50,
            value=30,
            help="Maximum percentage in any single county"
        )

        if st.button("Build Diversified", type="primary"):
            # Build diversified portfolio across counties
            selected_properties = {}
            county_counts = {}

            # Calculate max properties per county
            target_total = 25  # Target portfolio size
            max_props_per_county = max(1, int(target_total * (max_per_county / 100)))

            # Select properties ensuring diversification
            for _, row in df.iterrows():
                county = row['county']
                county_count = county_counts.get(county, 0)

                # Skip if this county is full
                if county_count >= max_props_per_county:
                    continue

                # Add property
                prop_id = row['id']
                selected_properties[prop_id] = {
                    'parcel_id': row['parcel_id'],
                    'county': row['county'],
                    'amount': row['amount'],
                    'acreage': row['acreage'],
                    'investment_score': row['investment_score'],
                    'estimated_all_in_cost': row.get('estimated_all_in_cost', 0),
                    'global_rank': row['global_rank'],
                    'selected_at': datetime.now().isoformat(),
                    'selection_method': 'diversified'
                }

                county_counts[county] = county_count + 1

                # Stop if we have enough counties and properties
                if len(county_counts) >= min_counties and len(selected_properties) >= target_total:
                    break

            command_state['selected_properties'] = selected_properties
            command_state['bulk_selection']['last_operation'] = 'diversified'
            command_state['bulk_selection']['properties_selected'] = len(selected_properties)

            total_cost = sum(prop.get('estimated_all_in_cost', 0) for prop in selected_properties.values())
            avg_score = sum(prop.get('investment_score', 0) for prop in selected_properties.values()) / len(selected_properties) if selected_properties else 0

            st.success(f"Built diversified portfolio: {len(selected_properties)} properties across {len(county_counts)} counties!")
            st.info(f"Total investment: {format_currency(total_cost)} | Avg score: {avg_score:.1f}")

def display_advanced_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Display advanced filtering controls."""
    with st.expander("ADVANCED FILTERS", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            # Score filter
            score_range = st.slider(
                "Investment Score Range",
                min_value=0.0,
                max_value=100.0,
                value=(0.0, 100.0),
                step=1.0,
                help="Filter by investment score range"
            )

            # Price filter
            max_price = min(50000.0, df['amount'].max() if not df.empty else 50000.0)
            price_range = st.slider(
                "Price Range ($)",
                min_value=0.0,
                max_value=max_price,
                value=(0.0, max_price),
                step=100.0,
                format="$%.0f",
                help="Filter by property price"
            )

        with col2:
            # County selection
            counties = ['All'] + sorted(df['county'].unique().tolist()) if not df.empty else ['All']
            selected_counties = st.multiselect(
                "Select Counties",
                options=counties,
                default=['All'],
                help="Filter by specific counties"
            )

            # Acreage filter
            max_acreage = min(100.0, df['acreage'].max() if not df.empty and df['acreage'].notna().any() else 100.0)
            acreage_range = st.slider(
                "Acreage Range",
                min_value=0.0,
                max_value=max_acreage,
                value=(0.0, max_acreage),
                step=0.1,
                help="Filter by property acreage"
            )

        with col3:
            # Water features
            water_only = st.checkbox("Water Features Only", help="Show only properties with water features")

            # Price per acre filter
            if not df.empty and df['price_per_acre'].notna().any():
                max_ppa_raw = df['price_per_acre'].quantile(0.95)
                # Ensure valid values and reasonable bounds
                max_ppa = min(50000.0, max(1000.0, max_ppa_raw)) if pd.notna(max_ppa_raw) else 10000.0

                price_per_acre_max = st.number_input(
                    "Max Price Per Acre ($)",
                    min_value=0.0,
                    max_value=max_ppa,
                    value=max_ppa,
                    step=1000.0,
                    help="Maximum price per acre"
                )
            else:
                price_per_acre_max = 50000.0

        if st.button("Apply Advanced Filters"):
            # Apply all filters
            filtered_df = df.copy()

            # Score filter
            filtered_df = filtered_df[
                (filtered_df['investment_score'] >= score_range[0]) &
                (filtered_df['investment_score'] <= score_range[1])
            ]

            # Price filter
            filtered_df = filtered_df[
                (filtered_df['amount'] >= price_range[0]) &
                (filtered_df['amount'] <= price_range[1])
            ]

            # County filter
            if 'All' not in selected_counties and selected_counties:
                filtered_df = filtered_df[filtered_df['county'].isin(selected_counties)]

            # Acreage filter
            filtered_df = filtered_df[
                (filtered_df['acreage'].fillna(0) >= acreage_range[0]) &
                (filtered_df['acreage'].fillna(0) <= acreage_range[1])
            ]

            # Water features filter
            if water_only:
                filtered_df = filtered_df[filtered_df['water_score'] > 0]

            # Price per acre filter
            filtered_df = filtered_df[
                filtered_df['price_per_acre'].fillna(0) <= price_per_acre_max
            ]

            st.session_state.statewide_command['filter_presets']['current_preset'] = 'advanced'
            st.success(f"Applied advanced filters. Showing {len(filtered_df)} properties.")

            return filtered_df

    return df

def display_property_table_with_selection(df: pd.DataFrame) -> pd.DataFrame:
    """Display the main property table with selection capabilities."""
    if df.empty:
        st.warning("No properties match the current filters.")
        return df

    st.subheader(f"PROPERTY RESULTS ({len(df):,} properties)")

    # Add selection column
    df_display = df.copy()
    df_display['Select'] = False

    # Restore previous selections
    command_state = st.session_state.statewide_command
    selected_ids = list(command_state.get('selected_properties', {}).keys())
    if selected_ids:
        df_display.loc[df_display['id'].isin(selected_ids), 'Select'] = True

    # Column configuration
    column_config = {
        "Select": st.column_config.CheckboxColumn("Select", default=False),
        "global_rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
        "parcel_id": st.column_config.TextColumn("Parcel ID", width="medium"),
        "county": st.column_config.TextColumn("County", width="small"),
        "amount": st.column_config.NumberColumn("Price", format="$%.0f", width="small"),
        "acreage": st.column_config.NumberColumn("Acres", format="%.2f", width="small"),
        "price_per_acre": st.column_config.NumberColumn("$/Acre", format="$%.0f", width="small"),
        "investment_score": st.column_config.NumberColumn("Score", format="%.1f", width="small"),
        "water_score": st.column_config.NumberColumn("Water", format="%.1f", width="small"),
        "estimated_all_in_cost": st.column_config.NumberColumn("All-in Cost", format="$%.0f", width="medium"),
        "description": st.column_config.TextColumn("Description", width="large")
    }

    # Select display columns
    display_columns = [
        "Select", "global_rank", "parcel_id", "county", "amount", "acreage",
        "price_per_acre", "investment_score", "water_score", "estimated_all_in_cost", "description"
    ]

    # Filter to only include existing columns
    available_columns = [col for col in display_columns if col in df_display.columns]

    # Display all properties (no limit for full visibility)
    df_limited = df_display[available_columns]

    # Data editor
    edited_df = st.data_editor(
        df_limited,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        key="statewide_property_selector",
        height=600
    )

    return edited_df

def update_command_center_selections(edited_df: pd.DataFrame, original_df: pd.DataFrame):
    """Update command center selections based on user input."""
    if edited_df is None or edited_df.empty:
        return

    # Get selected properties
    selected_mask = edited_df.get('Select', pd.Series(dtype=bool))
    if selected_mask.any():
        selected_rows = edited_df[selected_mask]

        # Update session state
        command_state = st.session_state.statewide_command
        command_state['selected_properties'] = {}

        for _, row in selected_rows.iterrows():
            prop_id = row.get('id')
            if prop_id:
                # Get full property data from original dataframe
                full_row = original_df[original_df['id'] == prop_id].iloc[0] if not original_df[original_df['id'] == prop_id].empty else row

                command_state['selected_properties'][prop_id] = {
                    'parcel_id': full_row.get('parcel_id'),
                    'county': full_row.get('county'),
                    'amount': full_row.get('amount'),
                    'acreage': full_row.get('acreage'),
                    'investment_score': full_row.get('investment_score'),
                    'estimated_all_in_cost': full_row.get('estimated_all_in_cost'),
                    'global_rank': full_row.get('global_rank'),
                    'selected_at': datetime.now().isoformat(),
                    'selection_method': 'manual'
                }

        command_state['bulk_selection']['last_operation'] = 'manual_selection'
        command_state['bulk_selection']['properties_selected'] = len(command_state['selected_properties'])
    else:
        # Clear selections if none selected
        st.session_state.statewide_command['selected_properties'] = {}

def display_selection_summary():
    """Display summary of current selections."""
    command_state = st.session_state.statewide_command
    selected_properties = command_state.get('selected_properties', {})

    if not selected_properties:
        return

    st.subheader(f"CURRENT SELECTION ({len(selected_properties)} properties)")

    # Calculate summary statistics
    total_cost = sum(prop.get('estimated_all_in_cost', 0) for prop in selected_properties.values())
    avg_score = sum(prop.get('investment_score', 0) for prop in selected_properties.values()) / len(selected_properties)
    counties_involved = len(set(prop.get('county') for prop in selected_properties.values()))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Investment", format_currency(total_cost))

    with col2:
        st.metric("Average Score", f"{avg_score:.1f}")

    with col3:
        st.metric("Counties Involved", counties_involved)

    with col4:
        budget_used = (total_cost / command_state['budget']) * 100 if command_state['budget'] > 0 else 0
        st.metric("Budget Used", f"{budget_used:.1f}%")

    # Action buttons
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("→ Send to Investment Portfolio", type="primary"):
            # Transfer to Investment Portfolio
            if 'investment_portfolio' not in st.session_state:
                st.session_state.investment_portfolio = {
                    'selected_properties': {},
                    'portfolio_analysis': {},
                    'budget': command_state['budget']
                }

            st.session_state.investment_portfolio['selected_properties'] = selected_properties.copy()
            st.success(f"Transferred {len(selected_properties)} properties to Investment Portfolio!")
            st.info("Go to the Investment Portfolio tab to continue with application processing.")

    with col_b:
        if st.button("Export Selection"):
            # Create export data
            export_data = []
            for prop_id, prop_data in selected_properties.items():
                export_data.append({
                    'Global Rank': prop_data.get('global_rank'),
                    'Property ID': prop_id,
                    'Parcel ID': prop_data.get('parcel_id'),
                    'County': prop_data.get('county'),
                    'Price': prop_data.get('amount'),
                    'Acreage': prop_data.get('acreage'),
                    'Investment Score': prop_data.get('investment_score'),
                    'Est. All-in Cost': prop_data.get('estimated_all_in_cost'),
                    'Selection Method': prop_data.get('selection_method'),
                    'Selected At': prop_data.get('selected_at')
                })

            if export_data:
                export_df = pd.DataFrame(export_data)
                csv_data = export_df.to_csv(index=False)
                st.download_button(
                    label="↓ Download CSV",
                    data=csv_data,
                    file_name=f"statewide_selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

    with col_c:
        if st.button("× Clear Selection"):
            command_state['selected_properties'] = {}
            st.success("Selection cleared!")
            st.rerun()

def display_statewide_command_center():
    """Main statewide command center component."""
    # Initialize state
    _initialize_command_center_state()

    # Load all properties
    df = load_all_properties_ranked()

    if df.empty:
        st.error("No properties loaded. Please ensure the backend API is running and data is available.")
        return

    # Calculate and display statewide statistics
    stats = calculate_statewide_stats(df)
    display_statewide_header(stats)

    st.markdown("---")

    # Smart filter presets
    df_filtered = display_smart_filter_presets(df)

    st.markdown("---")

    # Bulk selection tools
    display_bulk_selection_tools(df_filtered)

    st.markdown("---")

    # Advanced filters
    df_final = display_advanced_filters(df_filtered)

    st.markdown("---")

    # Property table with selection
    edited_df = display_property_table_with_selection(df_final)

    # Update selections
    update_command_center_selections(edited_df, df)

    st.markdown("---")

    # Selection summary and actions
    display_selection_summary()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <p><strong>Statewide Property Command Center</strong> • Discover Alabama's highest-scoring tax auction properties</p>
        <p><strong>Tip:</strong> Use smart presets for instant selection, then bulk tools for optimal portfolio building</p>
    </div>
    """, unsafe_allow_html=True)

# Export the main function
def display_statewide_command_center_component():
    """Export function for the statewide command center component."""
    display_statewide_command_center()