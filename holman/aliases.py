'''
Exact advertised names accepted during discovery.
'''

import os

DEFAULT_ALIASES = ('Tap Timer', 'BX2')


def get_default_aliases():
    '''
    Exact ``Tap Timer`` (BX1) and ``BX2`` by default. Env adds more exact names.
    '''
    aliases = list(DEFAULT_ALIASES)
    env = os.environ.get('HOLMAN_ACCEPTED_ALIASES')
    if env:
        for name in env.split(','):
            name = name.strip()
            if name and name not in aliases:
                aliases.append(name)
    return tuple(aliases)


def alias_accepted(alias, accepted_aliases=None):
    '''
    True when ``alias`` is a non-empty exact member of the allowlist.
    '''
    if accepted_aliases is None:
        accepted_aliases = get_default_aliases()
    if not alias:
        return False
    return alias in accepted_aliases
