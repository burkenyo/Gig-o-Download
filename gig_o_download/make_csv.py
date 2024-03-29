from argparse import ArgumentTypeError
import csv
import json
from pathlib import Path
from .paths import *

def get_out_dir_from_arg(out_dir_name: str) -> Path:
    dirs = list(filter(Path.is_dir, DATA_PATH.iterdir()))
    if not dirs:
        raise ArgumentTypeError("No gigs have been downloaded!")

    out_dir = next(filter(lambda p: p.name.lower() == out_dir_name.lower(), dirs), None)
    if out_dir is None:
        msg = f"{out_dir_name} not found! Valid options are: {", ".join(d.name for d in dirs)}"
        raise ArgumentTypeError(msg)

    if not next(out_dir.glob('*.json'), None):
        raise ArgumentTypeError(f"No gigs have been downloaded for {out_dir.name}!")

    return out_dir

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
