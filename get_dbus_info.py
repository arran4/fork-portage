import dbus
try:
    print(dbus.SystemBus())
except Exception as e:
    print("Error:", e)
