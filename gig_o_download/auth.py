from datetime import datetime
import getpass
import requests
import sys
from .paths import *

_AUTH_COOKIE_FILE = Path(CACHE_PATH, 'auth-cookie.txt')
_do_ensure_auth_cookie_file = True

def _ensure_auth_cookie_file():
    tries = 0
    while not _AUTH_COOKIE_FILE.exists():
        match tries:
            case 0:
                print('Auth cookie invalid, expired or not found! Please enter credentials.')
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
            write_utf8(_AUTH_COOKIE_FILE, auth_cookie)

        tries += 1

    test_response = requests.post('https://www.gig-o-matic.com/api/session', cookies={'auth': read_utf8(_AUTH_COOKIE_FILE)})
    if test_response.status_code != 200:
        _AUTH_COOKIE_FILE.unlink()
        _ensure_auth_cookie_file()

def cleanup_old_auth_cookie_file():
    if (_AUTH_COOKIE_FILE.exists()):
        # I don’t want to store an auth token for longer than necessary, so remove any existing cookie that’s too old
        stat_result = _AUTH_COOKIE_FILE.stat()
        create_datetime = datetime.fromtimestamp(stat_result.st_birthtime)
        if (datetime.now() - create_datetime).days >= 3:
            _AUTH_COOKIE_FILE.unlink()

def get_auth_cookie() -> str:
    global _do_ensure_auth_cookie_file
    if _do_ensure_auth_cookie_file:
        _ensure_auth_cookie_file()
        _do_ensure_auth_cookie_file = False

    return read_utf8(_AUTH_COOKIE_FILE)
