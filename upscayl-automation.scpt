on run
    tell application "Upscayl" to activate
    delay 3
    
    tell application "System Events"
        tell process "Upscayl"
            -- Move cursor away first (to a visible location)
            set mouse location to {400, 400}
            delay 1
            
            -- Slowly move to and click at the "Select Image" button position
            set mouse location to {80, 295}
            delay 2  -- Wait so you can see where the cursor is
            click at {80, 295}
            delay 3
            
            -- Move to and click "Set Output Folder" button
            set mouse location to {95, 678}
            delay 2
            click at {95, 678}
            delay 3
            
            -- Move to and click "Upscayl" button
            set mouse location to {70, 785}
            delay 2
            click at {70, 785}
        end tell
    end tell
end run