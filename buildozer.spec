[app]

# Name der App
title = Basics
package.name = basics
package.domain = org.example

# Quellcode
source.dir = .
source.include_exts = py
version = 1.0
entrypoint = main.py
orientation = portrait

# Bibliotheken
requirements = python3,kivy,pyjnius,android,pillow,bleak,asyncio, kivymd, opencv-python, numpy, plyer, camera4kivy

# Berechtigungen
android.permissions = KAMERA,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_SCAN,BLUETOOTH_CONNECT,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# Anzeige
fullscreen = 0

# Android SDK / NDK
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25

# Architektur
android.archs = arm64-v8a

# Logging
android.logcat_filters = *:S python:D

# Warnung bei Root
warn_on_root = 1
