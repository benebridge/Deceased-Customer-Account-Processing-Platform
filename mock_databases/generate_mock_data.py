#!/usr/bin/env python3
"""
Generate realistic mock databases for BeneBridge POC
Creates 20 deceased cases with beneficiaries, accounts, and fraud indicators
"""

import sqlite3
import random
import json
from datetime import datetime, timedelta
from pathlib import Path

# Realistic data pools
MALE_FIRST_NAMES = [
    "James", "Robert", "John", "Michael", "David", "William", "Richard",
    "Joseph", "Thomas", "Christopher", "Daniel", "Matthew", "Anthony",
    "Donald", "Mark", "Paul", "Steven", "Kenneth", "George", "Edward"
]

FEMALE_FIRST_NAMES = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth",
    "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Margaret", "Lisa",
    "Betty", "Dorothy", "Sandra", "Ashley", "Emily", "Donna", "Carol"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Thompson", "White", "Harris", "Sanchez", "Clark", "Lewis",
    "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott"
]

CITIES = [
    # All deceased must be from Los Angeles County for LA County death certificate template
    ("Los Angeles", "CA", "90001"),
    ("Los Angeles", "CA", "90012"),
    ("Los Angeles", "CA", "90013"),
    ("Los Angeles", "CA", "90015"),
    ("Los Angeles", "CA", "90017"),
    ("Beverly Hills", "CA", "90210"),
    ("Santa Monica", "CA", "90401"),
    ("Pasadena", "CA", "91101"),
    ("Long Beach", "CA", "90802"),
    ("Burbank", "CA", "91502"),
    ("Glendale", "CA", "91201"),
    ("Torrance", "CA", "90501"),
    ("Pomona", "CA", "91766"),
    ("El Monte", "CA", "91731"),
    ("Downey", "CA", "90241")
]

# Beneficiaries must also be from California (for CA driver's licenses)
BENEFICIARY_CITIES = [
    ("Los Angeles", "CA", "90001"), ("Los Angeles", "CA", "90012"), ("San Francisco", "CA", "94102"),
    ("San Diego", "CA", "92101"), ("San Jose", "CA", "95101"), ("Sacramento", "CA", "95814"),
    ("Fresno", "CA", "93721"), ("Oakland", "CA", "94612"), ("Santa Ana", "CA", "92701"),
    ("Anaheim", "CA", "92805"), ("Riverside", "CA", "92501"), ("Bakersfield", "CA", "93301"),
    ("Stockton", "CA", "95202"), ("Irvine", "CA", "92614"), ("Chula Vista", "CA", "91910"),
    ("Fremont", "CA", "94538"), ("Santa Monica", "CA", "90401"), ("Beverly Hills", "CA", "90210"),
    ("Pasadena", "CA", "91101"), ("Long Beach", "CA", "90802")
]

STREET_NAMES = [
    "Main St", "Oak Ave", "Maple Dr", "Pine Rd", "Cedar Ln", "Elm St",
    "Washington Blvd", "Lincoln Ave", "Park Pl", "Lake Dr", "River Rd",
    "Hill St", "Valley Way", "Sunset Blvd", "Harbor View", "Mountain Rd"
]

FINANCIAL_INSTITUTIONS = [
    # Only one institution - Community National Bank (using Beneficiary Claim Form)
    {"name": "Community National Bank", "type": "bank", "routing": "122016066"}
]

# Only IRA accounts since we're using IRA Beneficiary Claim Form
ACCOUNT_TYPES = ["IRA"]

RELATIONSHIPS = {
    "spouse": ["spouse", "wife", "husband"],
    "child": ["son", "daughter", "child"],
    "sibling": ["brother", "sister", "sibling"],
    "parent": ["mother", "father", "parent"],
    "other": ["niece", "nephew", "cousin", "friend", "partner"]
}

def generate_ssn():
    """Generate realistic-looking SSN"""
    area = random.randint(100, 899)  # Avoid 900+ (not issued)
    group = random.randint(10, 99)
    serial = random.randint(1000, 9999)
    return f"{area:03d}-{group:02d}-{serial:04d}"

def generate_dob(min_age=40, max_age=95):
    """Generate realistic date of birth for deceased persons"""
    today = datetime.now()
    years_ago = random.randint(min_age, max_age)
    birth_year = today.year - years_ago
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)  # Safe for all months
    return datetime(birth_year, birth_month, birth_day).strftime("%Y-%m-%d")

def generate_dod(dob_str, min_months_ago=1, max_months_ago=24):
    """Generate date of death (recent, within last 2 years)"""
    dob = datetime.strptime(dob_str, "%Y-%m-%d")
    today = datetime.now()
    months_ago = random.randint(min_months_ago, max_months_ago)
    dod = today - timedelta(days=months_ago * 30)

    # Make sure DOD is after DOB
    if dod < dob:
        dod = dob + timedelta(days=365 * 50)  # Died at ~50 if calculation fails

    return dod.strftime("%Y-%m-%d")

def generate_address(for_beneficiary=False):
    """Generate realistic US address"""
    number = random.randint(100, 9999)
    street = random.choice(STREET_NAMES)

    # Deceased must be from LA County, beneficiaries can be anywhere
    if for_beneficiary:
        city, state, zip_base = random.choice(BENEFICIARY_CITIES)
    else:
        city, state, zip_base = random.choice(CITIES)

    zip_code = f"{zip_base}"
    return {
        "street": f"{number} {street}",
        "city": city,
        "state": state,
        "zip": zip_code
    }

def generate_drivers_license(state):
    """Generate realistic driver's license number"""
    # Format varies by state, using alphanumeric
    letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
    numbers = ''.join(random.choices('0123456789', k=6))
    return f"{letters}{numbers}"

def generate_height():
    """Generate realistic height in feet and inches"""
    feet = random.randint(5, 6)
    inches = random.randint(0, 11)
    return f"{feet}'{inches}\""

def generate_weight():
    """Generate realistic weight in lbs"""
    return random.randint(120, 250)

def generate_eye_color():
    """Generate eye color"""
    return random.choice(["Brown", "Blue", "Green", "Hazel", "Gray"])

def generate_hair_color():
    """Generate hair color"""
    return random.choice(["Black", "Brown", "Blonde", "Red", "Gray", "White", "Bald"])

def generate_account_number():
    """Generate realistic account number"""
    return ''.join(random.choices('0123456789', k=10))

# Removed - balance now generated inline for IRA accounts

class MockDataGenerator:
    def __init__(self):
        self.deceased_persons = []
        self.beneficiaries = []
        self.accounts = []
        self.institutions = FINANCIAL_INSTITUTIONS
        self.fraud_cases = []
        self.all_persons = []  # For master reference document

    def generate_deceased_person(self, case_id, is_fraud=False):
        """Generate a realistic deceased person"""
        gender = random.choice(["M", "F"])
        first_name = random.choice(MALE_FIRST_NAMES if gender == "M" else FEMALE_FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)

        dob = generate_dob()
        dod = generate_dod(dob)
        ssn = generate_ssn()
        address = generate_address(for_beneficiary=False)  # Deceased from LA County

        deceased = {
            "case_id": case_id,
            "ssn": ssn,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "gender": gender,
            "dob": dob,
            "dod": dod,
            "address_street": address["street"],
            "address_city": address["city"],
            "address_state": address["state"],
            "address_zip": address["zip"],
            "height": generate_height(),
            "weight": generate_weight(),
            "eye_color": generate_eye_color(),
            # Deceased don't need hair color for death certificates
            "is_fraud": is_fraud
        }

        self.deceased_persons.append(deceased)
        self.all_persons.append({
            "type": "deceased",
            "case_id": case_id,
            **deceased
        })

        return deceased

    def generate_beneficiary(self, deceased, relationship_type, beneficiary_id):
        """Generate a beneficiary for a deceased person"""
        # Determine gender based on relationship
        if relationship_type == "spouse":
            # Opposite gender of deceased (simplified)
            gender = "F" if deceased["gender"] == "M" else "M"
            relationship = "wife" if gender == "F" else "husband"
            # Spouse has same last name (traditional, simplified)
            last_name = deceased["last_name"]
        elif relationship_type == "child":
            gender = random.choice(["M", "F"])
            relationship = "son" if gender == "M" else "daughter"
            # Children might have same last name
            last_name = deceased["last_name"] if random.random() > 0.3 else random.choice(LAST_NAMES)
        elif relationship_type == "sibling":
            gender = random.choice(["M", "F"])
            relationship = "brother" if gender == "M" else "sister"
            # Siblings likely have same last name
            last_name = deceased["last_name"] if random.random() > 0.2 else random.choice(LAST_NAMES)
        else:
            gender = random.choice(["M", "F"])
            relationship = random.choice(RELATIONSHIPS["other"])
            last_name = random.choice(LAST_NAMES)

        first_name = random.choice(MALE_FIRST_NAMES if gender == "M" else FEMALE_FIRST_NAMES)

        # Beneficiary age should make sense relative to relationship
        if relationship_type == "spouse":
            age = random.randint(40, 90)
        elif relationship_type == "child":
            age = random.randint(25, 65)
        elif relationship_type == "parent":
            age = random.randint(65, 95)
        else:
            age = random.randint(30, 70)

        dob = generate_dob(min_age=age, max_age=age+5)
        ssn = generate_ssn()
        address = generate_address(for_beneficiary=True)  # Beneficiaries can live anywhere
        dl_state = address["state"]

        beneficiary = {
            "beneficiary_id": beneficiary_id,
            "deceased_case_id": deceased["case_id"],
            "ssn": ssn,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "gender": gender,
            "dob": dob,
            "relationship": relationship,
            "address_street": address["street"],
            "address_city": address["city"],
            "address_state": address["state"],
            "address_zip": address["zip"],
            "phone": f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
            "email": f"{first_name.lower()}.{last_name.lower()}@email.com",
            "drivers_license": generate_drivers_license(dl_state),
            "dl_state": dl_state,
            "height": generate_height(),
            "weight": generate_weight(),
            "eye_color": generate_eye_color(),
            "hair_color": generate_hair_color()
        }

        self.beneficiaries.append(beneficiary)
        self.all_persons.append({
            "type": "beneficiary",
            "case_id": deceased["case_id"],
            **beneficiary
        })

        return beneficiary

    def generate_accounts_for_deceased(self, deceased):
        """Generate 1-3 IRA accounts at Community National Bank for deceased person"""
        num_accounts = random.randint(1, 3)  # 1-3 IRA accounts
        accounts_list = []

        for i in range(num_accounts):
            institution = self.institutions[0]  # Only Community National Bank
            account_type = "IRA"  # Only IRA accounts

            # IRA balances typically higher
            balance = round(random.uniform(50000, 1500000), 2)

            account = {
                "account_id": f"IRA-{deceased['case_id']:03d}-{i+1}",
                "deceased_case_id": deceased["case_id"],
                "institution_name": institution["name"],
                "institution_type": institution["type"],
                "routing_number": institution["routing"],
                "account_number": generate_account_number(),
                "account_type": account_type,
                "balance": balance,
                "status": "active",
                "opened_date": (datetime.now() - timedelta(days=random.randint(365*5, 365*30))).strftime("%Y-%m-%d")
            }

            accounts_list.append(account)
            self.accounts.append(account)

        return accounts_list

    def generate_beneficiary_designations(self, deceased, accounts, beneficiaries):
        """Link beneficiaries to accounts with percentages"""
        designations = []

        for account in accounts:
            # Each account has 1-3 beneficiaries
            num_beneficiaries = min(len(beneficiaries), random.randint(1, 3))
            selected_beneficiaries = random.sample(beneficiaries, num_beneficiaries)

            # Allocate percentages (must sum to 100)
            if num_beneficiaries == 1:
                percentages = [100]
            elif num_beneficiaries == 2:
                split = random.choice([50, 60, 70, 80])
                percentages = [split, 100 - split]
            else:  # 3 beneficiaries
                p1 = random.choice([34, 40, 50])
                p2 = random.choice([33, 30, 25])
                p3 = 100 - p1 - p2
                percentages = [p1, p2, p3]

            for beneficiary, percentage in zip(selected_beneficiaries, percentages):
                designation = {
                    "account_id": account["account_id"],
                    "beneficiary_id": beneficiary["beneficiary_id"],
                    "percentage": percentage,
                    "designation_type": "primary",
                    "designated_date": account["opened_date"]
                }
                designations.append(designation)

        return designations

    def generate_fraud_indicators(self, deceased, beneficiary):
        """Generate fraud indicator for suspicious case"""
        fraud_types = [
            {
                "type": "ssn_mismatch",
                "description": "SSN associated with multiple identities",
                "severity": "high",
                "details": f"SSN {beneficiary['ssn']} appears in multiple inconsistent records"
            },
            {
                "type": "recent_beneficiary_change",
                "description": "Beneficiary designation changed shortly before death",
                "severity": "medium",
                "details": f"Beneficiary {beneficiary['full_name']} added within 30 days of death"
            },
            {
                "type": "suspicious_document",
                "description": "Death certificate shows signs of alteration",
                "severity": "high",
                "details": "Document forensics indicate possible tampering with dates"
            },
            {
                "type": "blacklisted_individual",
                "description": "Claimant appears on fraud watchlist",
                "severity": "critical",
                "details": f"{beneficiary['full_name']} has history of fraudulent insurance claims"
            }
        ]

        fraud = random.choice(fraud_types)
        fraud_indicator = {
            "case_id": deceased["case_id"],
            "beneficiary_id": beneficiary["beneficiary_id"],
            "indicator_type": fraud["type"],
            "severity": fraud["severity"],
            "description": fraud["description"],
            "details": fraud["details"],
            "flagged_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "active"
        }

        self.fraud_cases.append(fraud_indicator)
        return fraud_indicator

    def generate_all_cases(self):
        """Generate all 20 cases with beneficiaries"""
        all_designations = []
        beneficiary_counter = 1

        for case_id in range(1, 21):
            # Determine if this is a fraud case (cases 13 and 19)
            is_fraud = case_id in [13, 19]

            # Generate deceased person
            deceased = self.generate_deceased_person(case_id, is_fraud)

            # Generate 1-3 beneficiaries per case
            num_beneficiaries = random.randint(1, 3)
            case_beneficiaries = []

            for i in range(num_beneficiaries):
                # Determine relationship (first beneficiary is often spouse or child)
                if i == 0:
                    rel_type = random.choice(["spouse", "child"])
                elif i == 1:
                    rel_type = random.choice(["child", "sibling"])
                else:
                    rel_type = random.choice(["sibling", "other"])

                beneficiary = self.generate_beneficiary(deceased, rel_type, beneficiary_counter)
                case_beneficiaries.append(beneficiary)
                beneficiary_counter += 1

                # Add fraud indicator for fraud cases
                if is_fraud and i == 0:  # Flag the primary beneficiary
                    self.generate_fraud_indicators(deceased, beneficiary)

            # Generate accounts for deceased
            accounts = self.generate_accounts_for_deceased(deceased)

            # Link beneficiaries to accounts
            designations = self.generate_beneficiary_designations(deceased, accounts, case_beneficiaries)
            all_designations.extend(designations)

        return all_designations

def create_databases():
    """Create all SQLite databases"""
    base_dir = Path(__file__).parent

    print("=" * 80)
    print("GENERATING BENEBRIDGE MOCK DATABASES")
    print("=" * 80)

    # Generate all data
    generator = MockDataGenerator()
    print("\nGenerating 20 deceased cases with beneficiaries...")
    designations = generator.generate_all_cases()

    print(f"✓ Generated {len(generator.deceased_persons)} deceased persons")
    print(f"✓ Generated {len(generator.beneficiaries)} beneficiaries")
    print(f"✓ Generated {len(generator.accounts)} financial accounts")
    print(f"✓ Generated {len(designations)} beneficiary designations")
    print(f"✓ Generated {len(generator.fraud_cases)} fraud indicators")

    # Create DMF database
    print("\n" + "=" * 80)
    print("Creating Death Master File (DMF) Database")
    print("=" * 80)
    dmf_db = base_dir / "dmf_mock.db"
    conn = sqlite3.connect(dmf_db)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS deceased_persons (
        case_id INTEGER PRIMARY KEY,
        ssn TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        gender TEXT NOT NULL,
        dob TEXT NOT NULL,
        dod TEXT NOT NULL,
        address_street TEXT,
        address_city TEXT,
        address_state TEXT,
        address_zip TEXT,
        height TEXT,
        weight INTEGER,
        eye_color TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    for person in generator.deceased_persons:
        c.execute('''INSERT INTO deceased_persons
                     (case_id, ssn, first_name, last_name, full_name, gender, dob, dod,
                      address_street, address_city, address_state, address_zip,
                      height, weight, eye_color)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (person["case_id"], person["ssn"], person["first_name"], person["last_name"],
                   person["full_name"], person["gender"], person["dob"], person["dod"],
                   person["address_street"], person["address_city"], person["address_state"],
                   person["address_zip"], person["height"], person["weight"], person["eye_color"]))

    conn.commit()
    conn.close()
    print(f"✓ Created {dmf_db}")

    # Create Beneficiary Registry database
    print("\n" + "=" * 80)
    print("Creating Beneficiary Registry Database")
    print("=" * 80)
    beneficiary_db = base_dir / "beneficiary_registry.db"
    conn = sqlite3.connect(beneficiary_db)
    c = conn.cursor()

    # Beneficiaries table
    c.execute('''CREATE TABLE IF NOT EXISTS beneficiaries (
        beneficiary_id INTEGER PRIMARY KEY,
        ssn TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        gender TEXT NOT NULL,
        dob TEXT NOT NULL,
        address_street TEXT,
        address_city TEXT,
        address_state TEXT,
        address_zip TEXT,
        phone TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Beneficiary designations table
    c.execute('''CREATE TABLE IF NOT EXISTS beneficiary_designations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT NOT NULL,
        beneficiary_id INTEGER NOT NULL,
        percentage INTEGER NOT NULL,
        designation_type TEXT NOT NULL,
        designated_date TEXT NOT NULL,
        FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries(beneficiary_id)
    )''')

    for beneficiary in generator.beneficiaries:
        c.execute('''INSERT INTO beneficiaries
                     (beneficiary_id, ssn, first_name, last_name, full_name, gender, dob,
                      address_street, address_city, address_state, address_zip, phone, email)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (beneficiary["beneficiary_id"], beneficiary["ssn"], beneficiary["first_name"],
                   beneficiary["last_name"], beneficiary["full_name"], beneficiary["gender"],
                   beneficiary["dob"], beneficiary["address_street"], beneficiary["address_city"],
                   beneficiary["address_state"], beneficiary["address_zip"],
                   beneficiary["phone"], beneficiary["email"]))

    for designation in designations:
        c.execute('''INSERT INTO beneficiary_designations
                     (account_id, beneficiary_id, percentage, designation_type, designated_date)
                     VALUES (?, ?, ?, ?, ?)''',
                  (designation["account_id"], designation["beneficiary_id"],
                   designation["percentage"], designation["designation_type"],
                   designation["designated_date"]))

    conn.commit()
    conn.close()
    print(f"✓ Created {beneficiary_db}")

    # Create Identity Verification database
    print("\n" + "=" * 80)
    print("Creating Identity Verification Database")
    print("=" * 80)
    identity_db = base_dir / "identity_verification.db"
    conn = sqlite3.connect(identity_db)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS identity_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ssn TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        gender TEXT NOT NULL,
        dob TEXT NOT NULL,
        address_street TEXT,
        address_city TEXT,
        address_state TEXT,
        address_zip TEXT,
        drivers_license TEXT,
        dl_state TEXT,
        dl_issue_date TEXT,
        dl_expiration TEXT,
        height TEXT,
        weight INTEGER,
        eye_color TEXT,
        hair_color TEXT,
        photo_reference TEXT,
        verification_status TEXT DEFAULT 'verified',
        last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    for beneficiary in generator.beneficiaries:
        # DL issued 2-4 years ago, expires in 4-6 years
        dl_issue = (datetime.now() - timedelta(days=random.randint(365*2, 365*4))).strftime("%Y-%m-%d")
        dl_exp = (datetime.now() + timedelta(days=random.randint(365*4, 365*6))).strftime("%Y-%m-%d")

        c.execute('''INSERT INTO identity_records
                     (ssn, first_name, last_name, full_name, gender, dob,
                      address_street, address_city, address_state, address_zip,
                      drivers_license, dl_state, dl_issue_date, dl_expiration,
                      height, weight, eye_color, hair_color,
                      photo_reference, verification_status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (beneficiary["ssn"], beneficiary["first_name"], beneficiary["last_name"],
                   beneficiary["full_name"], beneficiary["gender"], beneficiary["dob"],
                   beneficiary["address_street"], beneficiary["address_city"],
                   beneficiary["address_state"], beneficiary["address_zip"],
                   beneficiary["drivers_license"], beneficiary["dl_state"], dl_issue, dl_exp,
                   beneficiary["height"], beneficiary["weight"], beneficiary["eye_color"],
                   beneficiary["hair_color"],
                   f"photo_{beneficiary['beneficiary_id']}.jpg", "verified"))

    conn.commit()
    conn.close()
    print(f"✓ Created {identity_db}")

    # Create Financial Institutions/Accounts database
    print("\n" + "=" * 80)
    print("Creating Financial Institutions/Accounts Database")
    print("=" * 80)
    financial_db = base_dir / "financial_accounts.db"
    conn = sqlite3.connect(financial_db)
    c = conn.cursor()

    # Institutions table
    c.execute('''CREATE TABLE IF NOT EXISTS institutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL,
        routing_number TEXT,
        contact_phone TEXT,
        contact_email TEXT,
        api_endpoint TEXT,
        api_key TEXT
    )''')

    # Accounts table
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        account_id TEXT PRIMARY KEY,
        deceased_case_id INTEGER NOT NULL,
        institution_name TEXT NOT NULL,
        institution_type TEXT NOT NULL,
        routing_number TEXT,
        account_number TEXT NOT NULL,
        account_type TEXT NOT NULL,
        balance REAL NOT NULL,
        status TEXT NOT NULL,
        opened_date TEXT NOT NULL,
        last_activity_date TEXT,
        FOREIGN KEY (institution_name) REFERENCES institutions(name)
    )''')

    # Insert institutions
    for inst in FINANCIAL_INSTITUTIONS:
        c.execute('''INSERT INTO institutions
                     (name, type, routing_number, contact_phone, contact_email, api_endpoint, api_key)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (inst["name"], inst["type"], inst["routing"],
                   f"1-800-{random.randint(100,999)}-{random.randint(1000,9999)}",
                   f"api@{inst['name'].lower().replace(' ', '')}.com",
                   f"https://api.{inst['name'].lower().replace(' ', '')}.com/v1",
                   f"test_api_key_{random.randint(10000,99999)}"))

    # Insert accounts
    for account in generator.accounts:
        last_activity = (datetime.now() - timedelta(days=random.randint(1, 180))).strftime("%Y-%m-%d")

        c.execute('''INSERT INTO accounts
                     (account_id, deceased_case_id, institution_name, institution_type,
                      routing_number, account_number, account_type, balance, status,
                      opened_date, last_activity_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (account["account_id"], account["deceased_case_id"], account["institution_name"],
                   account["institution_type"], account["routing_number"], account["account_number"],
                   account["account_type"], account["balance"], account["status"],
                   account["opened_date"], last_activity))

    conn.commit()
    conn.close()
    print(f"✓ Created {financial_db}")

    # Create Fraud Indicators database
    print("\n" + "=" * 80)
    print("Creating Fraud Indicators Database")
    print("=" * 80)
    fraud_db = base_dir / "fraud_indicators.db"
    conn = sqlite3.connect(fraud_db)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS fraud_indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER,
        beneficiary_id INTEGER,
        indicator_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        description TEXT NOT NULL,
        details TEXT,
        flagged_date TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS blacklisted_individuals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ssn TEXT UNIQUE,
        full_name TEXT NOT NULL,
        reason TEXT NOT NULL,
        added_date TEXT NOT NULL,
        status TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS suspicious_patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_type TEXT NOT NULL,
        description TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Insert fraud indicators
    for fraud in generator.fraud_cases:
        c.execute('''INSERT INTO fraud_indicators
                     (case_id, beneficiary_id, indicator_type, severity, description, details,
                      flagged_date, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (fraud["case_id"], fraud["beneficiary_id"], fraud["indicator_type"],
                   fraud["severity"], fraud["description"], fraud["details"],
                   fraud["flagged_date"], fraud["status"]))

        # Add to blacklist if critical severity
        if fraud["severity"] == "critical":
            # Find the beneficiary
            beneficiary = next(b for b in generator.beneficiaries
                             if b["beneficiary_id"] == fraud["beneficiary_id"])
            c.execute('''INSERT INTO blacklisted_individuals
                         (ssn, full_name, reason, added_date, status)
                         VALUES (?, ?, ?, ?, ?)''',
                      (beneficiary["ssn"], beneficiary["full_name"],
                       fraud["description"], fraud["flagged_date"], "active"))

    # Add some suspicious patterns
    patterns = [
        ("rapid_beneficiary_changes", "Multiple beneficiary changes within 60 days", 75),
        ("high_value_claim", "Claim amount exceeds $1M", 60),
        ("out_of_state_claimant", "Claimant resides in different state than deceased", 40),
        ("recent_account_creation", "Account created within 90 days of death", 80),
        ("multiple_death_claims", "Individual filing multiple death claims", 95)
    ]

    for pattern_type, description, risk_score in patterns:
        c.execute('''INSERT INTO suspicious_patterns
                     (pattern_type, description, risk_score)
                     VALUES (?, ?, ?)''',
                  (pattern_type, description, risk_score))

    conn.commit()
    conn.close()
    print(f"✓ Created {fraud_db}")

    # Create master reference document
    print("\n" + "=" * 80)
    print("Creating Master Reference Document")
    print("=" * 80)

    reference_file = base_dir / "MASTER_REFERENCE_ALL_PERSONS.json"
    reference_data = {
        "generated_date": datetime.now().isoformat(),
        "total_cases": 20,
        "total_deceased": len(generator.deceased_persons),
        "total_beneficiaries": len(generator.beneficiaries),
        "fraud_cases": [13, 19],
        "persons": generator.all_persons,
        "designations": designations,
        "fraud_indicators": generator.fraud_cases
    }

    with open(reference_file, 'w') as f:
        json.dump(reference_data, f, indent=2)

    print(f"✓ Created {reference_file}")

    # Create human-readable CSV for easy reference
    import csv

    csv_file = base_dir / "MASTER_REFERENCE_ALL_PERSONS.csv"
    with open(csv_file, 'w', newline='') as f:
        # Include all fields needed for document creation
        fieldnames = [
            'type', 'case_id', 'full_name', 'first_name', 'last_name', 'gender',
            'ssn', 'dob', 'dod', 'height', 'weight', 'eye_color',
            'address_street', 'address_city', 'address_state', 'address_zip',
            'phone', 'email', 'drivers_license', 'dl_state', 'relationship'
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for person in generator.all_persons:
            writer.writerow(person)

    print(f"✓ Created {csv_file}")

    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Cases: 20")
    print(f"Deceased Persons: {len(generator.deceased_persons)}")
    print(f"Beneficiaries: {len(generator.beneficiaries)}")
    print(f"Financial Accounts: {len(generator.accounts)}")
    print(f"Fraud Cases: {len(generator.fraud_cases)} (Cases 13 and 19)")
    print(f"\nFraud Case Details:")
    for fraud in generator.fraud_cases:
        beneficiary = next(b for b in generator.beneficiaries
                         if b["beneficiary_id"] == fraud["beneficiary_id"])
        print(f"  Case {fraud['case_id']}: {beneficiary['full_name']} - {fraud['indicator_type']} ({fraud['severity']})")

    print("\n" + "=" * 80)
    print("DATABASE GENERATION COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Review MASTER_REFERENCE_ALL_PERSONS.csv for all person data")
    print("2. Use this data to create mock death certificates")
    print("3. Use this data to create mock ID documents")
    print("4. Use this data to create mock transfer applications")
    print("\nAll databases are ready for POC testing!")

if __name__ == "__main__":
    create_databases()
