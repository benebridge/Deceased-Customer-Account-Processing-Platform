#!/usr/bin/env python3
"""
Automatically generate California driver's licenses for all beneficiaries
"""

import sqlite3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def format_date_for_dl(date_str):
    """Convert date from YYYY-MM-DD to MM/DD/YYYY"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%m/%d/%Y")
    except:
        return date_str

def format_height(height_str):
    """Format height as 5'-06" """
    # Input: 5'6"
    # Output: 5'-06"
    if '"' in height_str:
        parts = height_str.replace('"', '').split("'")
        if len(parts) == 2:
            feet = parts[0]
            inches = parts[1].zfill(2)
            return f"{feet}'-{inches}\""
    return height_str

def main():
    base_dir = Path(__file__).parent
    parent_dir = base_dir.parent
    template_path = parent_dir / "Blank-California-Driving-License-Front.png"

    # Check if template exists
    if not template_path.exists():
        print(f"Error: Template not found at {template_path}")
        print("Please provide the correct path to the blank California DL template.")
        return

    # Create output directory
    output_dir = parent_dir / "Generated_Driver_Licenses"
    output_dir.mkdir(exist_ok=True)

    # Get all beneficiaries
    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    conn_ben.row_factory = sqlite3.Row
    c_ben = conn_ben.cursor()
    c_ben.execute("SELECT * FROM beneficiaries ORDER BY beneficiary_id")
    beneficiaries = [dict(row) for row in c_ben.fetchall()]
    conn_ben.close()

    # Get all identity records
    conn_id = sqlite3.connect(base_dir / "identity_verification.db")
    conn_id.row_factory = sqlite3.Row
    c_id = conn_id.cursor()
    c_id.execute("SELECT * FROM identity_records")
    identities = [dict(row) for row in c_id.fetchall()]
    conn_id.close()

    # Create identity lookup
    identity_map = {i['ssn']: i for i in identities}

    print("=" * 80)
    print("GENERATING CALIFORNIA DRIVER'S LICENSES")
    print("=" * 80)
    print()
    print(f"Template: {template_path}")
    print(f"Output directory: {output_dir}")
    print(f"Total beneficiaries: {len(beneficiaries)}")
    print()

    # Try to load fonts
    try:
        font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if not Path(font_path).exists():
            font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
        if not Path(font_path).exists():
            font_path = "/Library/Fonts/Arial.ttf"

        # Different font sizes (matching test script)
        font_tiny = ImageFont.truetype(font_path, 18)
        font_small = ImageFont.truetype(font_path, 22)
        font_medium = ImageFont.truetype(font_path, 28)
        font_large = ImageFont.truetype(font_path, 36)
        font_xlarge = ImageFont.truetype(font_path, 44)

        print(f"Using font: {font_path}")
    except Exception as e:
        print(f"Warning: Could not load Arial font: {e}")
        print("Using default font")
        font_tiny = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_xlarge = ImageFont.load_default()

    # Color definitions (based on the reference image)
    RED = (200, 0, 0)
    DARK_BLUE = (0, 51, 153)
    BLACK = (0, 0, 0)

    # Process each beneficiary
    for ben in beneficiaries:
        identity = identity_map.get(ben['ssn'])

        if not identity:
            print(f"⚠️  Skipping {ben['full_name']} - No identity record found")
            continue

        # Load template
        img = Image.open(template_path)
        draw = ImageDraw.Draw(img)

        # Format data
        dl_number = identity['drivers_license']
        exp_date = format_date_for_dl(identity['dl_expiration'])
        iss_date = format_date_for_dl(identity['dl_issue_date'])
        last_name = ben['last_name'].upper()
        first_name = ben['first_name'].upper()
        dob = format_date_for_dl(ben['dob'])
        sex = ben['gender']
        height = format_height(identity['height'])
        weight = f"{identity['weight']} lb"
        hair = identity['hair_color'][:3].upper()
        eyes = identity['eye_color'][:3].upper()

        # Get template dimensions
        width, height_img = img.size

        # Combine address into one line
        address_line1 = ben['address_street'].upper()
        address_line2 = f"{ben['address_city'].upper()}, {ben['address_state']} {ben['address_zip']}"
        full_address = f"{address_line1}, {address_line2}"

        # Text positions (perfected from test script)
        text_positions = [
            # DL Number (RED, large) - moved up slightly
            (int(width * 0.44), int(height_img * 0.31), dl_number, RED, font_xlarge),

            # Expiration (RED, below DL number) - moved up slightly, bigger font
            (int(width * 0.44), int(height_img * 0.36), exp_date, RED, font_large),

            # Last Name (below photo area, left side) - moved up
            (int(width * 0.42), int(height_img * 0.42), last_name, BLACK, font_medium),

            # First Name (below last name) - moved up, reduced spacing
            (int(width * 0.42), int(height_img * 0.46), first_name, BLACK, font_medium),

            # Address - single line, bigger font, moved slightly left
            (int(width * 0.38), int(height_img * 0.52), full_address, BLACK, font_medium),

            # Date of Birth - moved slightly up and a little bit left, bigger font, RED color
            (int(width * 0.45), int(height_img * 0.565), dob, RED, font_large),

            # Sex - moved up and to the right slightly more
            (int(width * 0.51), int(height_img * 0.71), sex, BLACK, font_medium),

            # Height - moved up a tiny bit and left to align with M
            (int(width * 0.51), int(height_img * 0.745), height, BLACK, font_medium),

            # Weight - moved to the right (twice as far), larger font
            (int(width * 0.64), int(height_img * 0.74), weight, BLACK, font_medium),

            # Hair (GRA) - moved up, larger font
            (int(width * 0.64), int(height_img * 0.71), hair, BLACK, font_medium),

            # Eyes (BLU) - moved up, bigger font
            (int(width * 0.80), int(height_img * 0.71), eyes, BLACK, font_medium),

            # Issue Date - moved down slightly more, bigger font
            (int(width * 0.78), int(height_img * 0.79), iss_date, BLACK, font_medium),
        ]

        # Draw all text
        for x, y, text, color, font in text_positions:
            draw.text((x, y), text, fill=color, font=font)

        # Save the generated license
        output_filename = f"CA_DL_{ben['beneficiary_id']:03d}_{ben['last_name']}_{ben['first_name']}.png"
        output_path = output_dir / output_filename
        img.save(output_path)

        print(f"✓ Generated: {output_filename}")

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"Generated {len(beneficiaries)} California driver's licenses")
    print(f"Output directory: {output_dir}")
    print()
    print("Note: You may need to adjust text positions in the script")
    print("      Open one of the generated images to check alignment")

if __name__ == "__main__":
    main()
