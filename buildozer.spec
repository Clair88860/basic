[app]
title = ArduinoBLE
package.name = arduinoble
package.domain = org.example
source.dir = .
version = 0.1
entrypoint = arduino_ble.py
requirements = python3,kivy,bleak
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,ACCESS_FINE_LOCATION
orientation = portrait
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

[buildozer]
log_level = 2
