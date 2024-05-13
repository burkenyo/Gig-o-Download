from argparse import ArgumentParser
from datetime import date
import shutil
from selenium import webdriver

from . import auth
from . import download
from . import make_csv
from .paths import *

auth.cleanup_old_auth_cookie_file()

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
download_parser.add_argument('-d', '--data-dir', type=get_out_dir_from_arg, default=DEFAULT_DATA_PATH,
                             help='The directory into which to download the archive.')
make_csv_parser = commands.add_parser('make-csv', help='Combine and convert downloaded gigs’ raw JSON files into '
                                      + 'a single CSV file suitable for searching and analysis. The generated file '
                                      + 'can be opened in Microsoft Excel or uploaded to Google Sheets.')
make_csv_parser.add_argument('archive_dir',
                             help='The directory (usually the band’s short name) where gigs’ raw JSON files are found. '
                             + 'If --data-dir is specified, it is searched for this.')
make_csv_parser.add_argument('-d', '--data-dir', type=get_out_dir_from_arg, default=DEFAULT_DATA_PATH,
                             help='The directory in which to search for the downloaded archive.')
commands.add_parser('clear-cache', help='Clear cached data, including the auth cookie.')
args = parser.parse_args()

match args.command:
    case 'list':
        download.list_bands()

    case 'download':
        browser_class = getattr(webdriver, args.browser)
        download.download(args.data_dir, args.band_id_or_short_name, browser_class, args.start_date, args.end_date)

    case 'clear-cache':
        shutil.rmtree(CACHE_PATH)

    case 'make-csv':
        out_dir = make_csv.get_out_dir_from_args(args.data_dir, args.archive_dir)
        make_csv.make_csv(out_dir)


def main():
    """A shim to support installation as a command-line script.
    Actual command processing occurs at the module level.
    """
    pass
