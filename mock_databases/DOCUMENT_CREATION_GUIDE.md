# Mock Document Creation Guide

This guide provides step-by-step instructions for creating mock documents for each of the 20 cases using the data in the databases.

## Quick Reference

- **Total Cases**: 20
- **Fraud Cases**: 13, 19 (create documents with intentional anomalies)
- **Master Data**: See `MASTER_REFERENCE_ALL_PERSONS.csv`
- **Query Tool**: `python3 query_helper.py case <case_id>`

## Documents Needed Per Case

For each case, you need to create:

1. **Death Certificate** (1 per case = 20 total)
2. **Beneficiary ID Documents** (1-3 per case = 41 total)
3. **Transfer Application** (optional, for demonstration)

## 1. Creating Death Certificates

### Data Source
Use the "deceased" rows from `MASTER_REFERENCE_ALL_PERSONS.csv` or query:
```bash
python3 query_helper.py case <case_id>
```

### Required Fields

Based on Washington State death certificate format:

| Field | Database Column | Example |
|-------|----------------|---------|
| Certificate Number | `case_id` + year | 2024-001234 |
| State File Number | `case_id` | 2024-000001 |
| First and Middle Name(s) | `first_name` | Jessica |
| Last Name(s) | `last_name` | Gonzalez |
| Sex | `gender` | F (Female) |
| Social Security Number | `ssn` | 400-36-9992 |
| Date of Birth | `dob` | April 28, 1973 (from 1973-04-28) |
| Date of Death | `dod` | October 13, 2025 (from 2025-10-13) |
| Age | Calculate from DOB/DOD | 52 years |
| Birthplace | `address_city`, `address_state` | Portland, OR |
| Address | `address_street`, `address_city`, `address_state`, `address_zip` | 1864 Elm St, Portland, OR 97201 |
| Height | `height` | 5'3" |
| Weight | `weight` | 233 lbs |
| Eye Color | `eye_color` | Blue |

### Case-Specific Instructions

#### Regular Cases (1-12, 14-18, 20)
Create standard death certificates with all accurate information.

#### Fraud Case 13 (Mark White)
- **Fraud Type**: Suspicious document / Tampered death certificate
- **Anomaly to Add**: Slightly alter the date of death
  - Actual DOD from database: 2024-09-18
  - On certificate, make it look changed/corrected (e.g., overwritten text)
  - Or use inconsistent date formats
  - Or show signs of digital manipulation
- This should be detectable by careful review but subtle enough to test fraud detection

#### Fraud Case 19 (Elizabeth White)
- **Fraud Type**: Recent beneficiary change
- **Anomaly**: Certificate itself is legitimate
- The fraud is in the beneficiary designation timing (in the database already)
- Create a normal, accurate death certificate

### File Naming Convention
```
death_cert_case_{case_id}_{last_name}_{first_name}.pdf
```
Example: `death_cert_case_01_Gonzalez_Jessica.pdf`

## 2. Creating Beneficiary ID Documents (Driver's Licenses)

### Data Source
Use the "beneficiary" rows from `MASTER_REFERENCE_ALL_PERSONS.csv`

Each beneficiary needs a driver's license matching their data in `identity_verification.db`.

### Required Fields

| Field | Database Column | Example |
|-------|----------------|---------|
| License Number | `drivers_license` | HE168575 |
| State | `dl_state` | MA |
| Full Name | `full_name` | Dorothy Gonzalez |
| Date of Birth | `dob` | 1968-08-12 (shown as 08/12/1968) |
| Sex | `gender` | F |
| Height | `height` | 5'7" |
| Weight | `weight` | 217 lbs |
| Eyes | `eye_color` | Blue |
| Address | Full address | 9589 Washington Blvd, Boston, MA 02101 |
| Issue Date | Calculate: 2-4 years ago | 04/15/2022 |
| Expiration Date | Calculate: 2-4 years from now | 04/15/2028 |
| Photo | Placeholder or stock photo | photo_{beneficiary_id}.jpg |

### State-Specific Formats

Create IDs matching the format of the state in `dl_state`:

- **MA** (Massachusetts): Standard horizontal format
- **WA** (Washington): Enhanced Driver License (EDL) option available
- **AZ** (Arizona): Standard format with desert background
- **OR** (Oregon): Standard format
- **NY** (New York): Enhanced Driver License
- **TX** (Texas): Standard format
- **CA** (California): Real ID compliant
- **FL** (Florida): Standard format
- **CO** (Colorado): Standard format

### Photo Requirements

For POC purposes, you can:
1. Use placeholder images
2. Use stock photos from royalty-free sources
3. Use AI-generated faces
4. Label as `photo_{beneficiary_id}.jpg`

### File Naming Convention
```
drivers_license_case_{case_id}_ben_{beneficiary_id}_{last_name}_{first_name}.pdf
```
Example: `drivers_license_case_01_ben_01_Gonzalez_Dorothy.pdf`

## 3. Creating Transfer Applications

Optional but helpful for full workflow demonstration.

### Data Source
Combine data from:
- Deceased person (DMF)
- Beneficiaries (Beneficiary Registry)
- Accounts (Financial Accounts)
- Use `python3 query_helper.py case <case_id>` for complete info

### Required Sections

#### Section 1: Deceased Account Holder Information
- Name, SSN, DOB, DOD, Last Address
- From `deceased_persons` table

#### Section 2: Financial Accounts
For each account in the case:
- Account Number
- Institution Name
- Account Type
- Current Balance
- Beneficiary Designations (with percentages)

From `accounts` and `beneficiary_designations` tables

#### Section 3: Claimant (Beneficiary) Information
For each beneficiary:
- Full Name, SSN, DOB
- Current Address
- Phone, Email
- Relationship to Deceased
- Percentage Share
- Driver's License Number and State

From `beneficiaries` table

#### Section 4: Supporting Documents
Checklist:
- [ ] Death Certificate (attach)
- [ ] Beneficiary ID (attach)
- [ ] Proof of Relationship (if required)
- [ ] Tax Forms (W-9)

### File Naming Convention
```
transfer_application_case_{case_id}_{account_id}.pdf
```

## Quick Start: Creating Documents for Case 1

### Step 1: Get Case Data
```bash
cd mock_databases
python3 query_helper.py case 1
```

Output shows:
- Deceased: Jessica Gonzalez
- 2 Accounts (401k and money market)
- 2 Beneficiaries (Margaret and Dorothy Gonzalez)

### Step 2: Create Death Certificate
Use data:
- Name: Jessica Gonzalez (F)
- SSN: 400-36-9992
- DOB: 1964-03-14 → Show as "March 14, 1964"
- DOD: 2025-10-13 → Show as "October 13, 2025"
- Address: 1864 Elm St, Portland, OR 97201
- Height: 5'3", Weight: 233 lbs, Eyes: Blue

### Step 3: Create Beneficiary IDs

#### For Margaret Gonzalez (Beneficiary ID: 3)
Query the CSV for beneficiary_id 3:
- DL: SG286617 (MA)
- DOB: 1959-12-10
- Height: 6'0", Weight: 224, Eyes: Brown
- Address: 917 Park Pl, Boston, MA 02101

#### For Dorothy Gonzalez (Beneficiary ID: 1)
Query the CSV for beneficiary_id 1:
- DL: HE168575 (MA)
- DOB: 1968-08-12
- Height: 5'7", Weight: 217, Eyes: Blue
- Address: 9589 Washington Blvd, Boston, MA 02101

### Step 4: Create Transfer Applications
- One for ACC-1-1 (401k, $148,603.63)
  - Margaret: 70%
  - Dorothy: 30%
- One for ACC-1-2 (money market, $113,094.44)
  - Margaret: 100%

## Tools and Templates

### Recommended Tools
- **PDF Creation**: Adobe Acrobat, LibreOffice, Google Docs
- **Death Certificates**: Use Washington State template or create similar
- **Driver's Licenses**: Use state-specific ID card makers/templates
- **Forms**: Create standardized transfer application form

### Data Validation Checklist

Before creating documents, verify:
- [ ] All names match across documents
- [ ] SSNs are consistent
- [ ] Dates are in correct formats
- [ ] Addresses match database
- [ ] Physical characteristics (height, weight, eyes) match
- [ ] Driver's license numbers match identity_verification.db
- [ ] Account numbers match financial_accounts.db
- [ ] Beneficiary percentages sum to 100% per account

### Testing Checklist

After creating documents:
- [ ] Upload death certificate to verification platform
- [ ] Verify against DMF database
- [ ] Upload beneficiary IDs
- [ ] Verify against identity_verification.db
- [ ] Check fraud detection for Cases 13 and 19
- [ ] Confirm beneficiary-account linkages
- [ ] Validate account balances and distributions

## Bulk Creation Strategy

### Priority Order

1. **Phase 1**: Create 5 sample cases (1, 2, 13, 19, 20)
   - Case 1: Simple case, 2 beneficiaries
   - Case 2: Simple case, 3 beneficiaries
   - Case 13: Fraud case (suspicious document)
   - Case 19: Fraud case (recent beneficiary change)
   - Case 20: Normal case for comparison

2. **Phase 2**: Create cases 3-12 (10 more cases)
   - Focus on variety of account types and beneficiary relationships

3. **Phase 3**: Create cases 14-18 (remaining cases)
   - Complete the full 20-case set

### Time Estimates
- Death Certificate: ~15 minutes each
- Driver's License: ~10 minutes each
- Transfer Application: ~20 minutes each

**Total for all 20 cases**:
- Death Certificates: ~5 hours
- Driver's Licenses (41): ~7 hours
- Transfer Applications (51): ~17 hours
- **Total**: ~29 hours for complete document set

### Shortcuts for POC
- Create only 5-10 cases instead of all 20
- Use templates to speed up creation
- Focus on fraud cases (13, 19) and a few normal cases
- Skip transfer applications for initial POC

## Database Integration

### Verifying Document Data

After creating documents, verify they match the database:

```python
from query_helper import BeneBridgeDB

db = BeneBridgeDB()

# Verify death certificate data
deceased = db.get_deceased_by_ssn("400-36-9992")
print(f"Name: {deceased['full_name']}")
print(f"DOD: {deceased['dod']}")

# Verify beneficiary ID
identity = db.verify_identity_by_dl("HE168575", "MA")
print(f"Beneficiary: {identity['full_name']}")
print(f"DOB: {identity['dob']}")
```

### Updating Document References

After creating physical documents, you may want to track them:

```sql
-- Add a documents table to track created files
CREATE TABLE created_documents (
    id INTEGER PRIMARY KEY,
    case_id INTEGER,
    document_type TEXT,
    file_path TEXT,
    created_date TIMESTAMP
);
```

## Next Steps

1. Review `MASTER_REFERENCE_ALL_PERSONS.csv` for all person data
2. Choose which cases to create first (recommend: 1, 2, 13, 19, 20)
3. Gather templates for death certificates and IDs
4. Create documents systematically
5. Test uploads in verification platform
6. Verify fraud detection works for Cases 13 and 19

## Support Files

- `MASTER_REFERENCE_ALL_PERSONS.csv` - All person data in spreadsheet format
- `MASTER_REFERENCE_ALL_PERSONS.json` - All data in structured JSON
- `query_helper.py` - Query tool for database lookups
- `README.md` - Complete database documentation

## Questions?

Refer to the README.md for database schema details and query examples.
