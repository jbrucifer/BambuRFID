@echo off
echo ============================================
echo  BambuNFC APK Builder
echo ============================================
echo.

:: Check for Java
java -version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Java not found!
    echo.
    echo Install JDK 17:
    echo   winget install EclipseAdoptium.Temurin.17.JDK
    echo.
    echo Or download from: https://adoptium.net/temurin/releases/
    echo After installing, restart this terminal and try again.
    exit /b 1
)

:: Check for ANDROID_HOME
if not defined ANDROID_HOME (
    if exist "%LOCALAPPDATA%\Android\Sdk" (
        set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
    ) else (
        echo [ERROR] Android SDK not found!
        echo.
        echo Install Android command-line tools:
        echo   1. Download from: https://developer.android.com/studio#command-line-tools-only
        echo   2. Extract to: %LOCALAPPDATA%\Android\Sdk
        echo   3. Run: sdkmanager "platforms;android-34" "build-tools;34.0.0"
        echo   4. Set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
        echo.
        echo Or install Android Studio which includes everything.
        exit /b 1
    )
)

echo Using ANDROID_HOME: %ANDROID_HOME%

:: Write local.properties
echo sdk.dir=%ANDROID_HOME:\=\\% > BambuNFC\local.properties

:: Build the APK
echo.
echo Building APK...
cd BambuNFC
call gradlew.bat assembleDebug

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================
    echo  BUILD SUCCESSFUL!
    echo ============================================
    echo.
    echo APK location:
    echo   app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo To install on your phone:
    echo   1. Copy the APK to your phone
    echo   2. Enable "Install from unknown sources" in Settings
    echo   3. Tap the APK to install
    echo.
    echo Or install via ADB:
    echo   adb install app\build\outputs\apk\debug\app-debug.apk
) else (
    echo.
    echo [ERROR] Build failed! Check the output above for errors.
)
