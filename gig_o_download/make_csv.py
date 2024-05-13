from argparse import ArgumentTypeError
import csv
import json
import sys
from .paths import *

def get_out_dir_from_args(data_dir: Path, out_dir_name: str) -> Path:
    def bail(message: str):
        print("Error with out-dir argument: " + message, file=sys.stderr)
        exit(1)

    if not data_dir.exists():
        bail('no gigs have been downloaded!')

    dirs = list(filter(Path.is_dir, data_dir.iterdir()))
    if not dirs:
        bail('no gigs have been downloaded!')

    out_dir = next(filter(lambda p: p.name.lower() == out_dir_name.lower(), dirs), None)
    if out_dir is None:
        msg = f'{out_dir_name} not found! Valid options are: {", ".join(d.name for d in dirs)}'
        bail(msg)

    if not next(out_dir.glob('*.json'), None):
        bail(f'no gigs have been downloaded for {out_dir.name}!')

    return out_dir

def make_csv(out_dir: Path):
    gigs = [json.loads(read_utf8(f)) for f in out_dir.glob('*.json')]
    gigs_csv_file = Path(out_dir, 'gigs.csv')

    with open_utf8(gigs_csv_file, 'w', '') as f:
        csv_file = csv.DictWriter(f, gigs[0].keys())
        csv_file.writeheader()
        csv_file.writerows(gigs)

    # remove unusual line terminators and zero-width characters
    fixup_table = str.maketrans('\u2028\u2029', '\n\n', '\u200B\u200C\u200D')

    write_utf8(gigs_csv_file, read_utf8(gigs_csv_file).translate(fixup_table))
    print(f'Created CSV file at {gigs_csv_file}')
