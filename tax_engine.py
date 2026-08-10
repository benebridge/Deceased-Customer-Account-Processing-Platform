"""
Tax Withholding Calculation Engine for Death Benefit Claims
Handles federal and state tax withholding for retirement account distributions
"""

import sqlite3
from datetime import datetime
from typing import Dict, Optional, Tuple
import json

class TaxEngine:
    """
    Calculates required tax withholding for death benefit distributions.
    Supports IRA, 401(k), 403(b), and other qualified retirement accounts.
    """

    # State income tax rates (2026 rates - simplified)
    STATE_TAX_RATES = {
        'CA': 0.093,  # California
        'NY': 0.0685, # New York
        'TX': 0.0,    # Texas - no state income tax
        'FL': 0.0,    # Florida - no state income tax
        'IL': 0.0495, # Illinois
        'PA': 0.0307, # Pennsylvania
        'OH': 0.0399, # Ohio
        'GA': 0.0575, # Georgia
        'NC': 0.0499, # North Carolina
        'MI': 0.0425, # Michigan
        'NJ': 0.0637, # New Jersey
        'VA': 0.0575, # Virginia
        'WA': 0.0,    # Washington - no state income tax
        'AZ': 0.025,  # Arizona
        'MA': 0.05,   # Massachusetts
        'TN': 0.0,    # Tennessee - no state income tax
        'IN': 0.0323, # Indiana
        'MO': 0.054,  # Missouri
        'MD': 0.0575, # Maryland
        'WI': 0.0765, # Wisconsin
        'CO': 0.044,  # Colorado
        'MN': 0.0985, # Minnesota
        'SC': 0.07,   # South Carolina
        'AL': 0.05,   # Alabama
        'LA': 0.0425, # Louisiana
        'KY': 0.05,   # Kentucky
        'OR': 0.099,  # Oregon
        'OK': 0.05,   # Oklahoma
        'CT': 0.0699, # Connecticut
        'UT': 0.0485, # Utah
        'IA': 0.0853, # Iowa
        'NV': 0.0,    # Nevada - no state income tax
        'AR': 0.055,  # Arkansas
        'MS': 0.05,   # Mississippi
        'KS': 0.057,  # Kansas
        'NM': 0.059,  # New Mexico
        'NE': 0.0684, # Nebraska
        'WV': 0.065,  # West Virginia
        'ID': 0.0558, # Idaho
        'HI': 0.11,   # Hawaii
        'NH': 0.0,    # New Hampshire - no state income tax on wages
        'ME': 0.0715, # Maine
        'RI': 0.0599, # Rhode Island
        'MT': 0.069,  # Montana
        'DE': 0.066,  # Delaware
        'SD': 0.0,    # South Dakota - no state income tax
        'ND': 0.029,  # North Dakota
        'AK': 0.0,    # Alaska - no state income tax
        'VT': 0.0875, # Vermont
        'WY': 0.0,    # Wyoming - no state income tax
    }

    def __init__(self, db_path='benebridge.db'):
        self.db_path = db_path

    def get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =================== MAIN CALCULATION ===================

    def calculate_withholding(
        self,
        distribution_amount: float,
        account_type: str,
        beneficiary_relationship: str,
        beneficiary_age: Optional[int],
        deceased_age_at_death: Optional[int],
        state: str = 'CA',
        federal_withholding_election: Optional[float] = None,
        state_withholding_election: Optional[float] = None
    ) -> Dict:
        """
        Calculate required tax withholding for a death benefit distribution.

        Args:
            distribution_amount: Total distribution amount
            account_type: IRA, 401K, 403B, etc.
            beneficiary_relationship: spouse, child, other
            beneficiary_age: Age of beneficiary
            deceased_age_at_death: Age of deceased at time of death
            state: Two-letter state code
            federal_withholding_election: Optional beneficiary election (0.0 - 1.0)
            state_withholding_election: Optional beneficiary election (0.0 - 1.0)

        Returns:
            Dict with withholding calculations and net distribution
        """

        # Calculate federal withholding
        federal_result = self._calculate_federal_withholding(
            distribution_amount,
            account_type,
            beneficiary_relationship,
            beneficiary_age,
            deceased_age_at_death,
            federal_withholding_election
        )

        # Calculate state withholding
        state_result = self._calculate_state_withholding(
            distribution_amount,
            state,
            state_withholding_election
        )

        # Calculate penalty (if applicable)
        penalty_result = self._calculate_early_distribution_penalty(
            distribution_amount,
            account_type,
            beneficiary_age,
            beneficiary_relationship
        )

        total_withholding = (
            federal_result['amount'] +
            state_result['amount'] +
            penalty_result['amount']
        )

        net_distribution = distribution_amount - total_withholding

        return {
            'distribution_amount': distribution_amount,
            'federal_withholding': federal_result,
            'state_withholding': state_result,
            'penalty': penalty_result,
            'total_withholding': total_withholding,
            'net_distribution': net_distribution,
            'tax_forms_required': self._get_required_tax_forms(account_type),
            'calculated_at': datetime.now().isoformat(),
            'account_type': account_type,
            'state': state
        }

    # =================== FEDERAL WITHHOLDING ===================

    def _calculate_federal_withholding(
        self,
        amount: float,
        account_type: str,
        relationship: str,
        beneficiary_age: Optional[int],
        deceased_age: Optional[int],
        election: Optional[float]
    ) -> Dict:
        """
        Calculate federal income tax withholding.

        Default rates per IRS guidelines:
        - IRAs: 10% default withholding
        - 401(k)/403(b): 20% mandatory withholding for lump sums
        - Beneficiary can elect different rate (0% to 100%)
        """

        # Default withholding rates
        if account_type in ['401K', '403B', '401(k)', '403(b)']:
            default_rate = 0.20  # 20% mandatory for employer plans
            minimum_rate = 0.20  # Cannot elect less than 20% for employer plans
        else:  # IRA, Roth IRA, etc.
            default_rate = 0.10  # 10% default for IRAs
            minimum_rate = 0.0   # Can elect 0% for IRAs

        # Apply beneficiary election if provided
        if election is not None:
            rate = max(election, minimum_rate)
        else:
            rate = default_rate

        withholding_amount = amount * rate

        # Spousal rollover considerations
        eligible_for_rollover = (relationship == 'spouse')

        return {
            'amount': withholding_amount,
            'rate': rate,
            'default_rate': default_rate,
            'minimum_rate': minimum_rate,
            'elected_rate': election,
            'eligible_for_rollover': eligible_for_rollover,
            'rollover_note': 'Spouse can roll over to own IRA to defer taxes' if eligible_for_rollover else None,
            'method': 'Beneficiary elected' if election is not None else 'Default withholding'
        }

    # =================== STATE WITHHOLDING ===================

    def _calculate_state_withholding(
        self,
        amount: float,
        state: str,
        election: Optional[float]
    ) -> Dict:
        """
        Calculate state income tax withholding.

        State withholding varies by state:
        - Some states have no income tax
        - Others require withholding based on state rates
        """

        state = state.upper()
        state_rate = self.STATE_TAX_RATES.get(state, 0.05)  # Default 5% if unknown

        # Allow beneficiary election
        if election is not None:
            rate = election
        else:
            rate = state_rate

        withholding_amount = amount * rate

        has_state_tax = state_rate > 0

        return {
            'amount': withholding_amount,
            'rate': rate,
            'state_rate': state_rate,
            'elected_rate': election,
            'state': state,
            'has_state_tax': has_state_tax,
            'method': 'Beneficiary elected' if election is not None else 'State default rate'
        }

    # =================== PENALTIES ===================

    def _calculate_early_distribution_penalty(
        self,
        amount: float,
        account_type: str,
        beneficiary_age: Optional[int],
        relationship: str
    ) -> Dict:
        """
        Calculate 10% early distribution penalty if applicable.

        Death benefit distributions are generally EXEMPT from the 10% penalty,
        regardless of age. This is a key exception to the early withdrawal penalty.
        """

        # Death distributions are exempt from 10% penalty per IRS rules
        penalty_applies = False
        penalty_amount = 0.0
        exemption_reason = 'Death benefit distribution - exempt from early withdrawal penalty'

        return {
            'amount': penalty_amount,
            'rate': 0.0,
            'applies': penalty_applies,
            'exemption_reason': exemption_reason,
            'note': 'IRS Code Section 72(t)(2)(A)(ii) - Death distributions are penalty-free'
        }

    # =================== TAX FORMS ===================

    def _get_required_tax_forms(self, account_type: str) -> list:
        """Get list of required tax forms for this distribution"""
        forms = ['1099-R']  # Always required for retirement distributions

        if account_type in ['401K', '403B', '401(k)', '403(b)']:
            forms.append('945')  # Annual return of withheld federal income tax

        return forms

    # =================== ADVANCED SCENARIOS ===================

    def calculate_10_year_rule_impact(
        self,
        account_balance: float,
        beneficiary_relationship: str,
        beneficiary_age: Optional[int]
    ) -> Dict:
        """
        Calculate tax implications under the SECURE Act 10-year rule.

        Most non-spouse beneficiaries must withdraw entire account within 10 years.
        This can have significant tax implications.
        """

        is_eligible_designated_beneficiary = (
            beneficiary_relationship == 'spouse' or
            (beneficiary_age and beneficiary_age < 18) or  # Minor child
            beneficiary_relationship == 'disabled' or
            beneficiary_relationship == 'chronically_ill'
        )

        if is_eligible_designated_beneficiary:
            distribution_strategy = 'Stretch distributions over life expectancy'
            annual_rmd_required = True
            ten_year_deadline = False
        else:
            distribution_strategy = '10-year rule applies - must distribute entire balance by end of 10th year'
            annual_rmd_required = False  # Unless account owner died after RBD
            ten_year_deadline = True

        # Estimate annual distribution under 10-year rule
        estimated_annual_distribution = account_balance / 10 if ten_year_deadline else account_balance / 20

        return {
            'eligible_designated_beneficiary': is_eligible_designated_beneficiary,
            'distribution_strategy': distribution_strategy,
            'annual_rmd_required': annual_rmd_required,
            'ten_year_deadline': ten_year_deadline,
            'estimated_annual_distribution': estimated_annual_distribution,
            'total_balance': account_balance,
            'tax_planning_note': 'Consider spreading distributions to minimize tax bracket impact' if ten_year_deadline else None
        }

    def calculate_inherited_roth_tax_treatment(
        self,
        distribution_amount: float,
        years_account_open: int,
        account_owner_age_at_death: int
    ) -> Dict:
        """
        Calculate tax treatment for inherited Roth IRA.

        Roth IRAs are generally tax-free if:
        1. Account has been open 5+ years
        2. Account owner was 59½ or older
        """

        five_year_rule_met = years_account_open >= 5
        age_requirement_met = account_owner_age_at_death >= 59.5

        is_qualified_distribution = five_year_rule_met and age_requirement_met

        if is_qualified_distribution:
            tax_treatment = 'Tax-free distribution'
            federal_withholding = 0.0
            state_withholding = 0.0
        else:
            tax_treatment = 'Earnings may be taxable'
            # Would need to calculate basis vs earnings
            federal_withholding = distribution_amount * 0.10  # Estimated
            state_withholding = distribution_amount * 0.05    # Estimated

        return {
            'is_qualified_distribution': is_qualified_distribution,
            'five_year_rule_met': five_year_rule_met,
            'age_requirement_met': age_requirement_met,
            'tax_treatment': tax_treatment,
            'estimated_federal_withholding': federal_withholding,
            'estimated_state_withholding': state_withholding,
            'tax_free': is_qualified_distribution
        }

    # =================== DATABASE INTEGRATION ===================

    def save_calculation_to_case(self, case_id: int, calculation: Dict) -> int:
        """Save tax calculation to database"""
        conn = self.get_db()
        cursor = conn.cursor()

        # Create tax_calculations table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tax_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                distribution_amount REAL NOT NULL,
                federal_withholding REAL NOT NULL,
                state_withholding REAL NOT NULL,
                penalty REAL NOT NULL,
                total_withholding REAL NOT NULL,
                net_distribution REAL NOT NULL,
                calculation_details TEXT,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(id)
            )
        ''')

        cursor.execute('''
            INSERT INTO tax_calculations (
                case_id, distribution_amount, federal_withholding,
                state_withholding, penalty, total_withholding,
                net_distribution, calculation_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            calculation['distribution_amount'],
            calculation['federal_withholding']['amount'],
            calculation['state_withholding']['amount'],
            calculation['penalty']['amount'],
            calculation['total_withholding'],
            calculation['net_distribution'],
            json.dumps(calculation)
        ))

        calc_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return calc_id

    def get_calculation_for_case(self, case_id: int) -> Optional[Dict]:
        """Get most recent tax calculation for a case"""
        conn = self.get_db()
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tax_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                distribution_amount REAL NOT NULL,
                federal_withholding REAL NOT NULL,
                state_withholding REAL NOT NULL,
                penalty REAL NOT NULL,
                total_withholding REAL NOT NULL,
                net_distribution REAL NOT NULL,
                calculation_details TEXT,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(id)
            )
        ''')

        result = cursor.execute('''
            SELECT * FROM tax_calculations
            WHERE case_id = ?
            ORDER BY calculated_at DESC
            LIMIT 1
        ''', (case_id,)).fetchone()

        conn.close()

        if result:
            details = json.loads(result['calculation_details'])
            return details
        return None


def get_tax_engine():
    """Get singleton instance of tax engine"""
    return TaxEngine()
