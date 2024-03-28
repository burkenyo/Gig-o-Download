from pathlib import Path
import platformdirs

def ensureDir(base: Path, dir_name: str):
    dir = Path(base, dir_name)
    dir.mkdir(exist_ok=True)
    return dir

APP_NAME = 'Gig-o-Download'
CACHE_PATH = platformdirs.user_cache_path(APP_NAME, ensure_exists=True)
AUTH_COOKIE_FILE = Path(CACHE_PATH, 'auth-cookie.txt')
DATA_PATH = ensureDir(platformdirs.user_documents_path(), APP_NAME)
