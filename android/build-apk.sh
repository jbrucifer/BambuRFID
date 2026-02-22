#!/bin/bash
echo "============================================"
echo " BambuNFC APK Builder"
echo "============================================"
echo ""

# Check for Java
if ! command -v java &> /dev/null; then
    echo "[ERROR] Java not found!"
    echo ""
    echo "Install JDK 17:"
    echo "  Ubuntu/Debian: sudo apt install openjdk-17-jdk"
    echo "  macOS:         brew install openjdk@17"
    echo "  Windows:       winget install EclipseAdoptium.Temurin.17.JDK"
    exit 1
fi

# Check for ANDROID_HOME
if [ -z "$ANDROID_HOME" ]; then
    if [ -d "$HOME/Android/Sdk" ]; then
        export ANDROID_HOME="$HOME/Android/Sdk"
    elif [ -d "$HOME/Library/Android/sdk" ]; then
        export ANDROID_HOME="$HOME/Library/Android/sdk"
    else
        echo "[ERROR] Android SDK not found!"
        echo ""
        echo "Install Android command-line tools:"
        echo "  1. Download from: https://developer.android.com/studio#command-line-tools-only"
        echo "  2. Extract and run: sdkmanager 'platforms;android-34' 'build-tools;34.0.0'"
        echo "  3. Set ANDROID_HOME to the SDK directory"
        exit 1
    fi
fi

echo "Using ANDROID_HOME: $ANDROID_HOME"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/BambuNFC"

# Write local.properties
echo "sdk.dir=$ANDROID_HOME" > local.properties

# Build
echo ""
echo "Building APK..."
chmod +x gradlew
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo " BUILD SUCCESSFUL!"
    echo "============================================"
    echo ""
    echo "APK location:"
    echo "  app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo "Install on phone:"
    echo "  adb install app/build/outputs/apk/debug/app-debug.apk"
else
    echo ""
    echo "[ERROR] Build failed!"
fi
