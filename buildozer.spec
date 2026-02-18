[app]
title = EasyDokumentation
package.name = archaelogie
package.domain = org.example
source.include_exts = py,png,jpg,kv,txt
version = 0.1
requirements = python3,kivy==2.1.0,pyjnius,opencv
orientation = portrait
source.dir = .

android.permissions = CAMERA, BLUETOOTH,BLUETOOTH_ADMIN,ACCESS_FINE_LOCATION,BLUETOOTH_CONNECT,BLUETOOTH_SCAN, WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21

android.arch = arm64-v8a
android.ndk = 25b


[buildozer]
log_level = 2
warn_on_root = 1
