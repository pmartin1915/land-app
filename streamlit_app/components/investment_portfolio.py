"""
Investment Portfolio Builder Component
Advanced cross-county property selection and portfolio optimization

This component provides:
- Unified view of top properties across all counties
- Investment budget tracking and optimization
- Bulk property selection with portfolio building
- County diversification analytics
- Portfolio-level ROI analysis
- Seamless integration with Application Assistant
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
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

def _initialize_portfolio_state():
    """Initialize portfolio session state with proper isolation."""
    if 'investment_portfolio' not in st.session_state:
        st.session_state.investment_portfolio = {
            'budget': 250000.0,  # Default budget
            'selected_properties': {},
            'portfolio_analysis': {},
            'diversification_settings': {
                'max_per_county': 0.4,  # Max 40% in any single county
                'min_counties': 3,      # Minimum county diversification
                'risk_tolerance': 'moderate'
            },
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

def load_all_properties_from_db() -> pd.DataFrame:
    """Load all properties directly from database as fallback."""
    try:
        import sqlite3

        # Find database file
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "alabama_auction_watcher.db"

        if not db_path.exists():
            logger.warning(f"Database not found at {db_path}")
            return pd.DataFrame()

        # Connect and query
        conn = sqlite3.connect(str(db_path))
        query = """
        SELECT * FROM properties
        WHERE investment_score IS NOT NULL
        ORDER BY investment_score DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        logger.info(f"Loaded {len(df)} properties from database fallback")
        return df

    except Exception as e:
        logger.error(f"Database fallback failed: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_all_properties() -> pd.DataFrame:
    """Load all properties from all counties with caching and database fallback."""
    try:
        url = get_api_base_url()
        headers = get_api_headers()

        # Get all properties without county filter
        params = {
            'skip': 0,
            'limit': 10000,  # Large limit to get all properties
            'sort_by': 'investment_score',
            'sort_order': 'desc'
        }

        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()

        # Handle paginated API response format
        if isinstance(data, dict) and 'properties' in data:
            properties = data['properties']
            if properties and len(properties) > 0:
                logger.info(f"Loaded {len(properties)} properties from API")
                return pd.DataFrame(properties)
        elif isinstance(data, list) and len(data) > 0:
            logger.info(f"Loaded {len(data)} properties from API")
            return pd.DataFrame(data)

        logger.warning("API returned empty or invalid data, using database fallback")
        return load_all_properties_from_db()

    except Exception as e:
        logger.warning(f"API request failed: {str(e)}, using database fallback")
        return load_all_properties_from_db()

def calculate_portfolio_metrics(selected_properties: Dict[str, Any], all_properties_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate comprehensive portfolio metrics."""
    if not selected_properties:
        return {}

    # Get selected property details
    selected_ids = list(selected_properties.keys())
    portfolio_df = all_properties_df[all_properties_df['id'].isin(selected_ids)].copy()

    if portfolio_df.empty:
        return {}

    # Basic metrics
    total_investment = portfolio_df['estimated_all_in_cost'].sum()
    total_properties = len(portfolio_df)
    avg_score = portfolio_df['investment_score'].mean()
    avg_price_per_acre = portfolio_df['price_per_acre'].mean()
    total_acreage = portfolio_df['acreage'].sum()

    # County diversification
    county_distribution = portfolio_df['county'].value_counts()
    county_percentages = (county_distribution / total_properties * 100).round(1)

    # Risk assessment
    score_std = portfolio_df['investment_score'].std()
    price_range = portfolio_df['amount'].max() - portfolio_df['amount'].min()

    # ROI estimation
    estimated_roi = avg_score * 2.5  # Conservative ROI estimate based on score

    return {
        'total_investment': total_investment,
        'total_properties': total_properties,
        'avg_score': avg_score,
        'avg_price_per_acre': avg_price_per_acre,
        'total_acreage': total_acreage,
        'county_distribution': county_distribution.to_dict(),
        'county_percentages': county_percentages.to_dict(),
        'diversification_score': min(len(county_distribution), 5) * 20,  # Max 100 for 5+ counties
        'risk_score': max(0, 100 - score_std * 10),  # Lower std = lower risk
        'estimated_roi': estimated_roi,
        'price_range': price_range
    }

def display_portfolio_header():
    """Display the portfolio header with key metrics."""
    st.title("Investment Portfolio Builder")
    st.markdown("**Build optimal property portfolios across all Alabama counties**")

    # Portfolio state
    portfolio_state = st.session_state.investment_portfolio

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Investment Budget",
            format_currency(portfolio_state['budget']),
            help="Your total investment budget"
        )

    with col2:
        selected_count = len(portfolio_state['selected_properties'])
        st.metric(
            "Selected Properties",
            f"{selected_count}",
            help="Number of properties in your portfolio"
        )

    with col3:
        if portfolio_state['portfolio_analysis']:
            total_investment = portfolio_state['portfolio_analysis'].get('total_investment', 0)
            remaining_budget = portfolio_state['budget'] - total_investment
            st.metric(
                "Remaining Budget",
                format_currency(remaining_budget),
                delta=f"{(remaining_budget/portfolio_state['budget']*100):.1f}% available",
                help="Budget remaining for additional properties"
            )
        else:
            st.metric("Remaining Budget", format_currency(portfolio_state['budget']))

    with col4:
        if portfolio_state['portfolio_analysis']:
            diversification_score = portfolio_state['portfolio_analysis'].get('diversification_score', 0)
            st.metric(
                "Diversification Score",
                f"{diversification_score}/100",
                help="Geographic diversification across counties"
            )
        else:
            st.metric("Diversification Score", "0/100")

def display_budget_controls():
    """Display budget and investment controls."""
    with st.expander("Investment Budget Settings", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_budget = st.number_input(
                "Total Investment Budget ($)",
                min_value=10000.0,
                max_value=5000000.0,
                value=st.session_state.investment_portfolio['budget'],
                step=10000.0,
                format="%.0f",
                help="Your total budget for property investments"
            )

            if new_budget != st.session_state.investment_portfolio['budget']:
                st.session_state.investment_portfolio['budget'] = new_budget
                st.rerun()

        with col2:
            # Investment strategy presets
            strategy = st.selectbox(
                "Investment Strategy",
                options=["Conservative", "Moderate", "Aggressive", "Custom"],
                index=1,
                help="Pre-configured investment strategies"
            )

            if strategy == "Conservative":
                max_per_property = st.slider("Max per Property (%)", 5, 25, 15)
                min_score = st.slider("Minimum Investment Score", 50, 100, 70)
            elif strategy == "Moderate":
                max_per_property = st.slider("Max per Property (%)", 10, 40, 25)
                min_score = st.slider("Minimum Investment Score", 30, 80, 50)
            elif strategy == "Aggressive":
                max_per_property = st.slider("Max per Property (%)", 15, 50, 35)
                min_score = st.slider("Minimum Investment Score", 20, 70, 30)
            else:  # Custom
                max_per_property = st.slider("Max per Property (%)", 5, 50, 25)
                min_score = st.slider("Minimum Investment Score", 10, 100, 40)

def display_top_properties_table(all_properties_df: pd.DataFrame) -> pd.DataFrame:
    """Display unified table of top properties across all counties."""
    st.subheader("Top Properties Across All Counties")

    if all_properties_df.empty:
        st.warning("No properties available. Ensure the backend is running and data is loaded.")
        return pd.DataFrame()

    # Filter and prepare data
    display_df = all_properties_df.copy()

    # Check if investment_score column exists
    if 'investment_score' not in display_df.columns:
        st.error("Investment scoring data not available. Please ensure the database has been properly populated with investment scores.")
        return pd.DataFrame()

    # Sort by investment score
    display_df = display_df.sort_values('investment_score', ascending=False)

    # Add portfolio selection column
    display_df['Select for Portfolio'] = False

    # Restore previous selections
    portfolio_state = st.session_state.investment_portfolio
    selected_ids = list(portfolio_state['selected_properties'].keys())
    if selected_ids:
        display_df.loc[display_df['id'].isin(selected_ids), 'Select for Portfolio'] = True

    # Display columns configuration
    column_config = {
        "Select for Portfolio": st.column_config.CheckboxColumn(
            "Select",
            help="Add to investment portfolio",
            default=False
        ),
        "rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
        "parcel_id": st.column_config.TextColumn("Parcel ID", width="medium"),
        "county": st.column_config.TextColumn("County", width="small"),
        "amount": st.column_config.NumberColumn("Price", format="$%.0f", width="small"),
        "acreage": st.column_config.NumberColumn("Acres", format="%.2f", width="small"),
        "price_per_acre": st.column_config.NumberColumn("$/Acre", format="$%.0f", width="small"),
        "investment_score": st.column_config.NumberColumn("Score", format="%.1f", width="small"),
        "estimated_all_in_cost": st.column_config.NumberColumn("All-in Cost", format="$%.0f", width="medium"),
        "water_score": st.column_config.NumberColumn("Water", format="%.1f", width="small"),
        "description": st.column_config.TextColumn("Description", width="large")
    }

    # Select display columns
    display_columns = [
        "Select for Portfolio", "rank", "parcel_id", "county", "amount",
        "acreage", "price_per_acre", "investment_score", "estimated_all_in_cost",
        "water_score", "description"
    ]

    # Filter display_df to only include columns that exist
    available_columns = [col for col in display_columns if col in display_df.columns]

    # Display all properties (no limit for full visibility)
    display_df_limited = display_df[available_columns]

    # Data editor for portfolio selection
    edited_df = st.data_editor(
        display_df_limited,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        key="portfolio_property_selector",
        height=600
    )

    return edited_df

def update_portfolio_selections(edited_df: pd.DataFrame, all_properties_df: pd.DataFrame):
    """Update portfolio selections based on user input."""
    if edited_df is None or edited_df.empty:
        return

    # Get selected properties
    selected_mask = edited_df.get('Select for Portfolio', pd.Series(dtype=bool))
    if selected_mask.any():
        selected_rows = edited_df[selected_mask]

        # Update session state
        portfolio_state = st.session_state.investment_portfolio
        portfolio_state['selected_properties'] = {}

        for _, row in selected_rows.iterrows():
            property_id = row.get('id')
            if property_id:
                portfolio_state['selected_properties'][property_id] = {
                    'parcel_id': row.get('parcel_id'),
                    'county': row.get('county'),
                    'amount': row.get('amount'),
                    'acreage': row.get('acreage'),
                    'investment_score': row.get('investment_score'),
                    'estimated_all_in_cost': row.get('estimated_all_in_cost'),
                    'selected_at': datetime.now().isoformat()
                }

        # Recalculate portfolio analysis
        portfolio_state['portfolio_analysis'] = calculate_portfolio_metrics(
            portfolio_state['selected_properties'],
            all_properties_df
        )
    else:
        # Clear selections if none selected
        st.session_state.investment_portfolio['selected_properties'] = {}
        st.session_state.investment_portfolio['portfolio_analysis'] = {}

def display_portfolio_analysis():
    """Display comprehensive portfolio analysis."""
    portfolio_state = st.session_state.investment_portfolio
    analysis = portfolio_state.get('portfolio_analysis', {})

    if not analysis:
        st.info("Select properties in the table above to see portfolio analysis")
        return

    st.subheader("Portfolio Analysis")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Investment",
            format_currency(analysis.get('total_investment', 0))
        )

    with col2:
        st.metric(
            "Average Score",
            format_score(analysis.get('avg_score', 0))
        )

    with col3:
        st.metric(
            "Total Acreage",
            format_acreage(analysis.get('total_acreage', 0))
        )

    with col4:
        st.metric(
            "Est. ROI",
            f"{analysis.get('estimated_roi', 0):.1f}%"
        )

    # Visualizations
    col_left, col_right = st.columns(2)

    with col_left:
        # County distribution pie chart
        county_dist = analysis.get('county_distribution', {})
        if county_dist:
            fig_pie = px.pie(
                values=list(county_dist.values()),
                names=list(county_dist.keys()),
                title="Portfolio Distribution by County",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        # Risk assessment gauge
        risk_score = analysis.get('risk_score', 50)
        diversification_score = analysis.get('diversification_score', 0)

        fig_gauge = go.Figure()

        fig_gauge.add_trace(go.Indicator(
            mode = "gauge+number+delta",
            value = risk_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Portfolio Risk Score"},
            delta = {'reference': 75},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))

        fig_gauge.update_layout(height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)

def add_properties_to_application_queue(selected_properties: Dict[str, Any], user_profile_id: str) -> Dict[str, Any]:
    """Add selected properties to Application Assistant queue."""
    try:
        url = f"{get_api_base_url().replace('/properties', '/applications')}"
        headers = get_api_headers()

        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }

        for prop_id, prop_data in selected_properties.items():
            try:
                # Add property to application queue
                add_url = f"{url}/properties/{prop_id}/application"
                params = {
                    'user_profile_id': user_profile_id,
                    'notes': f"Added from Investment Portfolio on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }

                response = requests.post(add_url, headers=headers, params=params, timeout=10)

                if response.status_code == 200:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Property {prop_data.get('parcel_id', prop_id)}: {response.text}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Property {prop_data.get('parcel_id', prop_id)}: {str(e)}")

        return results

    except Exception as e:
        return {
            'success': 0,
            'failed': len(selected_properties),
            'errors': [f"API Error: {str(e)}"]
        }

@st.cache_data(ttl=60)
def load_user_profiles() -> List[Dict[str, Any]]:
    """Load user profiles from Application Assistant."""
    try:
        url = f"{get_api_base_url().replace('/properties', '/applications')}/profiles"
        headers = get_api_headers()

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Failed to load user profiles: {e}")
        return []

def display_portfolio_actions():
    """Display portfolio action buttons and integration options."""
    portfolio_state = st.session_state.investment_portfolio
    selected_properties = portfolio_state.get('selected_properties', {})

    if not selected_properties:
        return

    st.subheader("Portfolio Actions")

    # Application Assistant Integration
    with st.expander("Add to Application Queue", expanded=True):
        st.markdown("**Seamlessly transfer your portfolio to Application Assistant**")

        # Load user profiles
        user_profiles = load_user_profiles()

        if user_profiles:
            profile_options = {f"{p['full_name']} ({p['email']})": p['id'] for p in user_profiles}

            col_a, col_b = st.columns([2, 1])

            with col_a:
                selected_profile = st.selectbox(
                    "Select User Profile",
                    options=list(profile_options.keys()),
                    help="Choose which profile to use for applications"
                )

            with col_b:
                if st.button("Add All to Queue", type="primary"):
                    if selected_profile:
                        profile_id = profile_options[selected_profile]

                        with st.spinner(f"Adding {len(selected_properties)} properties to application queue..."):
                            results = add_properties_to_application_queue(selected_properties, profile_id)

                        if results['success'] > 0:
                            st.success(f"Successfully added {results['success']} properties to application queue!")

                        if results['failed'] > 0:
                            st.warning(f"Failed to add {results['failed']} properties")
                            for error in results['errors']:
                                st.caption(f"Error: {error}")

                        # Clear cache to refresh data
                        st.cache_data.clear()

            # Show what will be added
            st.markdown("**Properties to be added:**")
            for i, (prop_id, prop_data) in enumerate(selected_properties.items(), 1):
                st.caption(f"{i}. {prop_data.get('parcel_id')} - {prop_data.get('county')} County - {format_currency(prop_data.get('estimated_all_in_cost', 0))}")

        else:
            st.warning("No user profiles found. Create a profile in the Application Assistant tab first.")
            if st.button("Go to Application Assistant"):
                st.switch_page("Application Assistant")

    # Additional Actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Portfolio ROI Analysis"):
            # Calculate detailed ROI for entire portfolio
            total_investment = sum(prop.get('estimated_all_in_cost', 0) for prop in selected_properties.values())
            avg_score = sum(prop.get('investment_score', 0) for prop in selected_properties.values()) / len(selected_properties)
            estimated_portfolio_roi = avg_score * 2.5  # Conservative estimate

            st.metric("Portfolio Investment", format_currency(total_investment))
            st.metric("Average Score", f"{avg_score:.1f}")
            st.metric("Estimated ROI", f"{estimated_portfolio_roi:.1f}%")

            if estimated_portfolio_roi > 100:
                st.success("Strong portfolio with high ROI potential!")
            elif estimated_portfolio_roi > 50:
                st.info("Solid portfolio with moderate returns expected")
            else:
                st.warning("Consider optimizing for higher-scoring properties")

    with col2:
        if st.button("Export Portfolio"):
            # Create detailed export data
            export_data = []
            for prop_id, prop_data in selected_properties.items():
                export_data.append({
                    'Property ID': prop_id,
                    'Parcel ID': prop_data.get('parcel_id'),
                    'County': prop_data.get('county'),
                    'Price': prop_data.get('amount'),
                    'Acreage': prop_data.get('acreage'),
                    'Investment Score': prop_data.get('investment_score'),
                    'Est. All-in Cost': prop_data.get('estimated_all_in_cost'),
                    'Selected Date': prop_data.get('selected_at', '')
                })

            if export_data:
                export_df = pd.DataFrame(export_data)
                csv_data = export_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"investment_portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Download portfolio as CSV for external analysis"
                )

    with col3:
        if st.button("Clear Portfolio"):
            if st.button("Confirm Clear", type="secondary"):
                st.session_state.investment_portfolio['selected_properties'] = {}
                st.session_state.investment_portfolio['portfolio_analysis'] = {}
                st.success("Portfolio cleared!")
                st.rerun()

def display_investment_portfolio():
    """Main investment portfolio component."""
    # Initialize state
    _initialize_portfolio_state()

    # Display header and metrics
    display_portfolio_header()

    # Budget controls
    display_budget_controls()

    st.markdown("---")

    # Load all properties
    all_properties_df = load_all_properties()

    if all_properties_df.empty:
        st.error("No properties loaded. Please ensure the backend API is running.")
        return

    # Display top properties table
    edited_df = display_top_properties_table(all_properties_df)

    # Update portfolio selections
    update_portfolio_selections(edited_df, all_properties_df)

    st.markdown("---")

    # Portfolio analysis
    display_portfolio_analysis()

    st.markdown("---")

    # Portfolio actions
    display_portfolio_actions()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <p><strong>Investment Portfolio Builder</strong> • Optimize your Alabama property investments</p>
        <p>Tip: Select properties to build diversified portfolios across multiple counties</p>
    </div>
    """, unsafe_allow_html=True)

# Export the main function
def display_investment_portfolio_component():
    """Export function for the investment portfolio component."""
    display_investment_portfolio()