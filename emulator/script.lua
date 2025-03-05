---@diagnostic disable: lowercase-global

-- Socket setup for communication with Python controller
statusSocket     = nil
lastScreenshotTime = 0
screenshotInterval = 3  -- Capture screenshots every 3 seconds

-- Debug buffer setup
function setupBuffer()
    debugBuffer = console:createBuffer("Debug")
    debugBuffer:setSize(100, 64)
    debugBuffer:clear()
    debugBuffer:print("Debug buffer initialized\n")
end

-- Screenshot capture function
function captureAndSendScreenshot()
    local currentTime = os.time()
    
    -- Only capture screenshots every 3 seconds
    if currentTime - lastScreenshotTime >= screenshotInterval then
        local screenshotPath = "/Users/alex/Documents/gemini-plays-pokemon/data/screenshots/screenshot.png"
        emu:screenshot(screenshotPath) -- Take the screenshot
        sendMessage("screenshot", screenshotPath) -- Send path to Python controller
        debugBuffer:print("Screenshot captured and sent: " .. screenshotPath .. "\n")
        
        -- Update the last screenshot time
        lastScreenshotTime = currentTime
    end
end

-- Function to receive and handle control input from AI
function receiveControlInput()
    if statusSocket then
        local input, err = statusSocket:receive(1024)
        if input then
            local keyIndex = tonumber(input)
            if keyIndex and keyIndex >= 0 and keyIndex <= 9 then
                -- Map key indices to key names for logging
                local keyNames = { "A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L" }
                
                -- Clear all keys and apply the new key press
                emu:clearKeys(0x3FF) -- Clear all keys
                emu:addKey(keyIndex) -- Press the received key
                debugBuffer:print("AI pressed: " .. keyNames[keyIndex + 1] .. "\n")
            else
                debugBuffer:print("Invalid input received: " .. tostring(input) .. "\n")
            end
        elseif err ~= socket.ERRORS.AGAIN then
            debugBuffer:print("Socket receive error: " .. err .. "\n")
        end
    end
end

-- Socket management functions
function sendMessage(messageType, content)
    if statusSocket then
        statusSocket:send(messageType .. "||" .. content .. "\n")
    end
end

function socketReceived()
    while true do
        local p, err = statusSocket:receive(1024)
        if p then
            debugBuffer:print("Received from controller: " .. p:match("^(.-)%s*$") .. "\n")
        else
            if err ~= socket.ERRORS.AGAIN then
                debugBuffer:print("Socket error: " .. err .. "\n")
                stopSocket()
            end
            return
        end
    end
end

function socketError(err)
    debugBuffer:print("Socket error: " .. err .. "\n")
    stopSocket()
end

function stopSocket()
    if not statusSocket then return end
    debugBuffer:print("Closing socket connection\n")
    statusSocket:close()
    statusSocket = nil
end

function startSocket()
    debugBuffer:print("Connecting to controller at 127.0.0.1:8888...\n")
    statusSocket = socket.tcp()
    statusSocket:add("received", socketReceived)
    statusSocket:add("error", socketError)
    if statusSocket:connect("127.0.0.1", 8888) then
        debugBuffer:print("Successfully connected to controller\n")
    else
        debugBuffer:print("Failed to connect to controller\n")
        stopSocket()
    end
end

-- Add callbacks to run our functions
callbacks:add("start", setupBuffer)
callbacks:add("start", startSocket)
callbacks:add("frame", captureAndSendScreenshot)
callbacks:add("frame", receiveControlInput)

-- Initialize on script load
if emu then
    setupBuffer()
    startSocket()
end