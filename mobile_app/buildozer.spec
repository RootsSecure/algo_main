[app]

# Application Context
title = RootsSecure
package.name = sentinel
package.domain = org.rootssecure
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

# Application Versioning
version = 1.0.0

# 1. Kivy & Python Configuration
# Included all requested architectural libraries
requirements = python3,kivy,pyjnius,pillow,paho-mqtt,sqlite3,oscpy

# 2. Android Deployment Details
android.api = 33
android.minapi = 21

# 3. Permissions
# Explicit permissions needed to operate network and filesystem concurrently
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, CAMERA, WAKE_LOCK, RECEIVE_BOOT_COMPLETED

# 4. Background Service Configuration
# Android service implementation indicating where to look for continuous background listening
# This launches service.py immediately alongside main application execution
services = SentinelListener:service.py:(foreground)

# Extras
fullscreen = 0
android.allow_backup = True
# Compiling targeting the relevant mobile CPU archetypes
android.archs = arm64-v8a, armeabi-v7a

# UI Polish - Digital Panopticon Splash Screen
presplash.filename = %(source.dir)s/data/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
