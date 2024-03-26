import base64
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from datetime import date, datetime
import getpass
import json
from pathlib import Path
import re
import requests
from requests.exceptions import HTTPError
from selenium.webdriver.remote.webdriver import WebDriver
import sys
from tempfile import NamedTemporaryFile
from .paths import *

@dataclass
class Gig:
    id: str
    name: str
    date: date

    @property
    def fileSafeName(self) -> str:
        name = str(self.date) + ' ' + re.sub(r'[^A-Za-z0-9 ,\.-]', '', self.name)
        return re.sub(r'\s+', ' ', name).strip()

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
        login_response = requests.post('https://www.gig-o-matic.com/login', {'email': email, 'password': password},
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

def print_bands(bands: list):
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
        print_bands(bands)
        exit(1)

    return matched_bands[0]['id'], matched_bands[0]['shortname']

def get_out_dir(band_short_name: str) -> Path:
    out_dir_name = re.sub(r'[^A-Za-z0-9_-]', '', band_short_name)
    out_dir = Path(DATA_PATH, out_dir_name)
    out_dir.mkdir(exist_ok=True)
    return out_dir

def get_gigs(band_id: str) -> list[Gig]:
    gigs_file = Path(CACHE_PATH, 'gigs.json')
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
    gigs_file.write_text(json.dumps(gigs_json))

    return gigs

def download_gig_pdf(gig: Gig, out_dir: Path, browser: WebDriver) -> bool:
    path = Path(out_dir, gig.fileSafeName + '.pdf')
    if path.exists():
        return False

    # delete_on_close=False is needed on Windows so the browser can access the file.
    # The file is still deleted when the context manager exits
    with NamedTemporaryFile('w+', suffix='.html', delete_on_close=sys.platform != 'win32') as t:
        t.write(fetch('gig_info.html?gk=' + gig.id))
        browser.get('file://' + t.name)
        path.write_bytes(base64.b64decode(browser.print_page()))

        return True

def download_gig_json(gig: Gig, out_dir: Path) -> bool:
    path = Path(out_dir, gig.fileSafeName + '.json')
    if path.exists():
        return False

    path.write_text(json.dumps(json.loads(fetch('api/gig/' + gig.id)), indent=2))

    return True

# command processing

def list_bands():
    bands = json.loads(fetch('api/bands'))
    print_bands(bands)

def download(band_id_or_short_name: str, browser_class: type[WebDriver], start_date: date | None, end_date: date | None):
    (band_id, band_short_name) = get_band_info(band_id_or_short_name)
    gigs = get_gigs(band_id)
    if start_date:
        gigs = filter(lambda g: g.date >= start_date, gigs)
    if end_date:
        gigs = filter(lambda g: g.date <= end_date, gigs)
    gigs = list(gigs)

    if not len(gigs):
        print('No gigs to download!', file=sys.stderr)
        exit(1)

    print(f'Downloading {len(gigs)} gigs...')
    out_dir = get_out_dir(band_short_name)
    with browser_class() as browser:
        for gig in gigs:
            print(f'{gig.fileSafeName:<80}', end='')
            downloaded = download_gig_pdf(gig, out_dir, browser)
            downloaded |= download_gig_json(gig, out_dir)

            print('' if downloaded else ' (skipped)')
