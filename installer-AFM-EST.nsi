; AFM-EST Installer Script
; Using NSIS (Nullsoft Scriptable Install System)

; Define application information
!define APP_NAME "AFM-EST"
!define APP_VERSION "1.1.0"
!define APP_PUBLISHER "AFM-EST Team"
!define APP_WEBSITE ""
!define APP_EXE "AFM-EST.exe"
!define APP_ICON "resources\\icons\\wjssdb.ico"

; Define installation directory
!define INSTALL_DIR "$PROGRAMFILES64\\${APP_NAME}"

; Set installer properties
Name "${APP_NAME} ${APP_VERSION}"
OutFile "${APP_NAME}-setup-${APP_VERSION}.exe"
Icon "${APP_ICON}"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "Software\\${APP_NAME}" "InstallDir"

; Include MUI2
!include "MUI2.nsh"

; Configure MUI
!define MUI_ABORTWARNING
!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"

; Welcome page
!insertmacro MUI_PAGE_WELCOME

; Directory selection page
!insertmacro MUI_PAGE_DIRECTORY

; Installation progress page
!insertmacro MUI_PAGE_INSTFILES

; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\\${APP_EXE}"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\\README.md"
!insertmacro MUI_PAGE_FINISH

; Uninstall pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Language files
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

Section "MainSection" SEC01
  ; Create installation directory
  SetOutPath "$INSTDIR"
  
  ; Install main executable
  File "dist\\${APP_EXE}"
  
  ; Install README file
  File "README.md"
  
  ; Install config directory
  SetOutPath "$INSTDIR\\config"
  File /r "config\\*"
  
  ; Install transfer history database
  SetOutPath "$INSTDIR"
  File "transfer_history.db"
  
  ; Create start menu shortcuts
  CreateDirectory "$SMPROGRAMS\\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}" "" "$INSTDIR\\${APP_EXE}" 0
  CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\Uninstall ${APP_NAME}.lnk" "$INSTDIR\\uninstall.exe" "" "$INSTDIR\\uninstall.exe" 0
  
  ; Write registry information
  WriteRegStr HKLM "Software\\${APP_NAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\\${APP_NAME}" "Version" "${APP_VERSION}"
  
SectionEnd

Section "Uninstall"
  ; Delete start menu shortcuts
  Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\\${APP_NAME}\\Uninstall ${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\\${APP_NAME}"
  
  ; Delete files in installation directory
  Delete "$INSTDIR\\${APP_EXE}"
  Delete "$INSTDIR\\README.md"
  Delete "$INSTDIR\\transfer_history.db"
  Delete "$INSTDIR\\error_log.txt"
  
  ; Delete directories
  RMDir /r "$INSTDIR\\config"
  RMDir "$INSTDIR"
  
  ; Delete registry entries
  DeleteRegKey HKLM "Software\\${APP_NAME}"
  
SectionEnd

; Function: Uninstall initialization
Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to uninstall ${APP_NAME}?" IDYES gogogo
  Abort
  gogogo:
FunctionEnd
