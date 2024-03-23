def _startup():
    import locale
    import os
    import re
    import sys

    if not re.fullmatch('utf-?8', locale.getpreferredencoding(), re.IGNORECASE):
        print('This utility needs to be run with utf-8 default encoding enabled!', file=sys.stderr)
        print(f'To enable utf-8 mode please invoke via “python -X utf8 {__file__} ...”')
        exit(1)

    os.chdir(os.path.dirname(__file__))

_startup()
