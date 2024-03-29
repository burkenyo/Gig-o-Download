from pathlib import Path
import platformdirs

def ensure_dir(base: Path, dir_name: str):
    dir = Path(base, dir_name)
    dir.mkdir(exist_ok=True)
    return dir

_APP_NAME = 'Gig-o-Download'
CACHE_PATH = platformdirs.user_cache_path(_APP_NAME, ensure_exists=True)
DATA_PATH = ensure_dir(platformdirs.user_documents_path(), _APP_NAME)
