from argparse import ArgumentParser
import base64
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from datetime import date, datetime
import getpass
import json
import os
from pathlib import Path
import re
import requests
from requests.exceptions import HTTPError
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
import shutil
import sys
from tempfile import NamedTemporaryFile

os.chdir(os.path.dirname(__file__))

@dataclass
class Gig:
    id: str
    name: str
    date: date

    @property
    def fileSafeName(self) -> str:
        name = str(self.date) + ' ' + re.sub(r'[^A-Za-z0-9 ,\.-]', '', self.name)
        return re.sub(' {2,}', ' ', name).strip()

CACHE_PATH = Path('cache')
CACHE_PATH.mkdir(exist_ok=True)
AUTH_COOKIE_FILE = Path(CACHE_PATH, 'auth-cookie.txt')

if (AUTH_COOKIE_FILE.exists()):
    # I don’t want to store an auth token for longer than necessary, so remove any existing cookie that’s too old
    stat_result = AUTH_COOKIE_FILE.stat()
    # Windows comptability with Python < 3.12
    create_datetime = datetime.fromtimestamp(getattr(stat_result, 'st_birthtime', stat_result.st_ctime))
    if (datetime.now() - create_datetime).days >= 3:
        AUTH_COOKIE_FILE.unlink()

# arguments

parser = ArgumentParser(description='Downloads archived gig info from Gig-o-Matic version 2. '
                        + 'Creates PDFs of archived gigs for browsing and JSON files containing the '
                        + 'raw database records.')
commands = parser.add_subparsers(title='commands', dest='command', required=True)
commands.add_parser('list', help='List the bands the user has access to.')
download_parser = commands.add_parser('download', help='Download archived gig info.')
download_parser.add_argument('band_id_or_short_name',
                    help='The Gig-o-Matic database ID or short name for your band.')
download_parser.add_argument('-s', '--start-date', type=date.fromisoformat,
                    help='The earliest day of gigs to include.')
download_parser.add_argument('-e', '--end-date', type=date.fromisoformat, default=date.today(),
                    help='The latest day of gigs to include. Defaults to today.')
download_parser.add_argument('-b', '--browser', choices=['Chrome', 'ChromiumEdge', 'Firefox'], default='Firefox',
                    help='The browser to use to generate PDFs of archived gigs. Chrome and ChromiumEdge '
                        + 'tend to be faster; Firefox tends to produce smaller sizes. Defaults to Firefox.')
commands.add_parser('clear-cache', help='Clears cached data, including the auth cookie.')
args = parser.parse_args()

# helper functions

def ensureAuthCookie():
    tries = 0
    while not AUTH_COOKIE_FILE.exists():
        match tries:
            case 0:
                print('Auth cookie expired or not found! Please enter credentials.')
            case 3:
                print(f'Could not retrieve auth cookie after {tries} attempts!', file=sys.stderr)
                exit(1)
            case _:
                print('Could not retrieve auth cookie! Ensure you’ve entered the correct credentials.', file=sys.stderr)

        email = input('      Gig-o email: ')
        password = getpass.getpass('   Gig-o password: ')
        login_response = requests.post('https://www.gig-o-matic.com/login',{'email': email, 'password': password},
                                       allow_redirects=False)

        auth_cookie = login_response.cookies.get('auth')
        if auth_cookie is not None:
            AUTH_COOKIE_FILE.write_text(auth_cookie)

        tries += 1

def fetch(path: str) -> str:
    ensureAuthCookie()
    response = requests.get('https://www.gig-o-matic.com/' + path, cookies={'auth': AUTH_COOKIE_FILE.read_text()})
    if response.status_code == 401:
        AUTH_COOKIE_FILE.unlink()
    response.raise_for_status()
    return response.text

def list_bands(bands: list):
    print(f'\nYou have access to these bands:\n    {"name":<15}id\n{"-" * 100}')
    for band in bands:
        print(f'    {band["shortname"]:<15}{band["id"]}')
    print('')

def get_band_info(band_id_or_short_name: str) -> tuple[str, str]:
    try:
        band = fetch('api/band/' + band_id_or_short_name)
        return band['id'], band['shortname']
    except HTTPError as ex:
        if ex.response.status_code not in [404]:
            raise

    bands = json.loads(fetch('api/bands'))
    matched_bands = list(filter(lambda b: b['shortname'].lower() == band_id_or_short_name.lower(), bands))

    if (len(matched_bands)) == 0:
        print(f'Band {band_id_or_short_name} does not exist or you do not have access to it!', file=sys.stderr)
        list_bands(bands)
        exit(1)

    return matched_bands[0]['id'], matched_bands[0]['shortname']

def get_out_dir(band_short_name: str) -> Path:
    out_dir_name = 'out-' + re.sub(r'[^A-Za-z0-9_]', '', band_short_name)
    out_dir = Path(re.sub(' {2,}', ' ', out_dir_name).strip())
    out_dir.mkdir(exist_ok=True)
    return out_dir

def get_gigs(band_id: str) -> list[Gig]:
    gigs_file = Path('cache', 'gigs.json')
    if gigs_file.exists():
        gigs_json = json.loads(gigs_file.read_text())
        if gigs_json['band_id'] != band_id:
            gigs_file.unlink()

            return get_gigs(band_id)

        print('Using cached gigs list...')
        return sorted((Gig(g['id'], g['name'], date.fromisoformat(g['date'])) for g in gigs_json['gigs']),
                      key=lambda g: g.date)

    def getGig(div: Tag) -> Gig:
        anchor = div.find('a')
        id = re.search(r'(?<=gk=).*$', anchor['href'])[0]
        name = anchor.text.strip()
        date = datetime.strptime(div.find('div').text.strip(), '%m/%d/%y').date()

        return Gig(id, name, date)

    print('Fetching gigs list...')
    archivePageHtml = BeautifulSoup(fetch('band_gig_archive?bk=' + band_id), 'html.parser')
    gigs = sorted((getGig(r) for r in archivePageHtml.css.select('div.row div.row')), key=lambda g: g.date)
    gigs_json = {'band_id': band_id, 'gigs': [{'id': g.id, 'name': g.name, 'date': g.date.isoformat()} for g in gigs]}
    gigs_file.write_text(json.dumps(gigs_json, indent=2))

    return gigs

def download_gig_pdf(gig: Gig, out_dir: Path, driver: WebDriver) -> bool:
    path = Path(out_dir, gig.fileSafeName + '.pdf')
    if path.exists():
        return False

    with NamedTemporaryFile('w+', suffix='.html') as t:
        t.write(fetch('gig_info.html?gk=' + gig.id))
        driver.get('file://' + t.name)
        path.write_bytes(base64.b64decode(driver.print_page()))

        return True

def download_gig_json(gig: Gig, out_dir: Path) -> bool:
    path = Path(out_dir, gig.fileSafeName + '.json')
    if path.exists():
        return False

    path.write_text(fetch('api/gig/' + gig.id))

    return True

# command processing

match args.command:
    case 'list':
        bands = json.loads(fetch('api/bands'))
        list_bands(bands)

    case 'download':
        (band_id, band_short_name) = get_band_info(args.band_id_or_short_name)
        gigs = get_gigs(band_id)
        if args.start_date:
            gigs = filter(lambda g: g.date >= args.start_date, gigs)
        if args.end_date:
            gigs = filter(lambda g: g.date <= args.end_date, gigs)
        gigs = list(gigs)

        if not len(gigs):
            print('No gigs to download!', file=sys.stderr)
            exit(1)

        print(f'Downloading {len(gigs)} gigs...')
        out_dir = get_out_dir(band_short_name)
        with getattr(webdriver, args.browser)() as driver:
            for gig in gigs:
                print(f'{gig.fileSafeName:<80}', end='')
                downloaded = download_gig_pdf(gig, out_dir, driver)
                downloaded |= download_gig_json(gig, out_dir)

                print('' if downloaded else ' (skipped)')

    case 'clear-cache':
        shutil.rmtree(CACHE_PATH)
