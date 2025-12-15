import streamlit as st
import pandas as pd
import time

def _initialize_comparison_state():
    """Initialize isolated comparison state to prevent interference with main table."""
    if 'comparison_state' not in st.session_state:
        st.session_state.comparison_state = {
            'active_comparison': False,
            'compared_properties': [],
            'comparison_data': None,
            'last_comparison_time': None
        }

def display_comparison_view(df: pd.DataFrame):
    """
    Display a side-by-side comparison of selected properties with isolated state management.
    This prevents interference with the main properties table state.

    Args:
        df: DataFrame containing the properties to compare.
    """
    # Initialize isolated state
    _initialize_comparison_state()

    # Set comparison as active in isolated state
    st.session_state.comparison_state['active_comparison'] = True
    st.session_state.comparison_state['last_comparison_time'] = time.time()

    st.subheader("Property Comparison")

    if len(df) < 2:
        st.info("Select 2 or more properties from the table above to compare them.")
        # Mark comparison as inactive when no properties selected
        st.session_state.comparison_state['active_comparison'] = False
        return

    # Create columns for each property
    cols = st.columns(len(df))

    # Define the attributes to display for comparison
    attributes = {
        "parcel_id": "Parcel ID",
        "county": "County",
        "amount": "Price",
        "acreage": "Acreage",
        "price_per_acre": "$/Acre",
        "investment_score": "Investment Score",
        "county_market_score": "County Market Score",
        "geographic_score": "Geographic Score",
        "market_timing_score": "Market Timing Score",
        "total_description_score": "Description Score",
        "road_access_score": "Road Access Score",
        "water_score": "Water Score"
    }

    for i, (index, row) in enumerate(df.iterrows()):
        with cols[i]:
            st.markdown(f"#### Property {i+1}")
            st.markdown(f"**Parcel ID:** {row.get('parcel_id', 'N/A')}")

            for key, label in attributes.items():
                if key != "parcel_id": # Already displayed
                    value = row.get(key, "N/A")
                    # Basic formatting for now
                    if isinstance(value, float):
                        if "score" in key.lower() or "acre" in key.lower():
                            st.metric(label=label, value=f"{value:.2f}")
                        else:
                            st.metric(label=label, value=f"${value:,.2f}")
                    else:
                        st.metric(label=label, value=value)

    # Store comparison data in isolated state
    st.session_state.comparison_state['compared_properties'] = df.to_dict('records')
    st.session_state.comparison_state['comparison_data'] = {
        'property_count': len(df),
        'comparison_completed': True,
        'timestamp': time.time()
    }

    # Add a reset comparison button to clear state if needed
    if st.button("Clear Comparison", type="secondary", key="clear_comparison_btn"):
        st.session_state.comparison_state['active_comparison'] = False
        st.session_state.comparison_state['compared_properties'] = []
        st.session_state.comparison_state['comparison_data'] = None
        st.rerun()
