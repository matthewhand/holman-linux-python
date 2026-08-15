'''
Advertised-name prefixes accepted during discovery.
'''

import os

DEFAULT_ALIAS_PREFIXES = ('Tap', 'BX')


def get_default_alias_prefixes():
    '''
    Tap (BX1) and BX (BX2) by default. Override for a future BX3.
    '''
    env = os.environ.get('HOLMAN_ACCEPTED_ALIAS_PREFIXES')
    if env:
        return tuple(p.strip() for p in env.split(',') if p.strip())
    return DEFAULT_ALIAS_PREFIXES
