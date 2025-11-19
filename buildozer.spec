[app]
# (str) Title of your application
title = Montreal Travel Companion
# (str) Package name
package.name = montrealtravel
# (str) Package domain
package.domain = com.travelcompanion
# (str) Source code directory (DO NOT change unless main.py is inside /app)
source.dir = .
# (list) Extensions to include
source.include_exts = py,png,jpg,kv,atlas
# (str) App version
version = 1.0
# (list) Python modules to include
requirements = python3,kivy==2.3.0,requests,plyer
# (str) App orientation
orientation = portrait
# (bool) Fullscreen or not
fullscreen = 0
# (list) Android Permissions
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION
# --- Android Build Settings ---
# (int) Target Android API
android.api = 33
# (int) Minimum supported Android API
android.minapi = 21
# ⚠️ MUST USE NDK 23b OR CI WILL FAIL
android.ndk = 23b
# (bool) Use --private internal storage
android.private_storage = True
# (str) Logcat filters
android.logcat_filters = *:S python:D
# (list) Architectures to build for
android.archs = arm64-v8a,armeabi-v7a
# ------------------------------------------------
[buildozer]
log_level = 2
warn_on_root = 0
# CRITICAL: Set to 0 to disable root check entirely
android.accept_sdk_license = True
