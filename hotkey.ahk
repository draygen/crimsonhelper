; CrimsonHelper — Windows-side capture hotkey
; Requires AutoHotkey v2  (https://www.autohotkey.com)
;
; Run this script on Windows BEFORE launching the game.
; It intercepts F6 globally and fires a capture even while CrimsonDesert
; has focus, then passes F6 through so the game still receives it.
;
; Change CAPTURE_URL if you edited server_port in config.json.

CAPTURE_URL := "http://127.0.0.1:8765/api/capture"

; ~F6  = pass the key through to the active window as well
; Remove the ~ if you want F6 consumed entirely by CrimsonHelper
~F6:: {
    try {
        req := ComObject("WinHttp.WinHttpRequest.5.1")
        req.Open("POST", CAPTURE_URL, true)   ; true = async, won't freeze
        req.Send()
    }
    ; Errors are silently ignored so the game is never interrupted
}
