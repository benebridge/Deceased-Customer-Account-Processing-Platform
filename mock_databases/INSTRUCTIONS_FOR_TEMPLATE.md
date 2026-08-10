# Instructions for Filling Out DECEASED_DATA_TEMPLATE.csv

## Overview
This template contains the 20 deceased persons from your death certificates. You need to fill in the missing data from each death certificate PDF.

## File Location
**Template:** `DECEASED_DATA_TEMPLATE.csv`

## Fields to Fill In

For each person (Case 1-20), look at the corresponding death certificate PDF and fill in these fields:

### Required Fields:
1. **ssn** - Social Security Number (format: XXX-XX-XXXX)
2. **dob** - Date of Birth (format: MM/DD/YYYY)
3. **dod** - Date of Death (format: MM/DD/YYYY)
4. **address_street** - Street address (e.g., "356 Valley Way")
5. **height** - Height (format: 5'10")
6. **weight** - Weight in pounds (e.g., 175)
7. **eye_color** - Eye color (e.g., Brown, Blue, Green, Hazel, Gray)

### Pre-filled Fields (verify these are correct):
- **case_id** - Case number (1-20)
- **full_name, first_name, last_name** - Name from death certificate filename
- **gender** - M or F
- **address_city** - City (extracted from PDFs, but verify)
- **address_state** - Should be "CA" for all
- **address_zip** - Zip code (extracted from PDFs, but verify)

## Death Certificate Mapping

| Case | Death Certificate PDF | Deceased Name |
|------|----------------------|---------------|
| 1 | Anthony-King-DC.pdf | Anthony King |
| 2 | Anthony-Moore-DC.pdf | Anthony Moore |
| 3 | Daniel-Martin-DC.pdf | Daniel Martin |
| 4 | David-Lee-DC.pdf | David Lee |
| 5 | Donna-Rodriguez-DC.pdf | Donna Rodriguez |
| 6 | Dorothy-Lee-DC.pdf | Dorothy Lee |
| 7 | Elizabeth-Walker-DC.pdf | Elizabeth Walker |
| 8 | George-Scott-DC.pdf | George Scott |
| 9 | James-Allen-DC.pdf | James Allen |
| 10 | Jennifer-Thompson-DC.pdf | Jennifer Thompson |
| 11 | Jessica-Taylor-DC.pdf | Jessica Taylor |
| 12 | Kenneth-Jones-DC.pdf | Kenneth Jones |
| 13 | Margaret-Wilson-DC.pdf | Margaret Wilson |
| 14 | Matthew-Lewis-DC.pdf | Matthew Lewis |
| 15 | Nancy-Wilson-DC.pdf | Nancy Wilson |
| 16 | Patricia-Martin-DC.pdf | Patricia Martin |
| 17 | Robert-Anderson-DC.pdf | Robert Anderson |
| 18 | Sandra-Wilson-DC.pdf | Sandra Wilson |
| 19 | Sarah-Sanchez-DC.pdf | Sarah Sanchez |
| 20 | William-Williams-DC.pdf | William Williams |

## Tips

1. **Open the CSV in Excel or Google Sheets** for easier editing
2. **One certificate at a time** - Open each PDF and fill in the corresponding row
3. **Date format** - Use MM/DD/YYYY (e.g., 05/16/2025, not 5/16/25)
4. **SSN format** - Include dashes: XXX-XX-XXXX
5. **Height format** - Use feet and inches with apostrophe and quote: 5'10"
6. **Save frequently** as you work through the certificates

## After Completing the Template

Once you've filled in all the data:

1. Save the file as **`DECEASED_DATA_COMPLETE.csv`**
2. Let me know, and I will:
   - Update the database with this correct data
   - Keep the beneficiaries unchanged (California residents with driver's license info)
   - Regenerate the Word document with the corrected deceased information

## Example Row (Completed)

```csv
1,Anthony King,Anthony,King,M,828-27-6160,10/17/1984,10/18/2024,356 Valley Way,Torrance,CA,90501,5'11",180,Brown
```

## Questions?

If you have any questions while filling this out, just let me know!
