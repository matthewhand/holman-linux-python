'''
Discovery allowlists: exact advertised names and vendor service UUIDs.
'''

import os

DEFAULT_ALIASES = ('Tap Timer', 'BX2')

HOLMAN_CO3015_SERVICE_UUID = '0a75f000-f9ad-467a-e564-3c19163ad543'
HOLMAN_CO3012_SERVICE_UUID = 'aacaebbb-af4b-baf3-7361-989ffeb0b129'  # some BTX2
HOLMAN_CO3011_SERVICE_UUID = 'c521f000-0d70-4d4f-8e43-40d84c50ab38'  # BTX1 / BX2
DEFAULT_SERVICE_UUIDS = (
    HOLMAN_CO3015_SERVICE_UUID,
    HOLMAN_CO3012_SERVICE_UUID,
    HOLMAN_CO3011_SERVICE_UUID,
)


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


def get_default_service_uuids():
    '''
    Default Holman vendor services (CO3015, CO3012, CO3011).

    If ``HOLMAN_SERVICE_UUIDS`` is set, that comma-separated list fully
    replaces the defaults (not extras). Unset or blank = defaults.
    '''
    env = os.environ.get('HOLMAN_SERVICE_UUIDS')
    if env and env.strip():
        uuids = []
        for raw in env.split(','):
            raw = raw.strip().lower()
            if raw and raw not in uuids:
                uuids.append(raw)
        if uuids:
            return tuple(uuids)
    return DEFAULT_SERVICE_UUIDS
