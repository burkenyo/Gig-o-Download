from argparse import ArgumentParser
from datetime import date, datetime
import locale
import re
import shutil
from selenium import webdriver
import sys
from . import download
from . import make_csv
from .paths import *

if not re.fullmatch('utf-?8', locale.getpreferredencoding(), re.IGNORECASE):
    print('This utility needs to be run with utf-8 default encoding enabled!', file=sys.stderr)
    print(f'To enable utf-8 mode please invoke via “python -X utf8 {__name__} ...”')
    exit(1)

if (AUTH_COOKIE_FILE.exists()):
    # I don’t want to store an auth token for longer than necessary, so remove any existing cookie that’s too old
    stat_result = AUTH_COOKIE_FILE.stat()
    # Windows comptability with Python < 3.12
    create_datetime = datetime.fromtimestamp(getattr(stat_result, 'st_birthtime', stat_result.st_ctime))
    if (datetime.now() - create_datetime).days >= 3:
        AUTH_COOKIE_FILE.unlink()

parser = ArgumentParser(description='Downloads archived gig info from Gig-o-Matic version 2.')
commands = parser.add_subparsers(title='commands', dest='command', required=True)
commands.add_parser('list', help='List the bands the user has access to.')
download_parser = commands.add_parser('download', help='Download archived gig info. Creates PDFs of archived gigs '
                                      + 'for browsing and JSON files containing the raw database records.')
download_parser.add_argument('band_id_or_short_name',
                             help='The Gig-o-Matic database ID or short name for your band.')
download_parser.add_argument('-s', '--start-date', type=date.fromisoformat,
                             help='The earliest day of gigs to include.')
download_parser.add_argument('-e', '--end-date', type=date.fromisoformat, default=date.today(),
                             help='The latest day of gigs to include. Defaults to today.')
download_parser.add_argument('-b', '--browser', choices=['Chrome', 'ChromiumEdge', 'Firefox'], default='Firefox',
                             help='The browser to use to generate PDFs of archived gigs. Chrome and ChromiumEdge '
                             + 'tend to be faster; Firefox tends to produce smaller sizes. Defaults to Firefox.')
make_csv_parser = commands.add_parser('make-csv', help='Combine and convert downloaded gigs’ raw JSON files into '
                                      + 'a single CSV file suitable for searching and analysis. The generated file '
                                      + 'can be opened in Microsoft Excel or uploaded to Google Sheets.')
make_csv_parser.add_argument('out_dir', choices=[p.name for p in Path(DATA_PATH).iterdir() if p.is_dir()],
                             help='The directory where gigs’ raw JSON files are found.')
commands.add_parser('clear-cache', help='Clear cached data, including the auth cookie.')
args = parser.parse_args()

match args.command:
    case 'list':
        download.list_bands()

    case 'download':
        browser_class = getattr(webdriver, args.browser)
        download.download(args.band_id_or_short_name, browser_class, args.start_date, args.end_date)

    case 'clear-cache':
        shutil.rmtree(CACHE_PATH)

    case 'make-csv':
        out_dir = Path(DATA_PATH, args.out_dir)
        make_csv.make_csv(out_dir)

def main():
    pass
