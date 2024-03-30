import base64
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from datetime import date, datetime
import json
import re
import requests
from requests.exceptions import HTTPError
from selenium.webdriver.remote.webdriver import WebDriver
import sys
from . import auth
from .paths import *

@dataclass
class Gig:
    id: str
    name: str
    date: date

    @property
    def file_safe_name(self) -> str:
        name = str(self.date) + ' ' + re.sub(r'[^A-Za-z0-9 ,\._-]', '', self.name)
        return re.sub(r'\s+', ' ', name).strip()

@dataclass
class Band:
    id: str
    short_name: str
    name: str

    @property
    def file_safe_name(self) -> str:
        return re.sub(r'[^A-Za-z0-9_-]', '', self.short_name)

# helper functions

def _fetch(path: str) -> str:
    response = requests.get('https://www.gig-o-matic.com/' + path, cookies={'auth': auth.get_auth_cookie()})
    response.raise_for_status()
    return response.text

def _get_bands() -> list[Band]:
    return [Band(b['id'], b['shortname'], b['name']) for b in json.loads(_fetch('api/bands'))]

def _print_bands(bands: list[Band]):
    print(f'\nYou have access to these bands:\n    {"name":<15}id\n{"-" * 100}')
    for band in bands:
        print(f'    {band.file_safe_name:<15}{band.id}')
    print('')

def _get_band(band_id_or_short_name: str) -> Band:
    try:
        band_json = json.loads(_fetch('api/band/' + band_id_or_short_name))
        return Band(band_id_or_short_name, band_json['shortname'], band_json['name'])
    except HTTPError as ex:
        if ex.response.status_code not in [401, 404]:
            raise

    bands = _get_bands()
    matched_band = next(filter(lambda b: band_id_or_short_name.lower() in [b.short_name.lower(), b.file_safe_name.lower()], bands), None)

    if not matched_band:
        print(f'Band {band_id_or_short_name} does not exist or you do not have access to it!', file=sys.stderr)
        _print_bands(bands)
        exit(1)

    return matched_band

def _get_gigs(band: Band) -> list[Gig]:
    band_id = band.id
    gigs_file = Path(ensure_dir(CACHE_PATH, band.file_safe_name), 'gigs.json')
    if gigs_file.exists():
        gigs_json = json.loads(read_utf8(gigs_file))

        print('Using cached gigs list...')
        return sorted((Gig(g['id'], g['name'], date.fromisoformat(g['date'])) for g in gigs_json),
                      key=lambda g: g.date)

    def get_gig(div: Tag) -> Gig:
        anchor = div.find('a')
        id = re.search(r'(?<=gk=).*$', anchor['href'])[0]
        name = anchor.text.strip()
        date = datetime.strptime(div.find('div').text.strip(), '%m/%d/%y').date()

        return Gig(id, name, date)

    print('Fetching gigs list...')
    archivePageHtml = BeautifulSoup(_fetch('band_gig_archive?bk=' + band_id), 'html.parser')
    gigs = sorted((get_gig(r) for r in archivePageHtml.css.select('div.row div.row')), key=lambda g: g.date)
    gigs_json = [{'id': g.id, 'name': g.name, 'date': g.date.isoformat()} for g in gigs]
    write_utf8(gigs_file, json.dumps(gigs_json))

    return gigs

def _download_gig_pdf(gig: Gig, out_dir: Path, browser: WebDriver) -> bool:
    file = Path(out_dir, gig.file_safe_name + '.pdf')
    if file.exists():
        return False

    with temporary_utf8_file('w+', '.html', sys.platform != 'win32') as temp_file:
        temp_file.write(_fetch('gig_info.html?gk=' + gig.id))
        browser.get('file://' + temp_file.name)
        file.write_bytes(base64.b64decode(browser.print_page()))

        return True

def _download_gig_json(gig: Gig, out_dir: Path) -> bool:
    file = Path(out_dir, gig.file_safe_name + '.json')
    if file.exists():
        return False

    write_utf8(file, json.dumps(json.loads(_fetch('api/gig/' + gig.id)), indent=2))

    return True

# command processing

def list_bands():
    _print_bands(_get_bands())

def download(band_id_or_short_name: str, browser_class: type[WebDriver], start_date: date | None, end_date: date | None):
    band = _get_band(band_id_or_short_name)
    gigs = _get_gigs(band)
    if start_date:
        gigs = filter(lambda g: g.date >= start_date, gigs)
    if end_date:
        gigs = filter(lambda g: g.date <= end_date, gigs)
    gigs = list(gigs)

    if not len(gigs):
        print('No gigs to download!', file=sys.stderr)
        exit(1)

    print(f'Downloading {len(gigs)} gigs...')
    out_dir = ensure_dir(DATA_PATH, band.file_safe_name)
    with browser_class() as browser:
        for gig in gigs:
            print(f'{gig.file_safe_name:<80}', end='')
            downloaded = _download_gig_pdf(gig, out_dir, browser)
            downloaded |= _download_gig_json(gig, out_dir)

            print('' if downloaded else ' (skipped)')
