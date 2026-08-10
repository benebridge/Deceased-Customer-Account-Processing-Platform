"""
Synthetic Data Generator for BeneBridge POC

Generates realistic death claim case scenarios following the methodology
described in Chapter 4 of the dissertation.

Generates:
- Deceased person personas
- Beneficiary personas
- Complete case scenarios (simple, moderate, complex, fraudulent)
- Proper distribution across account types and complexity levels
"""

import sqlite3
import random
import string
from datetime import datetime, timedelta
from faker import Faker

# Initialize Faker for realistic data generation
fake = Faker('en_US')

# SSA designated test SSN range
TEST_SSN_RANGE = range(987654320, 987654330)

# Account type distribution (from Chapter 5)
ACCOUNT_TYPES = {
    'IRA': 0.40,           # 40% - Individual Retirement Accounts
    '401k': 0.25,          # 25% - Employer-sponsored retirement
    'Life Insurance': 0.15, # 15% - Life insurance policies
    'Trust': 0.10,         # 10% - Trust accounts
    'Brokerage': 0.10      # 10% - Other account types
}

# Complexity distribution
COMPLEXITY_LEVELS = {
    'simple': 0.60,    # 60% - Straightforward cases
    'moderate': 0.30,  # 30% - Common complications
    'complex': 0.10    # 10% - Specialized handling required
}

# Death certificate types
CERT_TYPES = {
    'blockchain': 0.15,  # 15% - Blockchain verified (Titan Seal)
    'physical': 0.85     # 85% - Traditional physical certificates
}

# Fraud prevalence
FRAUD_RATE = 0.05  # 5% fraud cases

class SyntheticDataGenerator:
    def __init__(self, db_path='benebridge.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.used_ssns = set()
        self.used_case_numbers = set()

    def generate_ssn(self):
        """Generate SSN from SSA test range"""
        available_ssns = [ssn for ssn in TEST_SSN_RANGE if ssn not in self.used_ssns]
        if not available_ssns:
            # Fallback: generate fictional SSN outside real ranges
            ssn = f"{random.randint(900, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        else:
            ssn_num = random.choice(available_ssns)
            self.used_ssns.add(ssn_num)
            ssn = f"{str(ssn_num)[:3]}-{str(ssn_num)[3:5]}-{str(ssn_num)[5:]}"
        return ssn

    def generate_deceased_persona(self):
        """Generate realistic deceased person"""
        # Age at death follows actuarial life tables (65-90 most common)
        age_at_death = int(random.gauss(75, 10))  # Normal distribution around 75
        age_at_death = max(18, min(105, age_at_death))  # Clamp to reasonable range

        date_of_death = fake.date_between(start_date='-1y', end_date='today')
        date_of_birth = date_of_death - timedelta(days=age_at_death * 365)

        return {
            'name': fake.name(),
            'ssn': self.generate_ssn(),
            'dob': date_of_birth.strftime('%Y-%m-%d'),
            'dod': date_of_death.strftime('%Y-%m-%d'),
            'age': age_at_death,
            'address': f"{fake.street_address()}, {fake.city()}, CA {fake.zipcode()}"
        }

    def generate_beneficiary_persona(self, deceased_name):
        """Generate realistic beneficiary"""
        # Beneficiaries often share last name (spouse/child)
        relationship = random.choice(['spouse', 'child', 'sibling', 'other'])

        if relationship in ['spouse', 'child']:
            last_name = deceased_name.split()[-1]
            first_name = fake.first_name()
            name = f"{first_name} {last_name}"
        else:
            name = fake.name()

        return {
            'name': name,
            'email': fake.email(),
            'phone': fake.phone_number(),
            'address': f"{fake.street_address()}, {fake.city()}, CA {fake.zipcode()}",
            'relationship': relationship
        }

    def generate_account_balance(self, account_type):
        """Generate realistic account balance based on Federal Reserve wealth data"""
        # Different account types have different typical balances
        if account_type == 'IRA':
            # IRA balances: $5K - $500K, median ~$80K
            balance = random.lognormvariate(11.3, 1.2)  # Log-normal distribution
        elif account_type == '401k':
            # 401k balances: $10K - $800K, median ~$120K
            balance = random.lognormvariate(11.7, 1.3)
        elif account_type == 'Life Insurance':
            # Life insurance: $25K - $1M, common amounts
            balance = random.choice([25000, 50000, 100000, 250000, 500000, 1000000])
        elif account_type == 'Trust':
            # Trust accounts: $50K - $5M, higher balances
            balance = random.lognormvariate(12.5, 1.5)
        else:  # Brokerage
            # Brokerage: $10K - $2M
            balance = random.lognormvariate(11.5, 1.4)

        # Round to nearest $100
        return round(balance / 100) * 100

    def determine_complexity(self, account_type, balance, relationship):
        """Determine case complexity based on attributes"""
        complexity_score = 0

        # Account type complexity
        if account_type in ['Trust', '401k']:
            complexity_score += 2
        elif account_type == 'Life Insurance':
            complexity_score += 1

        # Balance complexity
        if balance > 500000:
            complexity_score += 2
        elif balance > 100000:
            complexity_score += 1

        # Relationship complexity
        if relationship not in ['spouse', 'child']:
            complexity_score += 1

        # Map score to complexity level
        if complexity_score >= 4:
            return 'complex'
        elif complexity_score >= 2:
            return 'moderate'
        else:
            return 'simple'

    def generate_case_number(self, institution_code='CNB'):
        """Generate unique case number"""
        year = datetime.now().year
        max_attempts = 100
        for _ in range(max_attempts):
            random_num = random.randint(1000, 9999)
            case_number = f"{institution_code}-{year}-{random_num}"
            if case_number not in self.used_case_numbers:
                self.used_case_numbers.add(case_number)
                return case_number
        # Fallback: use timestamp
        timestamp = int(datetime.now().timestamp() * 1000) % 10000
        case_number = f"{institution_code}-{year}-{timestamp}"
        self.used_case_numbers.add(case_number)
        return case_number

    def generate_access_code(self):
        """Generate secure access code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    def generate_certificate_number(self, death_date, cert_type):
        """Generate realistic death certificate number"""
        year = death_date.split('-')[0]
        county_codes = ['SF', 'LA', 'SD', 'OC', 'SAC', 'ALA']
        county = random.choice(county_codes)
        number = random.randint(10000, 99999)

        if cert_type == 'blockchain':
            return f"{year}-CA-{county}-{number}"
        else:
            # Physical certificates might have different formats
            return f"{year}-CA-{county}-{number}"

    def generate_blockchain_hash(self):
        """Generate realistic Ethereum transaction hash"""
        return '0x' + ''.join(random.choices('0123456789abcdef', k=64))

    def create_case(self, complexity='simple', is_fraud=False):
        """Create a complete case scenario"""

        # Step 1: Generate personas
        deceased = self.generate_deceased_persona()
        beneficiary = self.generate_beneficiary_persona(deceased['name'])

        # Step 2: Determine account type (weighted random)
        account_type = random.choices(
            list(ACCOUNT_TYPES.keys()),
            weights=list(ACCOUNT_TYPES.values())
        )[0]

        # Step 3: Generate account details
        balance = self.generate_account_balance(account_type)
        account_number = f"{account_type[:3].upper()}-{random.randint(100000, 999999)}"

        # Step 4: Determine actual complexity
        actual_complexity = self.determine_complexity(
            account_type,
            balance,
            beneficiary['relationship']
        )

        # Step 5: Death certificate details
        cert_type = random.choices(
            list(CERT_TYPES.keys()),
            weights=list(CERT_TYPES.values())
        )[0]

        cert_number = self.generate_certificate_number(deceased['dod'], cert_type)
        blockchain_hash = self.generate_blockchain_hash() if cert_type == 'blockchain' else None

        # Step 6: Generate case metadata
        case_number = self.generate_case_number()
        access_code = self.generate_access_code()
        submission_date = datetime.now().isoformat()

        # Step 7: Fraud indicators (if fraudulent case)
        if is_fraud:
            fraud_type = random.choice([
                'forged_document',
                'identity_theft',
                'duplicate_claim',
                'beneficiary_fraud'
            ])
            # Modify case to include fraud red flags
            if fraud_type == 'duplicate_claim':
                # Use an SSN that might be reused
                deceased['ssn'] = random.choice(list(self.used_ssns)) if self.used_ssns else deceased['ssn']
        else:
            fraud_type = None

        # Step 8: Assemble case
        case = {
            'case_number': case_number,
            'access_code': access_code,
            'deceased_name': deceased['name'],
            'deceased_ssn': deceased['ssn'],
            'date_of_birth': deceased['dob'],
            'date_of_death': deceased['dod'],
            'beneficiary_name': beneficiary['name'],
            'beneficiary_email': beneficiary['email'],
            'beneficiary_phone': beneficiary['phone'],
            'beneficiary_address': beneficiary['address'],
            'beneficiary_relationship': beneficiary['relationship'],
            'account_number': account_number,
            'account_type': account_type,
            'account_balance': balance,
            'financial_institution': 'Community National Bank',
            'death_cert_type': cert_type,
            'death_certificate_number': cert_number,
            'blockchain_hash': blockchain_hash,
            'status': 'pending',
            'submission_date': submission_date,
            'complexity': actual_complexity,
            'is_fraud': is_fraud,
            'fraud_type': fraud_type
        }

        return case

    def insert_case_to_db(self, case):
        """Insert case into database"""
        self.cursor.execute('''
            INSERT INTO cases (
                case_number, deceased_name, deceased_ssn, date_of_death,
                beneficiary_name, beneficiary_email, beneficiary_phone, beneficiary_address,
                account_number, account_type, account_balance, financial_institution,
                death_cert_type, blockchain_hash, death_certificate_number,
                status, submission_date, access_code, workflow_stage, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case['case_number'],
            case['deceased_name'],
            case['deceased_ssn'],
            case['date_of_death'],
            case['beneficiary_name'],
            case['beneficiary_email'],
            case['beneficiary_phone'],
            case['beneficiary_address'],
            case['account_number'],
            case['account_type'],
            case['account_balance'],
            case['financial_institution'],
            case['death_cert_type'],
            case['blockchain_hash'],
            case['death_certificate_number'],
            case['status'],
            case['submission_date'],
            case['access_code'],
            1,  # workflow_stage
            'medium'  # priority
        ))

        case_id = self.cursor.lastrowid

        # Create workflow tasks for this case
        self.create_workflow_tasks(case_id, case['account_type'])

        return case_id

    def create_workflow_tasks(self, case_id, account_type):
        """Create workflow tasks based on account type"""
        tasks = []

        if account_type == 'IRA':
            tasks = [
                ('Initial Review', 'Review submitted documents and basic information', 1),
                ('Document Verification', 'Verify death certificate and beneficiary ID', 2),
                ('Tax Calculation', 'Calculate federal and state tax withholding', 3),
                ('Final Approval', 'Final review and approval for payment', 4)
            ]
        elif account_type == '401k':
            tasks = [
                ('Initial Review', 'Review submitted documents', 1),
                ('Document Verification', 'Verify death certificate and ID', 2),
                ('Spousal Consent Check', 'Verify spousal waiver if applicable', 3),
                ('ERISA Compliance', 'Ensure ERISA compliance', 3),
                ('Tax Calculation', 'Calculate withholding', 4),
                ('Final Approval', 'Dual approval required', 5)
            ]
        elif account_type == 'Trust':
            tasks = [
                ('Initial Review', 'Review trust documents', 1),
                ('Document Verification', 'Verify all trust documentation', 2),
                ('Trustee Verification', 'Verify trustee authority', 3),
                ('Legal Review', 'Legal compliance check', 4),
                ('Final Approval', 'Executive approval required', 5)
            ]
        else:
            tasks = [
                ('Initial Review', 'Review claim documentation', 1),
                ('Document Verification', 'Verify death certificate', 2),
                ('Compliance Check', 'Standard compliance review', 3),
                ('Final Approval', 'Approve distribution', 4)
            ]

        for task_name, description, stage in tasks:
            self.cursor.execute('''
                INSERT INTO workflow_tasks (
                    case_id, task_name, task_description, stage, completed
                ) VALUES (?, ?, ?, ?, 0)
            ''', (case_id, task_name, description, stage))

    def generate_dataset(self, num_cases=50):
        """Generate complete synthetic dataset"""
        print(f"Generating {num_cases} synthetic cases...")
        print("=" * 60)

        cases_created = {
            'simple': 0,
            'moderate': 0,
            'complex': 0,
            'fraud': 0
        }

        for i in range(num_cases):
            # Determine if this should be a fraud case
            is_fraud = random.random() < FRAUD_RATE

            # Create case
            case = self.create_case(is_fraud=is_fraud)

            # Insert to database
            case_id = self.insert_case_to_db(case)

            # Track statistics
            if is_fraud:
                cases_created['fraud'] += 1
            else:
                cases_created[case['complexity']] += 1

            # Print progress
            if (i + 1) % 10 == 0:
                print(f"Created {i + 1}/{num_cases} cases...")

        self.conn.commit()

        print("\n" + "=" * 60)
        print("Dataset Generation Complete!")
        print("=" * 60)
        print(f"\nStatistics:")
        print(f"  Simple cases:   {cases_created['simple']} ({cases_created['simple']/num_cases*100:.1f}%)")
        print(f"  Moderate cases: {cases_created['moderate']} ({cases_created['moderate']/num_cases*100:.1f}%)")
        print(f"  Complex cases:  {cases_created['complex']} ({cases_created['complex']/num_cases*100:.1f}%)")
        print(f"  Fraud cases:    {cases_created['fraud']} ({cases_created['fraud']/num_cases*100:.1f}%)")
        print(f"  Total:          {num_cases}")

        # Print sample cases for testing
        print("\n" + "=" * 60)
        print("Sample Cases for Testing:")
        print("=" * 60)

        sample_cases = self.cursor.execute('''
            SELECT case_number, access_code, beneficiary_name, beneficiary_email,
                   account_type, account_balance, death_cert_type
            FROM cases
            ORDER BY RANDOM()
            LIMIT 5
        ''').fetchall()

        for case in sample_cases:
            print(f"\nCase: {case[0]}")
            print(f"  Access Code: {case[1]}")
            print(f"  Beneficiary: {case[2]} ({case[3]})")
            print(f"  Account: {case[4]} - ${case[5]:,.2f}")
            print(f"  Certificate: {case[6]}")

    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == '__main__':
    # Initialize generator
    generator = SyntheticDataGenerator()

    # Clear existing cases (optional - comment out if you want to keep existing)
    print("Clearing existing cases...")
    generator.cursor.execute('DELETE FROM cases')
    generator.cursor.execute('DELETE FROM workflow_tasks')
    generator.conn.commit()

    # Generate dataset
    generator.generate_dataset(num_cases=50)

    # Close connection
    generator.close()

    print("\n✓ Synthetic data generation complete!")
    print("\nYou can now test the three portals:")
    print("  - Institution Portal: http://localhost:5005")
    print("  - BeneBridge Portal:  http://localhost:5004")
    print("  - Executour Platform: http://localhost:5006")
