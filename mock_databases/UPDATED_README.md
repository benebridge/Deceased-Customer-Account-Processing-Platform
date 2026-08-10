# BeneBridge Mock Databases - UPDATED FOR POC

**Updated:** August 9, 2026
**Configured for:** Los Angeles County Death Certificates + Community National Bank IRA Beneficiary Claim Forms

## Important Changes from Original

### 🔄 Key Updates

1. **All deceased persons are from Los Angeles County, California**
   - Required for LA County death certificate template compatibility
   - Cities include: Los Angeles, Beverly Hills, Santa Monica, Pasadena, Long Beach, Burbank, Glendale, Torrance, Pomona, El Monte, Downey

2. **Single Financial Institution: Community National Bank**
   - All accounts are at Community National Bank
   - Required for consistent beneficiary claim form usage
   - Routing Number: 122016066

3. **IRA Accounts Only**
   - All accounts are IRA accounts
   - Matches the IRA Beneficiary Claim Form template
   - Balances: $50K - $1.5M (typical IRA ranges)

4. **Beneficiaries can live anywhere**
   - Not restricted to LA County
   - Allows for testing of out-of-state claimants
   - States include: CA, TX, NY, FL, WA, OR, AZ, CO, MA, IL, GA, etc.

## Database Statistics

- **Total Cases**: 20
- **Deceased Persons**: 20 (all in LA County, CA)
- **Beneficiaries**: 43
- **Financial Accounts**: 38 (all Community National Bank IRAs)
- **Beneficiary Designations**: 55
- **Fraud Cases**: 2 (Cases #13 and #19)

## Sample Cases

### CASE 1: Sandra Wilson (Simple baseline)
**Deceased**: Sandra Wilson, F, SSN: 185-54-5819
- DOB: 1935-02-06, DOD: 2025-05-16
- Address: 9890 Lake Dr, **El Monte, CA 91731** ✓ LA County
- Height: 6'5", Weight: 241 lbs, Eyes: Green

**Accounts**: 2 IRA accounts, Total: $1,895,775.90
- IRA-001-1: Community National Bank IRA ($1,295,190.78)
- IRA-001-2: Community National Bank IRA ($600,585.12)

**Beneficiary**:
- Kenneth Wilson (husband) - 100% of both accounts
- Lives in Austin, TX (out of state)

### CASE 13: Jennifer Thompson ⚠️ FRAUD CASE (Critical)
**Deceased**: Jennifer Thompson, F, SSN: 501-62-9628
- DOB: 1959-12-23, DOD: 2026-04-11
- Address: 8410 Sunset Blvd, **Los Angeles, CA 90001** ✓ LA County

**Accounts**: 1 IRA account, Total: $597,928.13
- IRA-013-1: Community National Bank IRA ($597,928.13)

**Beneficiaries**:
- Emily Thompson (40%)
- Daniel Thompson (30%) - **BLACKLISTED** ⚠️
- Donna White (30%)

**FRAUD INDICATOR**:
- Type: blacklisted_individual (CRITICAL)
- Description: Claimant appears on fraud watchlist
- Flagged beneficiary: Daniel Thompson (ID: 27)

### CASE 19: Elizabeth Walker ⚠️ FRAUD CASE (High)
**Deceased**: Elizabeth Walker, F, SSN: 167-83-3049
- DOB: 1974-09-17, DOD: 2026-05-11
- Address: 6413 Lincoln Ave, **Pomona, CA 91766** ✓ LA County

**Accounts**: 2 IRA accounts, Total: $1,913,572.99
- IRA-019-1: Community National Bank IRA ($662,452.25)
- IRA-019-2: Community National Bank IRA ($1,251,120.74)

**Beneficiaries**:
- Elizabeth Harris (100% of IRA-019-2) - **SSN MISMATCH** ⚠️
- Daniel Lewis (100% of IRA-019-1)

**FRAUD INDICATOR**:
- Type: ssn_mismatch (HIGH)
- Description: SSN associated with multiple identities
- Flagged beneficiary: Elizabeth Harris (ID: 40)

## Document Templates Required

### 1. Los Angeles County Death Certificate Template
- Use for ALL 20 deceased persons
- All deaths occurred in Los Angeles County, CA
- Date range: Aug 2024 - Jul 2026 (within last 2 years)

**Template Fields**:
- Certificate Number: 2024-XXXXXX or 2025-XXXXXX or 2026-XXXXXX
- County: Los Angeles
- State: California
- All addresses within LA County cities
- All other fields from database

### 2. Community National Bank IRA Beneficiary Claim Form
Location: `/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/Beneficiary-Claim-Form-IRA-After-2019-1.pdf`

**Form Fields**:
- Financial Institution: Community National Bank
- Account Type: IRA (all accounts)
- Account Numbers: From database (format: IRA-XXX-X)
- Routing Number: 122016066
- Deceased information from DMF
- Beneficiary information from beneficiary_registry.db

## Los Angeles County Cities Included

All deceased lived in one of these LA County cities:
- ✓ Los Angeles
- ✓ Beverly Hills
- ✓ Santa Monica
- ✓ Pasadena
- ✓ Long Beach
- ✓ Burbank
- ✓ Glendale
- ✓ Torrance
- ✓ Pomona
- ✓ El Monte
- ✓ Downey

## Database Files

Same 5 databases as before:
1. **dmf_mock.db** - Death Master File
2. **beneficiary_registry.db** - Beneficiaries and designations
3. **identity_verification.db** - ID verification
4. **financial_accounts.db** - Community National Bank accounts only
5. **fraud_indicators.db** - Fraud detection

## Query Examples

```bash
# View any case
python3 query_helper.py case 1

# Check all deceased are in CA
sqlite3 dmf_mock.db "SELECT address_city, address_state FROM deceased_persons;"

# Verify all accounts are Community National Bank IRAs
sqlite3 financial_accounts.db "SELECT DISTINCT institution_name, account_type FROM accounts;"

# Check fraud cases
python3 query_helper.py fraud
```

## Creating Documents

### Death Certificates (20 total)
Use LA County death certificate template for:
- All 20 deceased persons
- All addresses are in LA County
- All deaths recent (2024-2026)
- Use exact data from `MASTER_REFERENCE_ALL_PERSONS.csv`

**For Fraud Cases**:
- **Case 13**: Create normal death certificate (fraud is in beneficiary blacklist, not document)
- **Case 19**: Create normal death certificate (fraud is in SSN mismatch, not document)

### Beneficiary IDs (43 total)
- Create driver's licenses for all 43 beneficiaries
- States vary (TX, NY, CA, FL, etc. - check dl_state column)
- Use exact data from identity_verification.db

### IRA Beneficiary Claim Forms (38 total)
Use Community National Bank IRA Beneficiary Claim Form for:
- All 38 IRA accounts
- Institution: Community National Bank
- Routing: 122016066
- Account IDs: IRA-001-1, IRA-001-2, etc.

## Priority Cases for POC

Create these 5 cases first:

1. **Case 1** - Simple (1 beneficiary, 2 accounts)
2. **Case 2** - Multiple beneficiaries (3 beneficiaries)
3. **Case 13** - Fraud case (blacklisted beneficiary)
4. **Case 19** - Fraud case (SSN mismatch)
5. **Case 20** - Clean comparison case

## Key Differences from General Setup

| Aspect | Original | Updated |
|--------|----------|---------|
| Deceased Location | Various US cities | **LA County only** |
| Financial Institutions | 8 different banks/brokerages | **1 bank only** (Community National Bank) |
| Account Types | 6 types (checking, savings, 401k, IRA, brokerage, money market) | **IRA only** |
| Death Certificate | Washington State template | **LA County template** |
| Beneficiary Form | Generic transfer application | **Community National Bank IRA Beneficiary Claim Form** |

## All Cases Summary

Run `python3 query_helper.py all` to see complete list:

```
All Cases (20):
Case 1: Sandra Wilson (DOD: 2025-05-16) - El Monte, CA
Case 2: David Lee (DOD: 2026-06-10) - El Monte, CA
Case 3: George Scott (DOD: 2024-08-19) - Pomona, CA
...
Case 13: Jennifer Thompson (DOD: 2026-04-11) ⚠️ FRAUD - Los Angeles, CA
...
Case 19: Elizabeth Walker (DOD: 2026-05-11) ⚠️ FRAUD - Pomona, CA
Case 20: Richard Williams (DOD: 2024-09-18) - Los Angeles, CA
```

## Validation Checklist

Before creating documents, verify:
- [ ] All deceased addresses are in LA County, CA
- [ ] All accounts are Community National Bank IRAs
- [ ] Account IDs use format IRA-XXX-X
- [ ] Routing number is 122016066 for all accounts
- [ ] Death certificate template is LA County format
- [ ] Beneficiary claim form is Community National Bank IRA form
- [ ] Fraud cases 13 and 19 are identified
- [ ] All data matches MASTER_REFERENCE_ALL_PERSONS.csv

## Files Updated

- ✓ All 5 databases regenerated
- ✓ MASTER_REFERENCE_ALL_PERSONS.csv updated
- ✓ MASTER_REFERENCE_ALL_PERSONS.json updated
- ✓ Query helper still works with new data
- ✓ This README created

Ready for POC document creation! 🚀
