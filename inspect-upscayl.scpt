on run
    tell application "Upscayl" to activate
    delay 3
    
    tell application "System Events"
        set appName to name of the first process whose frontmost is true
        log "Frontmost app: " & appName
        
        tell process "Upscayl"
            set winCount to count of windows
            log "Number of windows: " & winCount
            
            if winCount > 0 then
                try
                    log "Window name: " & name of window 1
                    set btnCount to count of buttons of window 1
                    log "Button count: " & btnCount
                    
                    if btnCount > 0 then
                        repeat with i from 1 to btnCount
                            log "Button " & i & ": " & name of button i of window 1
                        end repeat
                    end if
                on error errMsg
                    log "Error getting elements: " & errMsg
                end try
            end if
        end tell
    end tell
end run