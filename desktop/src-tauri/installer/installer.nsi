; NSIS installer hooks for NHL Scoreboard Studio.
; Kills any running instances of the app before copying files,
; preventing "Error opening file for writing" during upgrades.

!macro NSIS_HOOK_PREINSTALL
  DetailPrint "Closing any running instances..."
  ; Kill the Tauri main exe and the Python sidecar.
  ; /F = force, /T = also tree (children), >NUL 2>&1 to suppress noise.
  nsExec::Exec 'taskkill /F /IM "NHL Scoreboard Studio.exe" /T'
  nsExec::Exec 'taskkill /F /IM "nhlsb-server.exe" /T'
  Sleep 500
!macroend
