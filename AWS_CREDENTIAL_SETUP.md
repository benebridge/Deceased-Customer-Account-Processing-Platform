# AWS Textract Setup - Step by Step Guide

## Step 1: Create AWS Account (if you don't have one)

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Follow the signup process (requires credit card, but Textract has a free tier)

**Free Tier**: 1,000 pages/month for the first 3 months

---

## Step 2: Create IAM User with Textract Access

1. **Log in to AWS Console**: https://console.aws.amazon.com

2. **Go to IAM** (Identity and Access Management):
   - Search for "IAM" in the top search bar
   - Click on "IAM"

3. **Create a New User**:
   - Click "Users" in the left sidebar
   - Click "Create user"
   - Enter username: `textract-user` (or any name you want)
   - Click "Next"

4. **Set Permissions**:
   - Select "Attach policies directly"
   - Search for and select these policies:
     - `AmazonTextractFullAccess` (for full Textract access)
   - Click "Next"

5. **Review and Create**:
   - Click "Create user"

---

## Step 3: Create Access Keys

1. **Click on the user** you just created (`textract-user`)

2. **Go to Security Credentials tab**

3. **Create Access Key**:
   - Scroll down to "Access keys"
   - Click "Create access key"
   - Select use case: "Command Line Interface (CLI)"
   - Check the box "I understand the above recommendation"
   - Click "Next"
   - (Optional) Add description: "BeneBridge POC Textract"
   - Click "Create access key"

4. **IMPORTANT - Save Your Keys**:
   - You'll see:
     - **Access key ID**: Looks like `AKIAIOSFODNN7EXAMPLE`
     - **Secret access key**: Looks like `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

   ⚠️ **Save these now!** The secret key will NEVER be shown again!

   - Click "Download .csv file" to save them
   - Or copy them to a secure location

5. **Click "Done"**

---

## Step 4: Configure AWS CLI

Now open your terminal and run:

```bash
aws configure
```

You'll be prompted for:

1. **AWS Access Key ID**: Paste your access key ID from Step 3
2. **AWS Secret Access Key**: Paste your secret access key from Step 3
3. **Default region name**: Enter `us-east-1`
4. **Default output format**: Enter `json`

Example:
```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

---

## Step 5: Verify Configuration

Test that your credentials work:

```bash
aws sts get-caller-identity
```

You should see output like:
```json
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/textract-user"
}
```

If you see this, you're all set! ✅

---

## Step 6: Test Textract Extraction

Now test the extraction on your documents:

```bash
cd bank_operations_platform
python3 textract_extraction.py
```

You should see extracted data from all three document types!

---

## Troubleshooting

### "Unable to locate credentials"
- Run `aws configure` again and make sure you entered the keys correctly
- Check that `~/.aws/credentials` file exists:
  ```bash
  cat ~/.aws/credentials
  ```

### "AccessDeniedException"
- Make sure you attached the `AmazonTextractFullAccess` policy to your IAM user
- Go back to IAM console → Users → your user → Permissions tab

### "Region not found"
- Make sure you set the region to `us-east-1` when running `aws configure`

---

## Cost Estimate

Textract pricing (after free tier):
- **AnalyzeDocument**: $1.50 per 1,000 pages
- **AnalyzeID**: $2.00 per 1,000 documents

For your 93 test cases (279 documents total):
- Death certificates: 93 pages × $0.0015 = **$0.14**
- Driver's licenses: 93 documents × $0.002 = **$0.19**
- Claim forms: 186 pages × $0.0015 = **$0.28**
- **Total: ~$0.61**

Very affordable for testing!

---

## Security Best Practices

1. **Never commit AWS credentials to Git**
   - The `.aws/` folder is automatically ignored by Git

2. **Use IAM users with minimal permissions**
   - We only gave Textract access, not full AWS access

3. **Rotate keys periodically**
   - Create new access keys every few months

4. **Delete unused keys**
   - If you're done testing, delete the access key from IAM console

---

## Next Steps

Once you've configured your credentials and tested the extraction:

1. I'll integrate Textract into your Flask app
2. Replace the current extraction methods with Textract
3. Test end-to-end with real documents

Let me know when you're ready! 🚀
