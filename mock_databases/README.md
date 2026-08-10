# BeneBridge Mock Databases - Complete Reference

Generated on: August 9, 2026

## Overview

This directory contains comprehensive mock databases for the BeneBridge POC, designed to replace external API calls with realistic local data. All data is interconnected and ready for demonstration purposes.

## Database Statistics

- **Total Cases**: 20
- **Deceased Persons**: 20
- **Beneficiaries**: 41
- **Financial Accounts**: 51
- **Beneficiary Designations**: 86
- **Fraud Cases**: 2 (Cases #13 and #19)

## Database Files

### 1. Death Master File (DMF) - `dmf_mock.db`

Simulates the Social Security Death Master File / SSDI database.

**Table**: `deceased_persons`

**Fields**:
- `case_id` - Unique case identifier (1-20)
- `ssn` - Social Security Number (format: XXX-XX-XXXX)
- `first_name`, `last_name`, `full_name`
- `gender` - M/F
- `dob` - Date of birth (YYYY-MM-DD)
- `dod` - Date of death (YYYY-MM-DD, all within last 2 years)
- `address_street`, `address_city`, `address_state`, `address_zip`
- `height` - Format: X'Y"
- `weight` - In pounds
- `eye_color` - Brown, Blue, Green, Hazel, Gray

**Query Example**:
```sql
SELECT * FROM deceased_persons WHERE ssn = '400-36-9992';
```

### 2. Beneficiary Registry - `beneficiary_registry.db`

Contains beneficiary information and account designations.

**Tables**:

#### `beneficiaries`
- `beneficiary_id` - Unique identifier
- `ssn`, `first_name`, `last_name`, `full_name`
- `gender`, `dob`
- `address_street`, `address_city`, `address_state`, `address_zip`
- `phone`, `email`

#### `beneficiary_designations`
- `id` - Auto-increment
- `account_id` - Links to financial account
- `beneficiary_id` - Links to beneficiary
- `percentage` - Percentage of account (must sum to 100 per account)
- `designation_type` - "primary" or "contingent"
- `designated_date` - When designation was made

**Query Example**:
```sql
SELECT b.full_name, bd.account_id, bd.percentage
FROM beneficiaries b
JOIN beneficiary_designations bd ON b.beneficiary_id = bd.beneficiary_id
WHERE bd.account_id = 'ACC-1-1';
```

### 3. Identity Verification - `identity_verification.db`

Simulates Persona API identity verification database.

**Table**: `identity_records`

**Fields**:
- `id` - Auto-increment
- `ssn`, `first_name`, `last_name`, `full_name`
- `gender`, `dob`
- `address_street`, `address_city`, `address_state`, `address_zip`
- `drivers_license` - DL number
- `dl_state` - State that issued DL
- `dl_expiration` - Expiration date (4-6 years from now)
- `height`, `weight`, `eye_color`
- `photo_reference` - Photo filename (e.g., "photo_1.jpg")
- `verification_status` - "verified", "pending", "failed"
- `last_verified` - Timestamp

**Query Example**:
```sql
SELECT * FROM identity_records WHERE drivers_license = 'HE168575' AND dl_state = 'MA';
```

### 4. Financial Accounts - `financial_accounts.db`

Contains financial institutions and account information.

**Tables**:

#### `institutions`
- `id`, `name` - Institution name
- `type` - "bank" or "brokerage"
- `routing_number`
- `contact_phone`, `contact_email`
- `api_endpoint`, `api_key` - For simulating API integration

**Available Institutions**:
- Wells Fargo (bank)
- Chase Bank (bank)
- Bank of America (bank)
- Citibank (bank)
- Fidelity Investments (brokerage)
- Charles Schwab (brokerage)
- Vanguard (brokerage)
- TD Ameritrade (brokerage)

#### `accounts`
- `account_id` - Format: ACC-{case_id}-{account_number}
- `deceased_case_id` - Links to deceased person
- `institution_name`, `institution_type`
- `routing_number`, `account_number`
- `account_type` - checking, savings, 401k, IRA, brokerage, money_market
- `balance` - Account balance ($5K-$1.5M depending on type)
- `status` - "active", "pending", "closed"
- `opened_date`, `last_activity_date`

**Query Example**:
```sql
SELECT a.account_id, a.institution_name, a.account_type, a.balance
FROM accounts a
WHERE a.deceased_case_id = 1;
```

### 5. Fraud Indicators - `fraud_indicators.db`

Tracks suspicious activities and fraudulent patterns.

**Tables**:

#### `fraud_indicators`
- `id`, `case_id`, `beneficiary_id`
- `indicator_type`:
  - `ssn_mismatch` - SSN associated with multiple identities
  - `recent_beneficiary_change` - Changed shortly before death
  - `suspicious_document` - Document tampering detected
  - `blacklisted_individual` - On fraud watchlist
- `severity` - "low", "medium", "high", "critical"
- `description` - Short description
- `details` - Detailed explanation
- `flagged_date`, `status` - "active", "resolved", "investigating"

#### `blacklisted_individuals`
- `id`, `ssn`, `full_name`
- `reason` - Why they're blacklisted
- `added_date`, `status`

#### `suspicious_patterns`
- Pattern definitions for fraud detection
- `pattern_type`, `description`, `risk_score` (0-100)

**Flagged Cases**:
- **Case 13**: Sarah White - Suspicious document (high severity)
- **Case 19**: Matthew White - Recent beneficiary change (medium severity)

**Query Example**:
```sql
SELECT * FROM fraud_indicators WHERE severity IN ('high', 'critical');
```

## Master Reference Files

### MASTER_REFERENCE_ALL_PERSONS.csv

Human-readable CSV with ALL person data (deceased + beneficiaries). Use this to create mock documents.

**Columns**:
- type, case_id, full_name, first_name, last_name, gender
- ssn, dob, dod (for deceased only)
- height, weight, eye_color
- address_street, address_city, address_state, address_zip
- phone, email (for beneficiaries only)
- drivers_license, dl_state (for beneficiaries only)
- relationship (for beneficiaries only)

### MASTER_REFERENCE_ALL_PERSONS.json

Complete structured data including:
- All persons (deceased + beneficiaries)
- All beneficiary designations
- All fraud indicators
- Metadata (generation date, totals)

## Sample Use Cases

### 1. Verify Death Certificate Against DMF

```python
import sqlite3

conn = sqlite3.connect('dmf_mock.db')
c = conn.cursor()

# Lookup by SSN from death certificate
c.execute("SELECT * FROM deceased_persons WHERE ssn = ?", ("400-36-9992",))
result = c.fetchone()

if result:
    print(f"Verified: {result['full_name']} died on {result['dod']}")
```

### 2. Find Beneficiaries for an Account

```python
conn = sqlite3.connect('beneficiary_registry.db')
c = conn.cursor()

# Get all beneficiaries for account ACC-1-1
c.execute('''
    SELECT b.full_name, b.phone, b.email, bd.percentage
    FROM beneficiaries b
    JOIN beneficiary_designations bd ON b.beneficiary_id = bd.beneficiary_id
    WHERE bd.account_id = ?
    ORDER BY bd.percentage DESC
''', ("ACC-1-1",))

for row in c.fetchall():
    print(f"{row[0]}: {row[3]}%")
```

### 3. Verify Beneficiary ID

```python
conn = sqlite3.connect('identity_verification.db')
c = conn.cursor()

# Verify driver's license
c.execute('''
    SELECT * FROM identity_records
    WHERE drivers_license = ? AND dl_state = ?
''', ("HE168575", "MA"))

result = c.fetchone()
if result and result['verification_status'] == 'verified':
    print(f"ID Verified: {result['full_name']}")
```

### 4. Check for Fraud Indicators

```python
conn = sqlite3.connect('fraud_indicators.db')
c = conn.cursor()

# Check if beneficiary is flagged
c.execute('''
    SELECT * FROM fraud_indicators
    WHERE beneficiary_id = ? AND status = 'active'
''', (29,))

flags = c.fetchall()
if flags:
    print(f"WARNING: {len(flags)} fraud indicator(s) found!")
    for flag in flags:
        print(f"  - {flag['indicator_type']}: {flag['description']}")
```

## Realistic Data Features

✅ **Gender-appropriate names**: Males have male names, females have female names
✅ **Logical relationships**:
   - Spouses have opposite genders (simplified)
   - Children have appropriate ages relative to parents
   - Siblings may share last names
✅ **Realistic demographics**:
   - Ages: 40-95 for deceased
   - Heights: 5'1" to 6'9"
   - Weights: 120-250 lbs
   - Eye colors: Brown, Blue, Green, Hazel, Gray
✅ **Recent deaths**: All dates of death within last 2 years
✅ **Realistic addresses**: Major US cities with proper zip codes
✅ **Realistic account balances**:
   - Checking/Savings: $5K-$150K
   - 401k/IRA/Brokerage: $50K-$1.5M
✅ **Proper beneficiary splits**: Percentages sum to 100% per account

## Document Creation Checklist

For each case, you need to create:

### Death Certificate
- [ ] Use deceased person's full data from MASTER_REFERENCE_ALL_PERSONS.csv
- [ ] Include: name, SSN, DOB, DOD, address, gender, height, weight
- [ ] Use Washington State format
- [ ] For fraud cases (13, 19): introduce subtle alterations

### Beneficiary ID Documents
- [ ] Create driver's license for each beneficiary
- [ ] Include: name, DOB, address, DL number, height, weight, eye color, photo
- [ ] Match data exactly to identity_verification.db
- [ ] Use appropriate state format (dl_state column)

### Transfer Application
- [ ] List all account details from financial_accounts.db
- [ ] Include all beneficiaries with correct percentages
- [ ] Deceased information from DMF
- [ ] Beneficiary contact info from beneficiary_registry.db

## Query Helper Script

A `query_helper.py` script is included to make database queries easier. See usage examples in the script.

## Regenerating Data

To regenerate all databases with new random data:

```bash
python3 generate_mock_data.py
```

**Warning**: This will overwrite all existing databases!

## Notes

- All SSNs are randomly generated and not associated with real people
- All names, addresses, and phone numbers are fictional
- Data is for POC demonstration purposes only
- Databases use SQLite for easy portability
- No external dependencies required for querying

## Support

For questions about the database structure or data generation, see `generate_mock_data.py` source code.
