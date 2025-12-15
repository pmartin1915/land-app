"""
Healthcare Professional Land Banking Component
Specialized tools and education for healthcare professionals entering Alabama land banking

This component provides:
- Conservative investment strategy guidance
- $5K-10K budget optimization tools
- Rural land appreciation tracking
- Legal compliance education
- "Set it and forget it" portfolio management
- Risk assessment for healthcare professionals
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
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

def _initialize_healthcare_banking_state():
    """Initialize healthcare land banking session state."""
    if 'healthcare_banking' not in st.session_state:
        st.session_state.healthcare_banking = {
            'budget': 5000.0,
            'risk_tolerance': 'conservative',
            'investment_timeline': '10_years',
            'properties_target': 3,
            'completed_education': {
                'legal_basics': False,
                'tax_deed_process': False,
                'due_diligence': False,
                'portfolio_management': False
            },
            'property_tracker': {},
            'annual_budget_plan': {},
            'last_refresh': datetime.now()
        }

def display_healthcare_professional_header():
    """Display header specifically for healthcare professionals."""
    st.title("Healthcare Professional Land Banking")
    st.markdown("**Conservative rural land investment strategy designed for busy healthcare professionals**")

    # Special welcome message
    st.info("""
    **Welcome, Healthcare Professional!** This tool is designed specifically for healthcare workers who want to build
    long-term wealth through conservative Alabama land banking while maintaining focus on their demanding careers.
    """)

    # Quick stats about healthcare professional advantages
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Recommended Budget",
            "$5K - $10K",
            help="Conservative starting budget for healthcare professionals"
        )

    with col2:
        st.metric(
            "Time Commitment",
            "2-3 hrs/month",
            help="Minimal time investment for 'set it and forget it' strategy"
        )

    with col3:
        st.metric(
            "Target Timeline",
            "10+ years",
            help="Long-term appreciation strategy"
        )

def display_education_center():
    """Display educational resources for healthcare professionals."""
    st.subheader("Land Banking Education Center")
    st.markdown("**Complete your education before investing - just like clinical practice!**")

    healthcare_state = st.session_state.healthcare_banking
    completed_education = healthcare_state['completed_education']

    # Education progress tracker
    total_modules = len(completed_education)
    completed_modules = sum(completed_education.values())
    progress_percentage = (completed_modules / total_modules) * 100

    st.progress(progress_percentage / 100, text=f"Education Progress: {completed_modules}/{total_modules} modules completed")

    # Education modules
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Core Education Modules**")

        # Module 1: Legal Basics
        with st.expander("Module 1: Alabama Tax Deed Legal Basics", expanded=not completed_education['legal_basics']):
            st.markdown("""
            **Learning Objectives:**
            - Understand Alabama's 3-year redemption period
            - Learn about property rights during redemption
            - Understand tax obligations as new owner

            **Key Points:**
            - **3-Year Wait:** You cannot take possession for 3 years
            - **Tax Responsibility:** You must pay property taxes during redemption
            - **Redemption Risk:** Original owner can reclaim property by paying back taxes + interest
            - **Documentation:** Keep all purchase and tax payment records

            **Alabama Code References:**
            - Title 40, Chapter 10 - Tax Sales
            - Section 40-10-28 - Redemption period
            - Section 40-10-30 - Certificate of purchase
            """)

            if st.button("Mark Module 1 Complete", key="module_1"):
                healthcare_state['completed_education']['legal_basics'] = True
                st.success("Module 1 completed! You understand the legal basics.")
                st.rerun()

        # Module 2: Tax Deed Process
        with st.expander("Module 2: Tax Deed Investment Process", expanded=not completed_education['tax_deed_process']):
            st.markdown("""
            **The Step-by-Step Process:**

            1. **Property Research** (Use your platform!)
               - Filter for rural water properties under $2K
               - Check investment scores and county data
               - Review property descriptions carefully

            2. **Due Diligence**
               - Google Earth satellite view
               - County GIS system research
               - Physical site visit (always!)
               - Title research at courthouse

            3. **Application Process**
               - Submit interest form to Alabama Department of Revenue
               - Wait for minimum price notification
               - Decide whether to proceed at that price
               - Submit payment if accepted

            4. **Post-Purchase**
               - Pay annual property taxes
               - Monitor property condition
               - Track redemption period
               - Plan long-term strategy
            """)

            if st.button("Mark Module 2 Complete", key="module_2"):
                healthcare_state['completed_education']['tax_deed_process'] = True
                st.success("Module 2 completed! You understand the investment process.")
                st.rerun()

    with col2:
        st.markdown("**Practical Application**")

        # Module 3: Due Diligence
        with st.expander("Module 3: Due Diligence Checklist", expanded=not completed_education['due_diligence']):
            st.markdown("""
            **Your Pre-Purchase Checklist:**

            **Online Research:**
            - [ ] Google Earth satellite view (water features, access roads)
            - [ ] County GIS system (zoning, flood zones, utilities)
            - [ ] Property tax history (no liens or complications)
            - [ ] Deed records (clear ownership chain)

            **Physical Inspection:**
            - [ ] Drive to property location
            - [ ] Verify road access (public vs. private)
            - [ ] Check for water features (creeks, ponds)
            - [ ] Look for obvious issues (wetlands, slopes, debris)
            - [ ] Take photos and GPS coordinates

            **Financial Analysis:**
            - [ ] Calculate annual property taxes
            - [ ] Estimate 10-year carrying costs
            - [ ] Research comparable land sales
            - [ ] Confirm budget fit (max $2K per property)

            **Legal Verification:**
            - [ ] Confirm clear title at courthouse
            - [ ] Verify no environmental restrictions
            - [ ] Check zoning limitations
            - [ ] Understand access rights
            """)

            if st.button("Mark Module 3 Complete", key="module_3"):
                healthcare_state['completed_education']['due_diligence'] = True
                st.success("Module 3 completed! You know how to research properties.")
                st.rerun()

        # Module 4: Portfolio Management
        with st.expander("Module 4: 'Set It and Forget It' Portfolio Management", expanded=not completed_education['portfolio_management']):
            st.markdown("""
            **Annual Management Tasks (Minimal Time):**

            **January - Tax Planning:**
            - [ ] Pay property taxes (set up auto-pay if possible)
            - [ ] Update tax records for deductions
            - [ ] Review property assessments

            **Spring - Property Inspection:**
            - [ ] Drive by all properties (make it a fun day trip!)
            - [ ] Take photos for insurance records
            - [ ] Check for any issues or trespassing
            - [ ] Update property condition notes

            **Summer - Market Analysis:**
            - [ ] Check comparable land sales in area
            - [ ] Monitor local development/growth
            - [ ] Assess appreciation trends

            **Fall - Portfolio Review:**
            - [ ] Calculate annual returns
            - [ ] Plan next year's acquisitions
            - [ ] Consider selling if needed
            - [ ] Update investment strategy

            **Emergency Management:**
            - Keep contact info for: County tax office, local real estate agent, attorney
            - Budget $200-500/year for unexpected costs
            - Maintain detailed records for each property
            """)

            if st.button("Mark Module 4 Complete", key="module_4"):
                healthcare_state['completed_education']['portfolio_management'] = True
                st.success("Module 4 completed! You're ready to manage a portfolio.")
                st.rerun()

    # Education completion reward
    if all(completed_education.values()):
        st.success("**Congratulations!** You've completed all education modules and are ready to start investing!")
        st.balloons()

def display_budget_optimizer():
    """Display budget optimization tools for healthcare professionals."""
    st.subheader("Healthcare Professional Budget Optimizer")
    st.markdown("**Optimize your $5K-10K budget for maximum land banking success**")

    healthcare_state = st.session_state.healthcare_banking

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Investment Parameters**")

        # Budget settings
        budget = st.slider(
            "Total Investment Budget ($)",
            min_value=1000,
            max_value=20000,
            value=int(healthcare_state['budget']),
            step=500,
            help="Your total budget for land banking"
        )
        healthcare_state['budget'] = float(budget)

        # Risk tolerance
        risk_tolerance = st.selectbox(
            "Risk Tolerance",
            options=['conservative', 'moderate', 'aggressive'],
            index=['conservative', 'moderate', 'aggressive'].index(healthcare_state['risk_tolerance']),
            help="Conservative: Under $1.5K per property, Moderate: Under $2.5K, Aggressive: Under $5K"
        )
        healthcare_state['risk_tolerance'] = risk_tolerance

        # Investment timeline
        timeline = st.selectbox(
            "Investment Timeline",
            options=['5_years', '10_years', '15_years', '20_years'],
            index=['5_years', '10_years', '15_years', '20_years'].index(healthcare_state['investment_timeline']),
            help="How long you plan to hold properties"
        )
        healthcare_state['investment_timeline'] = timeline

        # Target number of properties
        target_properties = st.slider(
            "Target Number of Properties",
            min_value=1,
            max_value=10,
            value=healthcare_state['properties_target'],
            help="How many properties you want to acquire"
        )
        healthcare_state['properties_target'] = target_properties

    with col2:
        st.markdown("**Budget Analysis**")

        # Calculate budget allocation
        if risk_tolerance == 'conservative':
            max_per_property = min(1500, budget // target_properties)
        elif risk_tolerance == 'moderate':
            max_per_property = min(2500, budget // target_properties)
        else:  # aggressive
            max_per_property = min(5000, budget // target_properties)

        # Budget breakdown
        property_budget = max_per_property * target_properties
        emergency_reserve = budget * 0.2  # 20% emergency reserve
        remaining_budget = budget - property_budget - emergency_reserve

        st.metric("Max Per Property", format_currency(max_per_property))
        st.metric("Property Budget", format_currency(property_budget))
        st.metric("Emergency Reserve", format_currency(emergency_reserve))

        if remaining_budget > 0:
            st.metric("Remaining Budget", format_currency(remaining_budget), delta="Available for expansion")
        else:
            st.metric("Budget Shortfall", format_currency(abs(remaining_budget)), delta="Reduce targets or increase budget")

        # Timeline projections
        timeline_years = int(timeline.split('_')[0])

        # Conservative appreciation estimates
        if timeline_years <= 5:
            expected_appreciation = 0.05  # 5% annually
        elif timeline_years <= 10:
            expected_appreciation = 0.07  # 7% annually
        else:
            expected_appreciation = 0.08  # 8% annually

        # Calculate projections
        future_value = property_budget * ((1 + expected_appreciation) ** timeline_years)
        total_return = future_value - property_budget
        roi_percentage = (total_return / property_budget) * 100

        st.markdown("**Projected Returns**")
        st.metric("Projected Portfolio Value", format_currency(future_value))
        st.metric("Total Projected Return", format_currency(total_return))
        st.metric("Total ROI", f"{roi_percentage:.1f}%")

def display_property_tracker():
    """Display property tracking for healthcare professionals."""
    st.subheader("Your Land Banking Portfolio Tracker")
    st.markdown("**Track your properties with minimal time investment**")

    healthcare_state = st.session_state.healthcare_banking
    property_tracker = healthcare_state['property_tracker']

    if not property_tracker:
        st.info("**Getting Started:** Use the Statewide Command Center to find properties, then add them here for tracking.")

        # Quick add property form
        with st.expander("Add Your First Property", expanded=True):
            with st.form("add_property_form"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    parcel_id = st.text_input("Parcel ID", help="From your platform or county records")
                    county = st.selectbox("County", options=['Cullman', 'Walker', 'Talladega', 'DeKalb', 'Cherokee', 'Randolph', 'Other'])
                    purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, max_value=5000.0, step=100.0)

                with col2:
                    acreage = st.number_input("Acreage", min_value=0.1, max_value=50.0, step=0.1)
                    water_features = st.checkbox("Has Water Features")
                    purchase_date = st.date_input("Purchase Date", value=datetime.now().date())

                with col3:
                    annual_taxes = st.number_input("Annual Property Taxes ($)", min_value=0.0, max_value=1000.0, step=10.0)
                    estimated_value = st.number_input("Estimated Current Value ($)", min_value=0.0, step=100.0)
                    notes = st.text_area("Notes", placeholder="Access roads, special features, etc.")

                submitted = st.form_submit_button("Add Property to Portfolio", type="primary")

                if submitted and parcel_id and county and purchase_price > 0:
                    property_id = f"{county}_{parcel_id}"
                    property_tracker[property_id] = {
                        'parcel_id': parcel_id,
                        'county': county,
                        'purchase_price': purchase_price,
                        'acreage': acreage,
                        'water_features': water_features,
                        'purchase_date': purchase_date.isoformat(),
                        'annual_taxes': annual_taxes,
                        'estimated_value': estimated_value or purchase_price,
                        'notes': notes,
                        'redemption_end_date': (purchase_date + timedelta(days=365*3)).isoformat(),
                        'added_date': datetime.now().isoformat()
                    }

                    st.success(f"Added {parcel_id} to your portfolio!")
                    st.rerun()

    else:
        # Display existing properties
        st.markdown(f"**Portfolio Summary: {len(property_tracker)} properties**")

        # Portfolio metrics
        total_investment = sum(prop['purchase_price'] for prop in property_tracker.values())
        total_acreage = sum(prop['acreage'] for prop in property_tracker.values())
        annual_taxes = sum(prop['annual_taxes'] for prop in property_tracker.values())
        water_properties = sum(1 for prop in property_tracker.values() if prop['water_features'])

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Investment", format_currency(total_investment))

        with col2:
            st.metric("Total Acreage", format_acreage(total_acreage))

        with col3:
            st.metric("Annual Taxes", format_currency(annual_taxes))

        with col4:
            st.metric("Water Properties", f"{water_properties}/{len(property_tracker)}")

        # Property table
        property_data = []
        for prop_id, prop in property_tracker.items():
            redemption_date = datetime.fromisoformat(prop['redemption_end_date'])
            days_to_redemption = (redemption_date - datetime.now()).days

            property_data.append({
                'Parcel ID': prop['parcel_id'],
                'County': prop['county'],
                'Purchase Price': format_currency(prop['purchase_price']),
                'Acreage': format_acreage(prop['acreage']),
                'Water': 'Yes' if prop['water_features'] else 'No',
                'Annual Taxes': format_currency(prop['annual_taxes']),
                'Days to Redemption': days_to_redemption if days_to_redemption > 0 else 'Expired',
                'Status': 'Redemption Period' if days_to_redemption > 0 else 'Deed Available'
            })

        if property_data:
            df = pd.DataFrame(property_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Annual carrying cost calculator
        st.markdown("**Annual Carrying Costs**")
        col_a, col_b = st.columns(2)

        with col_a:
            st.metric("Property Taxes", format_currency(annual_taxes))
            insurance_estimate = len(property_tracker) * 100  # $100 per property estimate
            st.metric("Est. Insurance", format_currency(insurance_estimate))

        with col_b:
            total_carrying_cost = annual_taxes + insurance_estimate
            st.metric("Total Annual Cost", format_currency(total_carrying_cost))
            monthly_cost = total_carrying_cost / 12
            st.metric("Monthly Cost", format_currency(monthly_cost))

def display_appreciation_tracker():
    """Display land appreciation tracking and projections."""
    st.subheader("Land Appreciation Tracker")
    st.markdown("**Monitor your rural land appreciation over time**")

    healthcare_state = st.session_state.healthcare_banking
    property_tracker = healthcare_state['property_tracker']

    if not property_tracker:
        st.info("Add properties to your portfolio to see appreciation tracking.")
        return

    # Create appreciation projections
    timeline_years = [1, 3, 5, 10, 15, 20]
    appreciation_scenarios = {
        'Conservative (5%)': 0.05,
        'Moderate (7%)': 0.07,
        'Optimistic (10%)': 0.10
    }

    # Calculate current portfolio value
    total_investment = sum(prop['purchase_price'] for prop in property_tracker.values())

    # Create projection chart
    projection_data = []
    for scenario, rate in appreciation_scenarios.items():
        for year in timeline_years:
            future_value = total_investment * ((1 + rate) ** year)
            projection_data.append({
                'Year': year,
                'Scenario': scenario,
                'Portfolio Value': future_value,
                'Total Return': future_value - total_investment
            })

    if projection_data:
        df_projections = pd.DataFrame(projection_data)

        # Create the chart
        fig = px.line(
            df_projections,
            x='Year',
            y='Portfolio Value',
            color='Scenario',
            title='Portfolio Value Projections',
            labels={'Portfolio Value': 'Portfolio Value ($)', 'Year': 'Years Held'}
        )

        # Add current value line
        fig.add_hline(y=total_investment, line_dash="dash", line_color="gray",
                     annotation_text=f"Current Investment: {format_currency(total_investment)}")

        st.plotly_chart(fig, use_container_width=True)

        # Display specific projections
        st.markdown("**Specific Projections**")

        col1, col2, col3 = st.columns(3)

        # 5-year projections
        with col1:
            st.markdown("**5-Year Projections**")
            for scenario, rate in appreciation_scenarios.items():
                value_5yr = total_investment * ((1 + rate) ** 5)
                return_5yr = value_5yr - total_investment
                roi_5yr = (return_5yr / total_investment) * 100
                st.caption(f"{scenario}: {format_currency(value_5yr)} (+{roi_5yr:.1f}%)")

        # 10-year projections
        with col2:
            st.markdown("**10-Year Projections**")
            for scenario, rate in appreciation_scenarios.items():
                value_10yr = total_investment * ((1 + rate) ** 10)
                return_10yr = value_10yr - total_investment
                roi_10yr = (return_10yr / total_investment) * 100
                st.caption(f"{scenario}: {format_currency(value_10yr)} (+{roi_10yr:.1f}%)")

        # 20-year projections
        with col3:
            st.markdown("**20-Year Projections**")
            for scenario, rate in appreciation_scenarios.items():
                value_20yr = total_investment * ((1 + rate) ** 20)
                return_20yr = value_20yr - total_investment
                roi_20yr = (return_20yr / total_investment) * 100
                st.caption(f"{scenario}: {format_currency(value_20yr)} (+{roi_20yr:.1f}%)")

def display_healthcare_land_banking():
    """Main healthcare land banking component."""
    # Initialize state
    _initialize_healthcare_banking_state()

    # Display header
    display_healthcare_professional_header()

    st.markdown("---")

    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["Education Center", "Budget Optimizer", "Portfolio Tracker", "Appreciation Tracker"])

    with tab1:
        display_education_center()

    with tab2:
        display_budget_optimizer()

    with tab3:
        display_property_tracker()

    with tab4:
        display_appreciation_tracker()

    # Footer with healthcare professional specific tips
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <p><strong>Healthcare Professional Land Banking</strong> • Conservative wealth building for busy healthcare workers</p>
        <p>Remember: Just like in healthcare, systematic processes and evidence-based decisions lead to the best outcomes!</p>
    </div>
    """, unsafe_allow_html=True)

# Export the main function
def display_healthcare_land_banking_component():
    """Export function for the healthcare land banking component."""
    display_healthcare_land_banking()