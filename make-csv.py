import _startup
from argparse import ArgumentParser
import csv
import json
from pathlib import Path

parser = ArgumentParser(description="Combines and converts downloaded gigs’ raw JSON files into "
                        + "a single CSV file suitable for searching and analysis. The generated file "
                        + "can be opened in Microsoft Excel or uploaded to Google Sheets.")
parser.add_argument('out_dir', help='The directory where gigs’ raw JSON files are found.')
args = parser.parse_args()

out_dir = Path(args.out_dir)
gigs = [json.loads(f.read_text()) for f in out_dir.glob('*.json')]
gigs_csv_file = Path(out_dir, 'gigs.csv')

with gigs_csv_file.open('w', newline='') as f:
    csv_file = csv.DictWriter(f, gigs[0].keys())
    csv_file.writeheader()
    csv_file.writerows(gigs)

# remove unusual line terminators and zero-width characters
fixup_table = str.maketrans("\u2028\u2029", "\n\n", "\u200B\u200C\u200D")

gigs_csv_file.write_text(gigs_csv_file.read_text().translate(fixup_table))
print(f'Create CSV file at {gigs_csv_file}')

