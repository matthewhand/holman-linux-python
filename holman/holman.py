"""
Module for managing Holman Bluetooth tap timers.
"""
import os

import gatt


_DEFAULT_ALIASES = ('Tap Timer', 'BX2')


def _get_default_aliases():
    """
    Tap Timer / BX2 allowlist, plus HOLMAN_ACCEPTED_ALIASES extras.

    If another Holman or compatible timer appears with a different
    advertised name, it can be added via env without a code change.
    """
    aliases = list(_DEFAULT_ALIASES)
    env = os.environ.get('HOLMAN_ACCEPTED_ALIASES')
    if env:
        for name in env.split(','):
            name = name.strip()
            if name and name not in aliases:
                aliases.append(name)
    return tuple(aliases)


def _get_default_service_uuids():
    '''
    CO3015 / CO3012 / CO3011 unless HOLMAN_SERVICE_UUIDS is set.

    When the env var is set, the comma-separated value fully replaces
    the hardcoded defaults (not extras). Unset or blank = defaults.

    If another Holman or compatible timer appears with a different
    vendor service UUID, it can be matched via env without a code change.
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
    return tuple(TapTimer.SERVICE_UUIDS)



class TapTimerManager(gatt.DeviceManager):
    """
    Entry point for managing and discovering Holman ``TapTimer``s.
    """

    def __init__(self, adapter_name='hci0', accepted_aliases=None,
                 service_uuids=None):
        """
        Instantiates a ``TapTimerManager``

        :param adapter_name: name of Bluetooth adapter used by this
                             tap timer manager
        :param accepted_aliases: exact advertised names to accept during
                                 discovery. Defaults to ``('Tap Timer', 'BX2')``
                                 plus extra names from ``HOLMAN_ACCEPTED_ALIASES``
                                 (comma-separated exact strings).
        :param service_uuids: vendor service UUIDs for discovery and
                              connect-time service pick. Defaults to
                              CO3015 / CO3012 / CO3011. When
                              ``HOLMAN_SERVICE_UUIDS`` is set, that
                              comma-separated list fully replaces the
                              defaults. Constructor wins over env.
        """
        # DeviceManager.__init__ calls update_devices() -> make_device(),
        # which reads accepted_aliases and service_uuids.
        if accepted_aliases is None:
            accepted_aliases = _get_default_aliases()
        self.accepted_aliases = tuple(accepted_aliases)
        if service_uuids is None:
            service_uuids = _get_default_service_uuids()
        self.service_uuids = tuple(u.lower() for u in service_uuids)
        self.listener = None
        self.discovered_tap_timers = {}
        super().__init__(adapter_name)

    def tap_timers(self):
        """
        Returns all known Holman tap timers.
        """
        return self.devices()

    def start_discovery(self, service_uuids=None):
        """
        Starts a Bluetooth discovery for Holman tap timers.

        Assign a `TapTimerManagerListener` to the `listener` attribute
        to collect discovered Holmans.
        """
        super().start_discovery(service_uuids=list(self.service_uuids))

    def make_device(self, mac_address):
        device = gatt.Device(
            mac_address=mac_address, manager=self, managed=False)
        alias = device.alias() or ''
        if alias not in self.accepted_aliases:
            return None
        return TapTimer(mac_address=mac_address, manager=self)

    def device_discovered(self, device):
        super().device_discovered(device)
        if device.mac_address in self.discovered_tap_timers:
            return
        self.discovered_tap_timers[device.mac_address] = device
        if self.listener is not None:
            self.listener.tap_timer_discovered(device)


class TapTimerManagerListener(object):
    """
    Base class for receiving discovery events from ``TapTimerManager``.

    Assign an instance of your subclass to the ``listener`` attribute
    of your ``TapTimerManager`` to receive discovery events.
    """

    def tap_timer_discovered(self, tap_timer):
        """
        This method gets called once for each Holman tap timer
        discovered nearby.

        :param tap_timer: the Holman tap timer that was discovered
        """
        pass


class TapTimer(gatt.Device):
    """
    This class represents a Holman tap timer.

    Obtain instances of this class by using the discovery mechanism of
    ``TapTimerManager`` or by manually creating an instance.

    Assign an instance of ``TapTimerListener`` to the ``listener``
    attribute to receive all Holman related events such as connection,
    disconnection and user input.

    :param adapter_name: name of Bluetooth adapter that can connect to
    this tap timer
    :param mac_address: MAC address of this Holman tap timer
    :param listener: instance of ``TapTimerListener`` that will be
    notified with all events
    """
    HOLMAN_CO3015_SERVICE_UUID = '0a75f000-f9ad-467a-e564-3c19163ad543'
    HOLMAN_CO3012_SERVICE_UUID = 'aacaebbb-af4b-baf3-7361-989ffeb0b129'
    HOLMAN_CO3011_SERVICE_UUID = 'c521f000-0d70-4d4f-8e43-40d84c50ab38'  # BTX1 / BX2
    STATE_CHARACTERISTIC_UUID = '0000f004-0000-1000-8000-00805f9b34fb'
    MANUAL_CHARACTERISTIC_UUID = '0000f006-0000-1000-8000-00805f9b34fb'
    AUTH_CHARACTERISTIC_UUID = '0000c001-0000-1000-8000-00805f9b34fb'
    AUTH_PAYLOAD = bytes((0xAE, 0x8E))

    SERVICE_UUIDS = [
        HOLMAN_CO3015_SERVICE_UUID,
        HOLMAN_CO3012_SERVICE_UUID,
        HOLMAN_CO3011_SERVICE_UUID]

    def __init__(self, mac_address, manager, service_uuids=None):
        """
        Create an instance with given Bluetooth adapter name and MAC
        address.

        :param mac_address: MAC address of Holman tap timer with
        format: ``AA:BB:CC:DD:EE:FF``
        :param manager: reference to the `TapTimerManager` that manages
        this tap timer
        :param service_uuids: vendor service UUIDs for connect-time
                              service pick. Defaults to the manager
                              list, else the same resolved defaults /
                              ``HOLMAN_SERVICE_UUIDS`` replace list.
        """
        super().__init__(mac_address=mac_address, manager=manager)

        if service_uuids is None:
            service_uuids = getattr(manager, 'service_uuids', None)
        if service_uuids is None:
            service_uuids = _get_default_service_uuids()
        self.service_uuids = tuple(u.lower() for u in service_uuids)

        self.listener = None
        self._battery_level = None
        self._manual_characteristic = None
        self._state_characteristic = None
        self._auth_characteristic = None
        # DBus completes writes asynchronously; hold f006 until c001 callback.
        self._pending_manual_payload = None
        self._state = bytes([0])

    def connect(self):
        """
        Tries to connect to this Holman tap timer and blocks until it
        has connected or failed to connect.

        Notifies ``listener`` as soon has the connection has succeeded
        or failed.
        """
        if self.listener:
            self.listener.started_connecting()
        super().connect()

    def connect_failed(self, error):
        self._pending_manual_payload = None
        super().connect_failed(error)
        if self.listener:
            self.listener.connect_failed(error)

    def disconnect(self):
        """
        Disconnects this Holman tap timer if connected.

        Notifies ``listener`` as soon as Holman was disconnected.
        """
        if self.listener:
            self.listener.started_disconnecting()
        self._refresh_state()
        super().disconnect()

    def disconnect_succeeded(self):
        self._pending_manual_payload = None
        super().disconnect_succeeded()
        if self.listener:
            self.listener.disconnect_succeeded()

    def services_resolved(self):
        super().services_resolved()
        # Resolution can be called again after reconnect. Never retain a
        # writable characteristic (or queued command) from the old session.
        self._pending_manual_payload = None
        self._manual_characteristic = None
        self._state_characteristic = None
        self._auth_characteristic = None

        accepted = {uuid.lower() for uuid in self.service_uuids}
        holman_service = next((
            service for service in self.services
            if service.uuid.lower() in accepted), None)
        if holman_service is None:
            if self.listener:
                # TODO: Use proper exception subclass
                self.listener.connect_failed(
                    Exception("Holman GATT service missing"))
            return

        manual_characteristic = next((
            char for char in holman_service.characteristics
            if char.uuid == self.MANUAL_CHARACTERISTIC_UUID), None)
        if manual_characteristic is None:
            # TODO: Use proper exception subclass
            self.listener.connect_failed(
                Exception(
                    "Holman GATT characteristic %s missing",
                    self.MANUAL_CHARACTERISTIC_UUID))
            return

        state_characteristic = next((
            char for char in holman_service.characteristics
            if char.uuid == self.STATE_CHARACTERISTIC_UUID), None)
        if state_characteristic is None:
            # TODO: Use proper exception subclass
            self.listener.connect_failed(
                Exception(
                    "Holman GATT characteristic %s missing",
                    self.STATE_CHARACTERISTIC_UUID))
            return
        self._auth_characteristic = next((
            char for char in holman_service.characteristics
            if char.uuid == self.AUTH_CHARACTERISTIC_UUID), None)
        # Publish the required characteristics only after both were found.
        self._manual_characteristic = manual_characteristic
        self._state_characteristic = state_characteristic
        self._refresh_state()

        # TODO: Only fire connected event when we read the firmware
        # version or battery value as in other SDKs
        if self.listener:
            self.listener.connect_succeeded()

    def battery_level(self):
        # TODO: determine which byte in state is used for battery level
        return self._battery_level

    def _refresh_state(self):
        if self._state_characteristic:
            self._state = self._state_characteristic.read_value()

    @property
    def is_on(self):
        """Return true if tap is running."""
        self._refresh_state()
        return self._state[-1] == 1

    @property
    def name(self):
        """The name of the tap timer."""
        return str(self.alias())

    def _write_manual(self, value):
        """Write f006 only after the optional asynchronous c001 unlock.

        An urgent stop can supersede a start waiting for the unlock callback.
        Devices without c001 retain the original direct f006 behaviour.
        """
        if self._manual_characteristic is None:
            return
        if self._pending_manual_payload is not None:
            if value == bytes(4):
                self._pending_manual_payload = value
                return
            raise RuntimeError("previous Holman unlock is still pending")
        if self._auth_characteristic is None:
            self._manual_characteristic.write_value(value)
            return
        self._pending_manual_payload = value
        try:
            self._auth_characteristic.write_value(self.AUTH_PAYLOAD)
        except Exception as error:
            self._pending_manual_payload = None
            if value == bytes(4):
                # Attempt all-off even if unlock failed; report if it fails.
                try:
                    self._manual_characteristic.write_value(value)
                except Exception as stop_error:
                    if self.listener:
                        self.listener.timer_write_failed(stop_error)
                    else:
                        raise
            elif self.listener:
                self.listener.timer_write_failed(error)
            else:
                raise

    def start(self, runtime=1, zone=1):
        """Start the requested outlet for 1-255 minutes (zone 1 by default)."""
        if zone not in (1, 2) or isinstance(zone, bool):
            raise ValueError("BX2 zone must be 1 (Sprinkler) or 2 (Hose)")
        runtime = min(255, max(1, int(runtime)))
        value = bytes([1, zone - 1, 0, runtime])
        self._write_manual(value)

    def stop(self):
        """Send the same all-zero stop command on every supported model."""
        self._write_manual(bytes(4))

    def characteristic_write_value_succeeded(self, characteristic):
        if characteristic == self._auth_characteristic:
            if self._pending_manual_payload is not None:
                value = self._pending_manual_payload
                self._pending_manual_payload = None
                try:
                    self._manual_characteristic.write_value(value)
                except Exception as error:
                    if self.listener:
                        self.listener.timer_write_failed(error)
                    else:
                        raise
            return
        self._refresh_state()
        if characteristic == self._manual_characteristic and self.listener:
            self.listener.timer_written()

    def characteristic_write_value_failed(self, characteristic, error):
        if characteristic == self._auth_characteristic:
            if self._pending_manual_payload is not None:
                value = self._pending_manual_payload
                self._pending_manual_payload = None
                if value == bytes(4):
                    # Still attempt emergency all-off after rejected unlock.
                    try:
                        self._manual_characteristic.write_value(value)
                    except Exception as write_error:
                        if self.listener:
                            self.listener.timer_write_failed(write_error)
                        else:
                            raise
                elif self.listener:
                    self.listener.timer_write_failed(error)
            return
        self._refresh_state()
        if characteristic == self._manual_characteristic and self.listener:
            self.listener.timer_write_failed(error)


class TapTimerListener:
    """
    Base class of listeners for a ``TapTimer`` with empty handler
    implementations.
    """
    def started_connecting(self):
        pass

    def connect_succeeded(self):
        pass

    def connect_failed(self, error):
        pass

    def started_disconnecting(self):
        pass

    def disconnect_succeeded(self):
        pass

    def timer_written(self):
        """Called once an f006 manual start/stop write completes."""
        pass

    def timer_write_failed(self, error):
        """Called if a queued c001/f006 manual write fails."""
        pass
