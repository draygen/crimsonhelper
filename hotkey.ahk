#Requires AutoHotkey v2.0
#SingleInstance Force

; ── Config ────────────────────────────────────────────────────────────────────
CAPTURE_URL  := "http://127.0.0.1:8765/api/capture"
STATUS_URL   := "http://127.0.0.1:8765/api/status"
LOG_FILE     := A_ScriptDir "\hotkey.log"
TOAST_MS     := 1200   ; capture feedback tooltip duration (ms)
MAX_LOG_LINES := 200

; ── Tray ──────────────────────────────────────────────────────────────────────
TraySetIcon("imageres.dll", 97)   ; camera-ish icon from Windows shell
A_IconTip := "CrimsonHelper — F6 to capture"

A_TrayMenu.Delete()
A_TrayMenu.Add("Capture Now  (F6)", MenuCapture)
A_TrayMenu.Add()
A_TrayMenu.Add("Open Dashboard", MenuDashboard)
A_TrayMenu.Add("View Log", MenuLog)
A_TrayMenu.Add()
A_TrayMenu.Add("Exit", (*) => ExitApp())
A_TrayMenu.Default := "Capture Now  (F6)"

Log("CrimsonHelper hotkey started — backend: " CAPTURE_URL)

; ── Hotkey ────────────────────────────────────────────────────────────────────
; ~F6 passes the key through to the active window (game still gets F6).
; Change to F6:: to consume it entirely.
~F6:: TriggerCapture()

; ── Functions ─────────────────────────────────────────────────────────────────
TriggerCapture() {
    global CAPTURE_URL, TOAST_MS
    try {
        req := ComObject("WinHttp.WinHttpRequest.5.1")
        req.Open("POST", CAPTURE_URL, false)   ; sync — fast enough (<50 ms local)
        req.SetTimeouts(500, 500, 500, 500)    ; connect / send / receive timeouts
        req.Send()

        status := req.Status
        if (status = 200) {
            body := req.ResponseText
            if InStr(body, '"game_not_running"') {
                ShowToast("⚠ Game not detected — check process guard in config.json", 2000)
                Log("Capture skipped: game_not_running")
            } else if InStr(body, '"debounced"') {
                ; silent — too fast, no feedback needed
            } else {
                ShowToast("📸 Captured", TOAST_MS)
                Log("Capture OK (HTTP 200)")
            }
        } else {
            ShowToast("✗ Capture failed — HTTP " status, 2000)
            Log("Capture failed: HTTP " status " | " req.ResponseText)
        }
    } catch as err {
        ShowToast("✗ Backend unreachable", 2000)
        Log("Capture error: " err.Message)
    }
}

ShowToast(msg, duration := 1200) {
    ToolTip(msg)
    SetTimer(() => ToolTip(), -duration)
}

Log(msg) {
    global LOG_FILE, MAX_LOG_LINES
    line := FormatTime(, "yyyy-MM-dd HH:mm:ss") " | " msg
    FileAppend(line "`n", LOG_FILE)
    ; Trim log if it gets too long
    try {
        lines := StrSplit(FileRead(LOG_FILE), "`n")
        if (lines.Length > MAX_LOG_LINES)
            FileDelete(LOG_FILE), FileAppend(ArrayJoin(lines.Slice(-MAX_LOG_LINES), "`n") "`n", LOG_FILE)
    }
}

ArrayJoin(arr, sep) {
    out := ""
    for v in arr
        out .= (out ? sep : "") v
    return out
}

; ── Tray menu actions ─────────────────────────────────────────────────────────
MenuCapture(*)  => TriggerCapture()
MenuDashboard(*) => Run("http://127.0.0.1:8765")
MenuLog(*) {
    global LOG_FILE
    if FileExist(LOG_FILE)
        Run("notepad.exe " LOG_FILE)
    else
        MsgBox("No log entries yet.", "CrimsonHelper", 64)
}
