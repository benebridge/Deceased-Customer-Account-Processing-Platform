# Quick Start Guide - Testing Real Verification

## Step 1: Install Dependencies

```bash
cd verification_services
pip install boto3 requests python-dotenv
```

## Step 2: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# .env file
PERSONA_API_KEY=persona_sandbox_YOUR_KEY_HERE
PERSONA_TEMPLATE_ID=itmpl_YOUR_TEMPLATE_ID  # Optional

AWS_ACCESS_KEY_ID=AKIA_YOUR_KEY_HERE
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY_HERE
AWS_REGION=us-west-2
```

## Step 3: Test AWS Textract with Your Death Certificate

```python
# test_textract.py
from death_cert_verification.textract_verifier import verify_death_certificate_textract

# Path to your death certificate (PDF or image)
cert_path = "/path/to/your/death_certificate.pdf"

# Expected values from your account records
expected_name = "Jane Doe"  # Replace with actual name
expected_ssn = "123-45-6789"  # Optional
expected_dod = "01/15/2024"  # Optional

# Run verification
result = verify_death_certificate_textract(
    file_path=cert_path,
    expected_deceased_name=expected_name,
    expected_ssn=expected_ssn,
    expected_date_of_death=expected_dod
)

print(f"Status: {result.status}")
print(f"Confidence: {result.confidence_score}%")
print(f"Processing Time: {result.processing_time_ms}ms")
print(f"\nExtracted Data:")
for key, value in result.details.get('extracted_data', {}).items():
    print(f"  {key}: {value}")
```

Run it:
```bash
python test_textract.py
```

## Step 4: Test Persona ID Verification

```python
# test_persona.py
from id_verification.persona_verifier import create_verification_inquiry, check_verification_status

# Create a verification inquiry
result = create_verification_inquiry(
    reference_id="TEST-001",  # Your internal reference (e.g., case number)
    expected_name="John Doe",  # Optional
    expected_dob="1990-01-15"  # Optional
)

if result.status.value == 'pending':
    inquiry_id = result.details['inquiry_id']
    inquiry_url = result.details['inquiry_url']

    print(f"Verification started!")
    print(f"Inquiry ID: {inquiry_id}")
    print(f"\nSend this URL to the user:")
    print(f"{inquiry_url}")
    print(f"\nUser will:")
    print(f"1. Upload government ID (both sides)")
    print(f"2. Take selfie with liveness detection")
    print(f"3. Persona verifies automatically")

    # Later, check status
    input("\nPress Enter after user completes verification...")

    status_result = check_verification_status(inquiry_id)
    print(f"\nVerification Status: {status_result.status}")
    print(f"Confidence: {status_result.confidence_score}%")
    print(f"\nExtracted Data:")
    for key, value in status_result.details.get('extracted_data', {}).items():
        if value:
            print(f"  {key}: {value}")
else:
    print(f"Error: {result.error_message}")
```

Run it:
```bash
python test_persona.py
```

## What Happens in Persona Flow:

1. **You create an inquiry** - generates a unique URL
2. **Send URL to user** - via email, SMS, or embedded in your app
3. **User completes verification**:
   - Takes photo of ID front
   - Takes photo of ID back
   - Takes selfie (with liveness detection - looks left/right)
4. **Persona processes automatically**:
   - Validates ID authenticity
   - Checks security features
   - Verifies with AAMVA database (for driver's licenses)
   - Matches face to ID photo
   - Returns result
5. **You check status** - get verification result + extracted data

## Expected Results

### Textract (Death Certificate):
```
Status: VERIFIED
Confidence: 92.5%
Processing Time: 3420ms

Extracted Data:
  decedent_name: JANE MARIE DOE
  date_of_death: 01/15/2024
  ssn: 123-45-6789
  date_of_birth: 05/20/1955
  sex: F
  place_of_death: SEATTLE, KING COUNTY, WASHINGTON
  state_file_number: 2024-001234
  certifier_name: DR. SMITH
```

### Persona (ID Verification):
```
Status: VERIFIED
Confidence: 95.0%

Extracted Data:
  name_first: John
  name_last: Doe
  birthdate: 1990-01-15
  address: 123 Main St
  city: Seattle
  state: WA
  postal_code: 98101
  id_number: WDL123456ABC
  id_state: WA

Verifications:
  government-id-verification: passed
  selfie-verification: passed
  database-verification: passed (AAMVA)
  liveness-check: passed
```

## Troubleshooting

### Textract Errors:

**"Unable to parse credentials"**
- Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
- Ensure no quotes around values in .env
- Try running `aws configure` to set up credentials

**"AccessDeniedException"**
- IAM user needs `AmazonTextractFullAccess` policy
- Check region is correct (us-west-2, us-east-1, etc.)

**"InvalidParameterException"**
- File might be corrupted or wrong format
- Textract supports: PNG, JPG, PDF
- File must be < 10 MB

### Persona Errors:

**"Invalid API key"**
- Double-check PERSONA_API_KEY in .env
- Use sandbox key for testing (starts with `persona_sandbox_`)
- Production keys start with `persona_production_`

**"Template not found"**
- PERSONA_TEMPLATE_ID is optional for basic flow
- Create template in Persona dashboard for custom flows
- Can omit for simple government ID verification

## Cost Monitoring

### Check AWS Costs:
1. Go to AWS Console → Billing Dashboard
2. View by service → Textract
3. Should see ~$0.05 per certificate processed

### Check Persona Usage:
1. Go to Persona Dashboard → Usage
2. View verification count
3. Sandbox is free, production charges per verification

## Next Steps

Once testing works:
1. Integrate into main BeneBridge workflow
2. Add error handling and retry logic
3. Store verification results in database
4. Set up webhooks for async notifications
5. Add audit logging for compliance

## Privacy Note

Remember:
- ✅ All processing happens locally or via secure APIs
- ✅ Textract runs in YOUR AWS account (you control data)
- ✅ Persona is SOC 2 Type II certified
- ✅ Data encrypted in transit (HTTPS) and at rest
- ❌ Never commit .env file to git (add to .gitignore)
- ❌ Never share API keys in screenshots or chat
