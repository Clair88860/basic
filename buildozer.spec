[app]
title = BLE_App
package.name = bleapp
package.domain = org.example
source.include_exts = py,png,jpg,kv,txt
version = 0.1
requirements = python3,kivy,pyjnius
orientation = portrait
source.dir = .

android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,ACCESS_FINE_LOCATION,BLUETOOTH_CONNECT,BLUETOOTH_SCAN
android.api = 33
android.minapi = 31
android.sdk = 33
android.arch = arm64-v8a
android.ndk = 25b
