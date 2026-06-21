#Requires AutoHotkey v2.0
#SingleInstance Force

; ── Read config.json (same directory as this script = project root) ───────────
_cfg    := FileRead(A_ScriptDir "\config.json")
_port   := 8765
_hkName := "f6"
if RegExMatch(_cfg, '"server_port"\s*:\s*(\d+)', &_m)
    _port := Integer(_m[1])
if RegExMatch(_cfg, '"hotkey"\s*:\s*"([^"]+)"', &_m)
    _hkName := _m[1]

CAPTURE_URL := "http://127.0.0.1:" _port "/api/capture"
STATUS_URL  := "http://127.0.0.1:" _port "/api/status"
PID_FILE    := A_ScriptDir "\hotkey.pid"
LOG_FILE    := A_ScriptDir "\hotkey.log"
TOAST_MS    := 1200
MAX_LOG     := 200

; ── Tray ──────────────────────────────────────────────────────────────────────
TraySetIcon("imageres.dll", 97)
A_IconTip := "CrimsonHelper — " StrUpper(_hkName) " to capture"

A_TrayMenu.Delete()
A_TrayMenu.Add("Capture Now  (" StrUpper(_hkName) ")", MenuCapture)
A_TrayMenu.Add()
A_TrayMenu.Add("Open Dashboard", MenuDashboard)
A_TrayMenu.Add("View Log", MenuLog)
A_TrayMenu.Add()
A_TrayMenu.Add("Exit", (*) => ExitApp())
A_TrayMenu.Default := "Capture Now  (" StrUpper(_hkName) ")"

; ── PID file — lets start.sh kill us cleanly on Ctrl+C ───────────────────────
try FileDelete(PID_FILE)
FileAppend(String(A_PID) "`n", PID_FILE)
OnExit(OnExitCleanup)

OnExitCleanup(reason, code) {
    global PID_FILE
    try FileDelete(PID_FILE)
    Log("Exiting (" reason ")")
}

Log("Started — hotkey: " _hkName "  port: " _port "  pid: " A_PID)

; ── Dynamic hotkey from config.json ──────────────────────────────────────────
; ~ passes the key through to the active window so the game still receives it.
; Remove ~ if you want the key fully consumed by CrimsonHelper.
Hotkey("~" _hkName, TriggerCaptureHK)
TriggerCaptureHK(*) => TriggerCapture()

; ── Backend health-check — auto-exit when CrimsonHelper stops ─────────────────
_ready     := false
_failCount := 0
SetTimer(CheckBackend, 8000)   ; first check at 8 s — backend needs time to start

CheckBackend() {
    global STATUS_URL, _ready, _failCount
    try {
        req := ComObject("WinHttp.WinHttpRequest.5.1")
        req.Open("GET", STATUS_URL, false)
        req.SetTimeouts(2000, 2000, 2000, 2000)
        req.Send()
        _ready     := true
        _failCount := 0
        SetTimer(CheckBackend, 5000)
    } catch {
        if _ready {
            _failCount++
            if _failCount >= 2 {   ; two consecutive misses = CrimsonHelper stopped
                Log("Backend unreachable — exiting")
                ExitApp()
            }
        }
        SetTimer(CheckBackend, 8000)
    }
}

; ── Capture ───────────────────────────────────────────────────────────────────
TriggerCapture() {
    global CAPTURE_URL, TOAST_MS
    try {
        req := ComObject("WinHttp.WinHttpRequest.5.1")
        req.Open("POST", CAPTURE_URL, false)
        req.SetTimeouts(500, 500, 500, 500)
        req.Send()

        body := req.ResponseText
        if (req.Status = 200) {
            if InStr(body, '"game_not_running"')
                ShowToast("Game not detected", 2000)
            else if !InStr(body, '"debounced"')   ; silent on debounce
                ShowToast("Captured", TOAST_MS)
        } else {
            ShowToast("Capture failed — HTTP " req.Status, 2000)
            Log("Capture failed: HTTP " req.Status)
        }
    } catch as err {
        ShowToast("Backend unreachable", 2000)
        Log("Capture error: " err.Message)
    }
}

; ── Helpers ───────────────────────────────────────────────────────────────────
ShowToast(msg, duration := 1200) {
    ToolTip(msg)
    SetTimer(() => ToolTip(), -duration)
}

Log(msg) {
    global LOG_FILE, MAX_LOG
    FileAppend(FormatTime(, "yyyy-MM-dd HH:mm:ss") " | " msg "`n", LOG_FILE)
    try {
        lines := StrSplit(FileRead(LOG_FILE), "`n")
        if (lines.Length > MAX_LOG) {
            trimmed := ""
            for i, v in lines
                if (i > lines.Length - MAX_LOG)
                    trimmed .= v "`n"
            FileDelete(LOG_FILE)
            FileAppend(trimmed, LOG_FILE)
        }
    }
}

; ── Tray menu callbacks ───────────────────────────────────────────────────────
MenuCapture(*)   => TriggerCapture()
MenuDashboard(*) => Run("http://127.0.0.1:" _port)
MenuLog(*) {
    global LOG_FILE
    if FileExist(LOG_FILE)
        Run("notepad.exe " LOG_FILE)
    else
        MsgBox("No log entries yet.", "CrimsonHelper", 64)
}
