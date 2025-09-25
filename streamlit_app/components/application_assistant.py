"""
Property Application Assistant UI Component
Complete end-to-end workflow for organizing property application data

LEGAL COMPLIANCE NOTICE:
This component provides data organization assistance only.
All government applications must be manually reviewed and submitted by the user.
No automated form submission or security bypass is performed.
"""

import streamlit as st
import pandas as pd
import requests
import json
import io
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import time
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.security import get_security_config, create_secure_headers
from config.enhanced_error_handling import smart_retry, get_user_friendly_error_message
from scripts.utils import format_currency, format_acreage, format_score

logger = logging.getLogger(__name__)

# Alabama Counties for dropdown
ALABAMA_COUNTIES = [
    'Autauga', 'Baldwin', 'Barbour', 'Bibb', 'Blount', 'Bullock', 'Butler', 'Calhoun',
    'Chambers', 'Cherokee', 'Chilton', 'Choctaw', 'Clarke', 'Clay', 'Cleburne', 'Coffee',
    'Colbert', 'Conecuh', 'Coosa', 'Covington', 'Crenshaw', 'Cullman', 'Dale', 'Dallas',
    'DeKalb', 'Elmore', 'Escambia', 'Etowah', 'Fayette', 'Franklin', 'Geneva', 'Greene',
    'Hale', 'Henry', 'Houston', 'Jackson', 'Jefferson', 'Lamar', 'Lauderdale', 'Lawrence',
    'Lee', 'Limestone', 'Lowndes', 'Macon', 'Madison', 'Marengo', 'Marion', 'Marshall',
    'Mobile', 'Monroe', 'Montgomery', 'Morgan', 'Perry', 'Pickens', 'Pike', 'Randolph',
    'Russell', 'St. Clair', 'Shelby', 'Sumter', 'Talladega', 'Tallapoosa', 'Tuscaloosa',
    'Walker', 'Washington', 'Wilcox', 'Winston'
]

APPLICATION_STATUSES = [
    'draft', 'ready', 'submitted', 'price_received', 'accepted', 'rejected', 'completed'
]

def _initialize_application_state():
    """Initialize isolated application assistant state."""
    if 'application_assistant' not in st.session_state:
        st.session_state.application_assistant = {
            'active_profile': None,
            'selected_properties': {},
            'form_data_cache': {},
            'roi_cache': {},
            'last_refresh': datetime.now()
        }

def get_api_headers() -> Dict[str, str]:
    """Get secure API headers for backend communication."""
    security_config = get_security_config()
    return create_secure_headers()

def get_api_base_url() -> str:
    """Get the API base URL."""
    security_config = get_security_config()
    return f"{security_config.api_base_url}/applications"

@st.cache_data(ttl=300)
@smart_retry(max_retries=3, base_delay=1.0)
def load_user_profiles() -> List[Dict[str, Any]]:
    """Load all user profiles from the backend with enhanced error handling."""
    try:
        url = f"{get_api_base_url()}/profiles"
        headers = get_api_headers()

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        user_msg, suggestions = get_user_friendly_error_message(e)
        logger.error(f"Failed to load user profiles: {user_msg}")
        return []

@smart_retry(max_retries=2, base_delay=1.5)
def create_user_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user profile with enhanced error handling."""
    try:
        url = f"{get_api_base_url()}/profiles"
        headers = get_api_headers()

        response = requests.post(url, headers=headers, json=profile_data, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        user_msg, suggestions = get_user_friendly_error_message(e)
        logger.error(f"Failed to create user profile: {user_msg}")
        return {"success": False, "error": user_msg, "suggestions": suggestions}

def add_property_to_queue(property_id: str, user_profile_id: str, notes: str = "") -> Dict[str, Any]:
    """Add a property to the application queue."""
    try:
        url = f"{get_api_base_url()}/properties/{property_id}/application"
        headers = get_api_headers()
        params = {"user_profile_id": user_profile_id}
        if notes:
            params["notes"] = notes

        response = requests.post(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Failed to add property to queue: {e}")
        return {"success": False, "error": str(e)}

@st.cache_data(ttl=60)
def load_user_applications(profile_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load applications for a user profile."""
    try:
        url = f"{get_api_base_url()}/profiles/{profile_id}/applications"
        headers = get_api_headers()
        params = {}
        if status_filter:
            params["status"] = status_filter

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Failed to load user applications: {e}")
        return []

def get_property_roi(property_id: str) -> Dict[str, Any]:
    """Get ROI calculation for a property."""
    try:
        url = f"{get_api_base_url()}/properties/{property_id}/roi"
        headers = get_api_headers()

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Failed to get property ROI: {e}")
        return {}

def get_application_form_data(application_id: str) -> Dict[str, Any]:
    """Get pre-populated form data for an application."""
    try:
        url = f"{get_api_base_url()}/applications/{application_id}/form-data"
        headers = get_api_headers()

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Failed to get form data: {e}")
        return {}

def update_application_status(application_id: str, status: str, final_price: Optional[float] = None, notes: str = "") -> Dict[str, Any]:
    """Update application status."""
    try:
        url = f"{get_api_base_url()}/applications/{application_id}/status"
        headers = get_api_headers()
        params = {"status": status}
        if final_price:
            params["final_price"] = final_price
        if notes:
            params["notes"] = notes

        response = requests.put(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.error(f"Failed to update application status: {e}")
        return {"success": False, "error": str(e)}

def display_legal_disclaimer():
    """Display the professional legal compliance banner."""
    st.markdown("""
    <div class="disclaimer-banner">
        <h4>LEGAL COMPLIANCE NOTICE</h4>
        <p><strong>Data Organization Assistance Only:</strong> This tool helps organize your property application data for manual submission to Alabama government offices.
        <strong>No automated form submission is performed.</strong> You must manually review all information and submit applications yourself.</p>
        <p><strong>Alabama Redemption Period:</strong> Properties purchased at tax auctions are subject to a <strong>3-year redemption period</strong>
        during which the original owner can reclaim the property. Always consult with legal and real estate professionals.</p>
    </div>
    """, unsafe_allow_html=True)

def display_user_profile_section():
    """Display user profile management section."""
    st.subheader("USER PROFILE MANAGEMENT")

    # Load existing profiles
    profiles = load_user_profiles()

    col1, col2 = st.columns([2, 1])

    with col1:
        if profiles:
            profile_options = {f"{p['full_name']} ({p['email']})": p for p in profiles}
            selected_profile_key = st.selectbox(
                "Select Profile for Applications",
                options=["Create New Profile"] + list(profile_options.keys()),
                key="profile_selector"
            )

            if selected_profile_key != "Create New Profile":
                st.session_state.application_assistant['active_profile'] = profile_options[selected_profile_key]
                profile = profile_options[selected_profile_key]

                # Display profile info
                st.success(f"Active Profile: {profile['full_name']}")
                with st.expander("Profile Details"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Email:** {profile['email']}")
                        st.write(f"**Phone:** {profile['phone']}")
                        st.write(f"**Address:** {profile['address']}, {profile['city']}, {profile['state']} {profile['zip_code']}")
                    with col_b:
                        st.write(f"**Max Investment:** {format_currency(profile['max_investment_amount']) if profile['max_investment_amount'] else 'Not set'}")
                        st.write(f"**Acreage Range:** {profile['min_acreage'] or 0} - {profile['max_acreage'] or 'No limit'} acres")
                        st.write(f"**Preferred Counties:** {', '.join(profile['preferred_counties']) if profile['preferred_counties'] else 'None specified'}")
        else:
            st.info("No profiles found. Create your first profile below.")
            st.session_state.application_assistant['active_profile'] = None

    with col2:
        if st.button("↻ Refresh Profiles", type="secondary"):
            st.cache_data.clear()
            st.rerun()

    # Create new profile form
    if not profiles or (profiles and st.checkbox("Create New Profile", key="create_new_profile")):
        st.markdown("---")
        st.subheader("CREATE NEW PROFILE")

        with st.form("new_profile_form"):
            col_a, col_b = st.columns(2)

            with col_a:
                full_name = st.text_input("Full Legal Name*", placeholder="John Doe")
                email = st.text_input("Email Address*", placeholder="john@example.com")
                phone = st.text_input("Phone Number*", placeholder="(555) 123-4567")
                address = st.text_input("Street Address*", placeholder="123 Main St")

            with col_b:
                city = st.text_input("City*", placeholder="Birmingham")
                state = st.text_input("State*", value="Alabama")
                zip_code = st.text_input("ZIP Code*", placeholder="35203")
                max_investment = st.number_input("Max Investment Amount ($)", min_value=0.0, value=50000.0, step=1000.0)

            col_c, col_d = st.columns(2)
            with col_c:
                min_acreage = st.number_input("Minimum Acreage", min_value=0.0, value=0.0, step=0.1)
                max_acreage = st.number_input("Maximum Acreage (0 = no limit)", min_value=0.0, value=0.0, step=1.0)

            with col_d:
                preferred_counties = st.multiselect("Preferred Counties", options=ALABAMA_COUNTIES, default=[])

            submitted = st.form_submit_button("Create Profile", type="primary")

            if submitted:
                if all([full_name, email, phone, address, city, state, zip_code]):
                    profile_data = {
                        "full_name": full_name,
                        "email": email,
                        "phone": phone,
                        "address": address,
                        "city": city,
                        "state": state,
                        "zip_code": zip_code,
                        "max_investment_amount": max_investment if max_investment > 0 else None,
                        "min_acreage": min_acreage if min_acreage > 0 else None,
                        "max_acreage": max_acreage if max_acreage > 0 else None,
                        "preferred_counties": preferred_counties
                    }

                    result = create_user_profile(profile_data)
                    if result.get("success"):
                        st.success(f"Profile created successfully for {full_name}!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        suggestions = result.get('suggestions', [])
                        st.error(f"Failed to create profile: {error_msg}")
                        if suggestions:
                            st.info(f"Suggestions: {'; '.join(suggestions)}")
                else:
                    st.error("Please fill in all required fields marked with *")

def display_property_selection_section():
    """Display property selection and queue management."""
    active_profile = st.session_state.application_assistant.get('active_profile')

    if not active_profile:
        st.warning("Please select or create a user profile first.")
        return

    st.subheader("PROPERTY APPLICATION QUEUE")

    # Load current applications
    applications = load_user_applications(active_profile['id'])

    if applications:
        st.markdown(f"**Current Applications for {active_profile['full_name']}:**")

        # Create applications DataFrame
        apps_data = []
        for app in applications:
            apps_data.append({
                "ID": app['id'],
                "Parcel": app['parcel_number'],
                "County": app['county'],
                "Price": format_currency(app['amount']) if app['amount'] else "N/A",
                "Acreage": format_acreage(app['acreage']) if app['acreage'] else "N/A",
                "Score": format_score(app['investment_score']) if app['investment_score'] else "N/A",
                "Status": app['status'].title(),
                "Created": app['created_at'][:10] if app['created_at'] else "N/A"
            })

        if apps_data:
            apps_df = pd.DataFrame(apps_data)

            # Status filter
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    options=["All"] + [s.title() for s in APPLICATION_STATUSES],
                    key="status_filter"
                )

            with col2:
                if st.button("↻ Refresh Applications"):
                    st.cache_data.clear()
                    st.rerun()

            # Display filtered applications
            if status_filter != "All":
                filtered_apps = [app for app in applications if app['status'] == status_filter.lower()]
            else:
                filtered_apps = applications

            # Applications table with actions
            for i, app in enumerate(filtered_apps):
                with st.expander(f"{app['parcel_number']} - {app['county']} County ({app['status'].title()})", expanded=False):
                    col_a, col_b, col_c = st.columns([2, 1, 1])

                    with col_a:
                        st.write(f"**Property:** {app['description'] or 'No description'}")
                        st.write(f"**Price:** {format_currency(app['amount']) if app['amount'] else 'N/A'}")
                        st.write(f"**Acreage:** {format_acreage(app['acreage']) if app['acreage'] else 'N/A'}")
                        st.write(f"**Investment Score:** {format_score(app['investment_score']) if app['investment_score'] else 'N/A'}")
                        if app['notes']:
                            st.write(f"**Notes:** {app['notes']}")

                    with col_b:
                        # ROI Calculator Button
                        if st.button(f"Calculate ROI", key=f"roi_{app['id']}"):
                            roi_data = get_property_roi(app['property_id'])
                            if roi_data:
                                st.session_state.application_assistant['roi_cache'][app['id']] = roi_data

                        # Display cached ROI
                        if app['id'] in st.session_state.application_assistant.get('roi_cache', {}):
                            roi = st.session_state.application_assistant['roi_cache'][app['id']]
                            st.success(f"ROI: {roi.get('roi_percentage', 0):.1f}%")
                            st.write(f"Est. Equity: {format_currency(roi.get('estimated_equity', 0))}")

                    with col_c:
                        # Form Data Button
                        if st.button(f"Generate Form Data", key=f"form_{app['id']}"):
                            form_data = get_application_form_data(app['id'])
                            if form_data:
                                st.session_state.application_assistant['form_data_cache'][app['id']] = form_data

                        # Status Update
                        new_status = st.selectbox(
                            "Update Status",
                            options=APPLICATION_STATUSES,
                            index=APPLICATION_STATUSES.index(app['status']),
                            key=f"status_{app['id']}"
                        )

                        if new_status != app['status']:
                            if st.button(f"Update Status", key=f"update_{app['id']}"):
                                result = update_application_status(app['id'], new_status)
                                if result.get("success"):
                                    st.success("Status updated!")
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(f"Failed: {result.get('error')}")
    else:
        st.info("No applications found. Add properties from the main dashboard.")

    # Add new property section
    st.markdown("---")
    st.subheader("ADD PROPERTIES TO QUEUE")
    st.info("**Tip:** Go to the Main Dashboard tab, select properties using the checkboxes, then return here to add them to your application queue.")

    # Check if user has selected properties in the main app
    main_app_state = st.session_state.get('app_state', {})
    selected_properties = main_app_state.get('selected_properties', {})

    if selected_properties and selected_properties.get('count', 0) > 0:
        st.success(f"Found {selected_properties['count']} selected properties from Main Dashboard")

        # Show preview of selected properties
        property_data = selected_properties.get('property_data', {})
        if property_data:
            st.markdown("**Selected Properties Preview:**")
            for i, (property_id, prop_data) in enumerate(property_data.items(), 1):
                with st.expander(f"{i}. {prop_data.get('parcel_id', 'Unknown')} - {prop_data.get('county', 'Unknown')} County", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Amount:** {format_currency(prop_data.get('amount', 0))}")
                        st.write(f"**Acreage:** {format_acreage(prop_data.get('acreage', 0))}")
                    with col2:
                        st.write(f"**Investment Score:** {format_score(prop_data.get('investment_score', 0))}")
                        st.write(f"**Estimated Cost:** {format_currency(prop_data.get('estimated_all_in_cost', 0))}")

        # Property addition form
        with st.form("add_properties_form"):
            notes = st.text_area("Notes (optional)", placeholder="Any specific notes about these properties...")
            submitted = st.form_submit_button("Add Selected Properties to Queue", type="primary")

            if submitted:
                # Extract property data from selected properties
                property_data = selected_properties.get('property_data', {})

                if not property_data:
                    st.error("No property data found. Please select properties from the Main Dashboard first.")
                    return

                # Process each selected property
                successful_adds = 0
                failed_adds = []

                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, (property_id, prop_data) in enumerate(property_data.items()):
                    progress = (i + 1) / len(property_data)
                    progress_bar.progress(progress)
                    status_text.text(f"Adding property {i + 1} of {len(property_data)}: {prop_data.get('parcel_id', 'Unknown')}")

                    # Add property to queue
                    result = add_property_to_queue(property_id, active_profile['id'], notes)

                    if result.get("success"):
                        successful_adds += 1
                    else:
                        failed_adds.append(f"{prop_data.get('parcel_id', property_id)}: {result.get('error', 'Unknown error')}")

                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()

                # Show results
                if successful_adds > 0:
                    st.success(f"Successfully added {successful_adds} properties to application queue!")
                    if successful_adds == len(property_data):
                        st.balloons()  # Celebrate complete success

                if failed_adds:
                    st.error(f"Failed to add {len(failed_adds)} properties:")
                    for error in failed_adds:
                        st.caption(f"• {error}")

                # Clear cache and refresh
                if successful_adds > 0:
                    st.cache_data.clear()
                    time.sleep(1)  # Brief delay to show results
                    st.rerun()

    # Manual property addition
    with st.expander("MANUAL PROPERTY ADDITION (Advanced)"):
        with st.form("manual_add_form"):
            property_id = st.text_input("Property ID", placeholder="Enter property ID from main dashboard")
            notes = st.text_area("Notes", placeholder="Optional notes about this property")
            submitted = st.form_submit_button("Add Property")

            if submitted and property_id:
                result = add_property_to_queue(property_id, active_profile['id'], notes)
                if result.get("success"):
                    st.success("Property added to queue!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Failed to add property: {result.get('error', 'Unknown error')}")

def display_roi_calculator_section():
    """Display detailed ROI calculator."""
    st.subheader("ROI CALCULATOR & INVESTMENT ANALYSIS")

    # Check for cached ROI data
    roi_cache = st.session_state.application_assistant.get('roi_cache', {})

    if roi_cache:
        st.markdown("**Recent ROI Calculations:**")

        for app_id, roi_data in roi_cache.items():
            with st.expander(f"ROI Analysis - Property {roi_data.get('property_id', 'Unknown')}", expanded=True):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Minimum Bid",
                        format_currency(roi_data.get('minimum_bid', 0))
                    )
                    st.metric(
                        "Estimated Fees",
                        format_currency(roi_data.get('estimated_fees', 0))
                    )
                    st.metric(
                        "Total Investment",
                        format_currency(roi_data.get('estimated_total_cost', 0))
                    )

                with col2:
                    st.metric(
                        "Estimated Market Value",
                        format_currency(roi_data.get('estimated_market_value', 0)) if roi_data.get('estimated_market_value') else "N/A"
                    )
                    st.metric(
                        "Estimated Equity",
                        format_currency(roi_data.get('estimated_equity', 0)) if roi_data.get('estimated_equity') else "N/A"
                    )
                    st.metric(
                        "ROI Percentage",
                        f"{roi_data.get('roi_percentage', 0):.1f}%" if roi_data.get('roi_percentage') else "N/A"
                    )

                with col3:
                    st.metric(
                        "Risk Score",
                        f"{roi_data.get('risk_score', 50):.1f}/100"
                    )
                    st.metric(
                        "Confidence Level",
                        roi_data.get('confidence_level', 'Unknown')
                    )

                    # Redemption period info
                    if roi_data.get('redemption_period_ends'):
                        redemption_date = datetime.fromisoformat(roi_data['redemption_period_ends'].replace('Z', '+00:00'))
                        st.write(f"**Redemption Ends:** {redemption_date.strftime('%B %d, %Y')}")

                # Investment recommendation
                roi_percentage = roi_data.get('roi_percentage', 0)
                if roi_percentage and roi_percentage > 100:
                    st.success(f"**Strong Investment Opportunity** - {roi_percentage:.1f}% ROI potential")
                elif roi_percentage and roi_percentage > 50:
                    st.info(f"**Moderate Investment Opportunity** - {roi_percentage:.1f}% ROI potential")
                elif roi_percentage and roi_percentage > 0:
                    st.warning(f"**Marginal Investment** - {roi_percentage:.1f}% ROI potential")
                else:
                    st.error("**High Risk Investment** - Limited ROI data available")
    else:
        st.info("Calculate ROI for properties in your application queue to see detailed analysis here.")

def display_form_data_section():
    """Display form data generation and export."""
    st.subheader("APPLICATION FORM DATA")

    # Check for cached form data
    form_cache = st.session_state.application_assistant.get('form_data_cache', {})

    if form_cache:
        st.markdown("**Generated Form Data:**")

        for app_id, form_data in form_cache.items():
            with st.expander(f"Form Data - Application {app_id}", expanded=True):

                # Legal disclaimer
                st.warning("**LEGAL NOTICE:** This data is for manual copy-paste into Alabama state forms only. You must manually review and submit all applications.")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Applicant Information:**")
                    st.text_input("Application Date", value=form_data.get('application_date', ''), disabled=True)
                    st.text_input("Full Name", value=form_data.get('applicant_name', ''), disabled=True)
                    st.text_input("Email", value=form_data.get('email', ''), disabled=True)
                    st.text_input("Phone", value=form_data.get('phone', ''), disabled=True)
                    st.text_input("Address", value=form_data.get('address', ''), disabled=True)
                    st.text_input("City, State ZIP", value=f"{form_data.get('city', '')}, {form_data.get('state', '')} {form_data.get('zip_code', '')}", disabled=True)

                with col2:
                    st.markdown("**Property Information:**")
                    st.text_input("Parcel Number", value=form_data.get('parcel_number', ''), disabled=True)
                    st.text_input("Property Description", value=form_data.get('property_description', ''), disabled=True)
                    st.text_input("Assessed Name", value=form_data.get('assessed_name', ''), disabled=True)
                    st.text_input("Our Estimated Value", value=format_currency(form_data.get('our_estimated_value', 0)), disabled=True)
                    st.text_input("Investment Score", value=format_score(form_data.get('investment_score', 0)), disabled=True)

                # Export options
                st.markdown("---")
                st.markdown("**Export Options:**")

                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    # Text export
                    form_text = f"""
APPLICATION FORM DATA
Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

APPLICANT INFORMATION:
Name: {form_data.get('applicant_name', '')}
Email: {form_data.get('email', '')}
Phone: {form_data.get('phone', '')}
Address: {form_data.get('address', '')}
City, State ZIP: {form_data.get('city', '')}, {form_data.get('state', '')} {form_data.get('zip_code', '')}

PROPERTY INFORMATION:
Parcel Number: {form_data.get('parcel_number', '')}
Description: {form_data.get('property_description', '')}
Assessed Name: {form_data.get('assessed_name', '')}
Our Estimated Value: {format_currency(form_data.get('our_estimated_value', 0))}
Investment Score: {format_score(form_data.get('investment_score', 0))}

LEGAL NOTICE: This data is for manual copy-paste into Alabama state forms only.
User must manually review and submit all applications.
                    """

                    st.download_button(
                        "↓ Download Text",
                        data=form_text,
                        file_name=f"application_form_data_{app_id}.txt",
                        mime="text/plain"
                    )

                with col_b:
                    # CSV export
                    csv_data = {
                        'Field': ['Application Date', 'Applicant Name', 'Email', 'Phone', 'Address', 'City', 'State', 'ZIP Code',
                                 'Parcel Number', 'Property Description', 'Assessed Name', 'Estimated Value', 'Investment Score'],
                        'Value': [form_data.get('application_date', ''), form_data.get('applicant_name', ''),
                                 form_data.get('email', ''), form_data.get('phone', ''), form_data.get('address', ''),
                                 form_data.get('city', ''), form_data.get('state', ''), form_data.get('zip_code', ''),
                                 form_data.get('parcel_number', ''), form_data.get('property_description', ''),
                                 form_data.get('assessed_name', ''), format_currency(form_data.get('our_estimated_value', 0)),
                                 format_score(form_data.get('investment_score', 0))]
                    }

                    csv_df = pd.DataFrame(csv_data)
                    csv_buffer = io.StringIO()
                    csv_df.to_csv(csv_buffer, index=False)

                    st.download_button(
                        "↓ Download CSV",
                        data=csv_buffer.getvalue(),
                        file_name=f"application_form_data_{app_id}.csv",
                        mime="text/csv"
                    )

                with col_c:
                    # Clear cache button
                    if st.button(f"× Clear Form Data", key=f"clear_{app_id}"):
                        if app_id in st.session_state.application_assistant['form_data_cache']:
                            del st.session_state.application_assistant['form_data_cache'][app_id]
                        st.rerun()
    else:
        st.info("Generate form data for applications in your queue to see exportable data here.")

def display_application_assistant():
    """Main application assistant component."""
    # Initialize state
    _initialize_application_state()

    # Display legal disclaimer
    display_legal_disclaimer()

    st.title("Property Application Assistant")
    st.markdown("**Complete workflow for organizing property application data for manual government submission**")

    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["User Profiles", "Application Queue", "ROI Calculator", "Form Data"])

    with tab1:
        display_user_profile_section()

    with tab2:
        display_property_selection_section()

    with tab3:
        display_roi_calculator_section()

    with tab4:
        display_form_data_section()

    # Footer with additional legal notices
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <p><strong>IMPORTANT LEGAL REMINDERS:</strong></p>
        <p>• All applications must be manually submitted to Alabama State Land Commissioner office</p>
        <p>• This tool provides data organization assistance only - no automated submission</p>
        <p>• Always consult with legal and real estate professionals before investing</p>
        <p>• Alabama tax deed properties have a 3-year redemption period</p>
    </div>
    """, unsafe_allow_html=True)

# Main export function
def display_application_assistant_component():
    """Export function for the application assistant component."""
    display_application_assistant()