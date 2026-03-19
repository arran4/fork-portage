import portage
import portage.util
import logging

try:
    import dbus
except ImportError:
    dbus = None

_system_bus = None
_dbus_initialized = False

def _init_dbus():
    global _system_bus, _dbus_initialized
    if _dbus_initialized:
        return _system_bus

    _dbus_initialized = True
    if dbus is not None:
        try:
            _system_bus = dbus.SystemBus()
        except dbus.exceptions.DBusException:
            _system_bus = None
    return _system_bus

def send_dbus_signal(signal_name, signature, *args):
    # Depending on how the module is imported, portage.settings might not be populated immediately.
    # Therefore, we fetch it gracefully.
    try:
        settings = portage.settings
        if "dbus" not in settings.features:
            return
    except AttributeError:
        # Fallback if portage.settings is missing
        return

    bus = _init_dbus()
    if bus is None:
        return

    try:
        # We broadcast the signal on a specific object path and interface
        # without requiring a service to be registered (bus name).
        # Any listener can catch this signal.
        msg = dbus.lowlevel.SignalMessage('/', 'org.gentoo.portage', signal_name)
        msg.append(*args, signature=signature)
        bus.send_message(msg)
    except Exception as e:
        portage.util.writemsg_level("!!! DBus Exception: %s\n" % (e,), level=logging.WARNING, noiselevel=-1)
