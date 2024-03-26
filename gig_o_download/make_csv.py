from argparse import ArgumentTypeError
import csv
import json
from pathlib import Path
import re
from .paths import *

def make_csv(out_dir: Path):
    gigs = [json.loads(f.read_text()) for f in out_dir.glob('*.json')]
    gigs_csv_file = Path(out_dir, 'gigs.csv')

    with gigs_csv_file.open('w', newline='') as f:
        csv_file = csv.DictWriter(f, gigs[0].keys())
        csv_file.writeheader()
        csv_file.writerows(gigs)

    # remove unusual line terminators and zero-width characters
    fixup_table = str.maketrans("\u2028\u2029", "\n\n", "\u200B\u200C\u200D")

    gigs_csv_file.write_text(gigs_csv_file.read_text().translate(fixup_table))
    print(f'Created CSV file at {gigs_csv_file}')
