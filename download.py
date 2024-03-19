from argparse import ArgumentParser
import base64
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import requests
from requests.exceptions import HTTPError
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
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
args = parser.parse_args()

auth_cookie = Path('config', 'auth-cookie.txt').read_text()

# helper functions

def fetch(path: str) -> str:
    response =  requests.get('https://www.gig-o-matic.com/' + path, cookies={'auth': auth_cookie})
    response.raise_for_status()
    return response.text

def list_bands(bands: list):
    print(f'You have access to these bands:\n    {"name":<15}id\n{"-" * 100}')
    for band in bands:
        print(f'    {band["shortname"]:<15}{band["id"]}')
    print('')

def get_band_info(band_id_or_short_name: str) -> tuple[str, str]:
    try:
        band = fetch('api/band/' + band_id_or_short_name)
        return band['id'], band['shortname']
    except HTTPError as ex:
        if ex.response.status_code != 404:
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
    return re.sub(' {2,}', ' ', out_dir_name).strip()

def get_gigs(band_id: str) -> list[Gig]:
    path = Path('cache', 'gigs.json')
    if path.exists():
        gigs_json = json.loads(path.read_text())
        if gigs_json['band_id'] != band_id:
            path.unlink()

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
    path.write_text(json.dumps(gigs_json, indent=2))

    return gigs

def download_gig_pdf(gig: Gig, out_dir: Path, driver: WebDriver):
    path = Path(out_dir, gig.fileSafeName + '.pdf')
    if path.exists():
        return

    with NamedTemporaryFile('w+', suffix='.html') as t:
        t.write(fetch('gig_info.html?gk=' + gig.id))
        driver.get('file://' + t.name)
        path.write_bytes(base64.b64decode(driver.print_page()))

def download_gig_json(gig: Gig, out_dir: Path):
    path = Path(out_dir, gig.fileSafeName + '.json')
    if path.exists():
        return

    path.write_text(fetch('api/gig/' + gig.id))

# command processing

match args.command:
    case 'list':
        bands = json.loads(fetch('api/bands'))
        list_bands(bands)

    case 'download':
        (band_id, band_short_name) = get_band_info(args.band_id_or_short_name)
        out_dir = get_out_dir(band_short_name)
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
        with getattr(webdriver, args.browser)() as driver:
            for gig in gigs:
                print(gig.fileSafeName)
                download_gig_pdf(gig, out_dir, driver)
                download_gig_json(gig, out_dir)
