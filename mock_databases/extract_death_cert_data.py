#!/usr/bin/env python3
"""
Extract data from existing death certificates to populate database
"""

import os
import re
from pathlib import Path

# Based on the filenames, here are the 20 deceased persons
DECEASED_FROM_CERTS = [
    "Anthony King",
    "Anthony Moore",
    "Daniel Martin",
    "David Lee",
    "Donna Rodriguez",
    "Dorothy Lee",
    "Elizabeth Walker",
    "George Scott",
    "James Allen",
    "Jennifer Thompson",
    "Jessica Taylor",
    "Kenneth Jones",
    "Margaret Wilson",
    "Matthew Lewis",
    "Nancy Wilson",
    "Patricia Martin",
    "Robert Anderson",
    "Sandra Wilson",
    "Sarah Sanchez",
    "William Williams"
]

def main():
    print("=" * 80)
    print("DECEASED PERSONS FROM DEATH CERTIFICATES")
    print("=" * 80)
    print()

    cert_dir = Path("/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/Mock Death Certs")

    # Get all PDF files
    cert_files = sorted(cert_dir.glob("*.pdf"))

    print(f"Found {len(cert_files)} death certificates:")
    print()

    for i, cert_file in enumerate(cert_files, 1):
        # Extract name from filename (e.g., "Sandra-Wilson-DC.pdf" -> "Sandra Wilson")
        name_part = cert_file.stem.replace("-DC", "").replace("-", " ")
        print(f"{i:2d}. {name_part}")

    print()
    print("=" * 80)
    print()
    print("These are the 20 deceased persons that should be in the database.")
    print("The database should preserve their original data without modification.")

if __name__ == "__main__":
    main()
