-- MapleHits: MapleStory-style damage numbers for WoW Forever, matched to MapleStory Classic footage. Digits are
-- textures drawn from the Bowlby One font (SIL Open Font License, OFL-BowlbyOne.txt) by make_maplehits_art.py:
-- gradient fill, thick white rim, thin dark outline; no game art. Hits run red-orange to yellow, crits crimson to
-- pink with a white-yellow burst, hits on you violet to magenta; MISS takes your colors when you miss and violet when
-- the mob misses you. The first digit is bigger with the bottoms lined up, the others bob and overlap, each over the
-- one before; hits landing together stack tight, the newest on top. Numbers rise slowly and fade.
-- Hits come from UNIT_COMBAT (Forever closes the combat log); a secret amount can't be split in digits, so it goes
-- whole to a font string. /mh on/off  ·  /mh teste  ·  /mh escala 1.2  ·  /mh altura 60  ·  /mh blizz  ·  /mh debug
local _, ns = ...
local ART = "Interface\\AddOns\\MapleHits\\art\\"
local FONT = "Interface\\AddOns\\MapleHits\\BowlbyOne-Regular.ttf"
local INK = ns.INK                                 -- the digit's height in its cell (Art.lua)
local DIGIT, FIRST, GAP, BOB = 60, 1.3, 0.74, 2    -- cell size, first digit scale, spacing (overlap), up/down bob
local LINE = DIGIT * INK * 0.67                    -- stack step: lines overlap by a third
local LIFE, HOLD, RISE = 1.1, 0.55, 36             -- seconds shown, seconds before fading, pixels risen in all
local STACK = 0.6                                  -- hits this close together stack up
-- kind: texture (art/<name>.tga); top, mid, bottom fill colors for a secret amount (same as the textures)
local function rgb(r, g, b) return {r / 255, g / 255, b / 255} end
local KIND = { -- the stream's hues at full strength, with a deeper top and a brighter bottom for punch
    hit = {"hit", rgb(236, 20, 0), rgb(255, 128, 0), rgb(255, 240, 0)},
    crit = {"crit", rgb(226, 0, 40), rgb(255, 28, 128), rgb(255, 150, 236)},
    taken = {"taken", rgb(76, 16, 236), rgb(178, 36, 255), rgb(255, 84, 236)},
    heal = {"heal", rgb(0, 70, 230), rgb(30, 170, 255), rgb(176, 246, 255)},
    miss = {"miss_hit"},     -- you missed
    missTaken = {"miss_taken"}, -- the mob missed you
}
-- a secret amount (Forever hides combat numbers) can't be split into digits or measured, so it is drawn whole, in
-- layers: dark copies all around (the outline), white copies a bit closer (the rim), the fill on top in three
-- clipped color bands. No copy has its own outline, so no dark lines cross the white rim.
local TS = 46                                       -- its font size: digits as tall as the textures'
local BASE, TALL = 0.29, 0.67                       -- the digits sit this far up the string and are this tall (em),
                                                    -- measured on screen in Forever
local AROUND = {}                                   -- twelve directions, so the rim stays round
for i = 0, 11 do AROUND[#AROUND + 1] = {math.cos(i * math.pi / 6), math.sin(i * math.pi / 6)} end
local OUTLINE, RIM = 5, 3.6                         -- distance of the dark copies (each with a solid black edge of
                                                    -- its own, so the outline comes out black, not gray) and of
                                                    -- the white ones, pixels
local DIGITS = "Interface\\AddOns\\MapleHits\\MapleHitsDigits.ttf" -- make_maplehits_font.py: digits leaning like
                                                    -- MISS, packed tight, each a little up or down
local STEPS = 10                                    -- color bands of the fill, bottom to top: a smooth gradient
local function grad(k, t) -- the fill color at t (0 top, 1 bottom) between the kind's top, mid and bottom colors
    local a, b, u = k[2], k[3], t / 0.5
    if t > 0.5 then a, b, u = k[3], k[4], (t - 0.5) / 0.5 end
    return a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u, a[3] + (b[3] - a[3]) * u
end
-- the game's own combat text: damage over mobs, DoTs, pets, heals, and the text on you (enableFloatingCombatText)
local CVARS = {"enableFloatingCombatText", "floatingCombatTextCombatDamage", "floatingCombatTextCombatDamage_v2",
    "floatingCombatTextCombatLogPeriodicSpells", "floatingCombatTextCombatLogPeriodicSpells_v2",
    "floatingCombatTextPetMeleeDamage", "floatingCombatTextPetMeleeDamage_v2", "floatingCombatTextPetSpellDamage",
    "floatingCombatTextPetSpellDamage_v2", "floatingCombatTextCombatHealing", "floatingCombatTextCombatHealing_v2"}

local DB
local pool, live, stacks = {}, {}, {}
local function secret(v) return issecretvalue and issecretvalue(v) end

local function newNumber()
    local n = CreateFrame("Frame", nil, UIParent)
    n:SetSize(1, 1)
    n:SetFrameStrata("HIGH")
    n.digits = {}
    n.burst = n:CreateTexture(nil, "BACKGROUND") -- behind a crit's first digit
    n.burst:SetTexture(ART .. "burst")
    n.burst:SetSize(DIGIT * 1.7, DIGIT * 1.28)
    n.word = n:CreateTexture(nil, "ARTWORK") -- MISS
    n.word:SetSize(DIGIT * 4, DIGIT)
    n.word:SetPoint("CENTER", n, "CENTER", 0, DIGIT * INK / 2)
    local function text(parent, layer, flags, x, y)
        local fs = parent:CreateFontString(nil, layer)
        fs:SetFont(FONT, TS, flags)
        fs:SetFont(DIGITS, TS, flags) -- keeps Bowlby One if the digit font is missing
        fs:SetPoint("BOTTOM", n, "CENTER", x, y)
        return fs
    end
    n.secret = {}
    for _, layer in ipairs({{"BACKGROUND", OUTLINE, 0, 0, 0, "THICKOUTLINE"}, {"BORDER", RIM, 1, 1, 1, ""}}) do
        for _, o in ipairs(AROUND) do
            local fs = text(n, layer[1], layer[6], o[1] * layer[2], o[2] * layer[2])
            fs:SetTextColor(layer[3], layer[4], layer[5])
            n.secret[#n.secret + 1] = fs
        end
    end
    n.fill = text(n, "ARTWORK", "", 0, 0)
    n.secret[#n.secret + 1] = n.fill
    n.bands = {}
    for i = 1, STEPS - 1 do
        local c = CreateFrame("Frame", nil, n)
        c:SetClipsChildren(true)
        c:SetPoint("BOTTOMLEFT", n, "CENTER", -300, TS * (BASE + TALL * i / STEPS))
        c:SetPoint("TOPRIGHT", n, "CENTER", 300, TS * 2)
        c.fs = text(c, "OVERLAY", "", 0, 0)
        n.bands[i] = c
        n.secret[#n.secret + 1] = c.fs
    end
    return n
end

-- lay text out on n with the bottoms on n's center: digit textures, the MISS word, or a secret amount as text
local function layout(n, text, kind)
    local k = KIND[kind]
    for _, t in ipairs(n.digits) do t:Hide() end
    n.word:Hide()
    local hidden = not secret(text)
    for _, fs in ipairs(n.secret) do
        fs:SetText(hidden and "" or text) -- a secret only goes to SetText
        fs:SetShown(not hidden)
    end
    local total, first = DIGIT * 2, DIGIT * 0.6
    if not hidden then
        n.fill:SetTextColor(grad(k, 1 - 0.5 / STEPS))
        for i, band in ipairs(n.bands) do band.fs:SetTextColor(grad(k, 1 - (i + 0.5) / STEPS)) end
        total = DIGIT * 2.4 -- unknown: room for about three digits, for the crit burst
    elseif text == "MISS" then
        n.word:SetTexture(ART .. k[1])
        n.word:Show()
    else
        local ds, sizes, adv = {}, {}, {}
        for ch in tostring(text):gmatch("%d") do ds[#ds + 1] = tonumber(ch) end
        total = 0
        for i, d in ipairs(ds) do
            sizes[i] = DIGIT * ((i == 1 and #ds > 1) and FIRST or 1)
            adv[i] = ns.WIDTH[d + 1] * sizes[i] -- the ink width, not the whole cell
            total = total + adv[i] * (i < #ds and GAP or 1)
        end
        local x = -total / 2
        for i, d in ipairs(ds) do
            local t = n.digits[i] or n:CreateTexture(nil, "ARTWORK")
            n.digits[i] = t
            t:SetDrawLayer("ARTWORK", math.min(i - 1, 7)) -- each digit over the one before
            t:SetTexture(ART .. k[1])
            t:SetTexCoord(d / 16, (d + 1) / 16, 0, 1) -- sixteen cells across the strip
            t:SetSize(sizes[i], sizes[i])
            local bob = i == 1 and 0 or (i % 2 == 0 and -BOB or BOB)
            t:SetPoint("CENTER", n, "CENTER", x + adv[i] / 2, sizes[i] * INK / 2 + bob)
            t:Show()
            x = x + adv[i] * GAP
        end
        first = adv[1] or first
    end
    -- the crit burst: its bright core right at the first digit's left edge, partly behind it. A secret amount's width
    -- is unknown, so the burst holds on to the text's own left edge (if the game allows it)
    n.burst:SetShown(kind == "crit")
    n.burst:ClearAllPoints()
    if not hidden and pcall(n.burst.SetPoint, n.burst, "CENTER", n.fill, "LEFT", -DIGIT * 0.17, 0) then return end
    n.burst:SetPoint("CENTER", n, "CENTER", -total / 2 - DIGIT * 0.17, DIGIT * INK * 0.6)
end

-- show text (a number, a secret number or "MISS") at screen point x, y; key groups hits on the same unit
local function spawn(key, x, y, text, kind)
    local n = table.remove(pool) or newNumber()
    layout(n, text, kind)
    local now = GetTime()
    local s = stacks[key]
    if s and now - s[1] < STACK then s[2] = s[2] + 1 else s = {now, 0} end
    s[1], stacks[key] = now, s
    local level = 10 + math.min(s[2], 50) * 8 -- newer lines over older ones
    n:SetFrameLevel(level)
    for i, band in ipairs(n.bands) do band:SetFrameLevel(level + i) end -- each color band over the one below
    n.x, n.y = x + math.random(-4, 4), y + s[2] * LINE
    n.size, n.t0 = DB.scale or 1, now
    n:SetScale(n.size)
    n:SetAlpha(1)
    n:SetPoint("CENTER", UIParent, "BOTTOMLEFT", n.x / n.size, n.y / n.size)
    n:Show()
    live[#live + 1] = n
end

-- rise slowly the whole time, fade after HOLD; done numbers go back to the pool
local driver = CreateFrame("Frame")
driver:SetScript("OnUpdate", function()
    local now = GetTime()
    for i = #live, 1, -1 do
        local n = live[i]
        local t = now - n.t0
        if t >= LIFE then
            n:Hide()
            table.remove(live, i)
            pool[#pool + 1] = n
        else
            n:SetAlpha(t < HOLD and 1 or 1 - (t - HOLD) / (LIFE - HOLD))
            n:SetPoint("CENTER", UIParent, "BOTTOMLEFT", n.x / n.size, (n.y + RISE * t / LIFE) / n.size)
        end
    end
end)

-- where to draw: you a bit over the screen center, your target higher up the middle. Forever forbids measuring
-- nameplates ("Can't measure restricted regions"), so numbers can't sit over each mob.
local function point(unit)
    local w, h = UIParent:GetSize()
    return w / 2, h / 2 + (unit == "player" and (DB.height or 60) or (DB.targetHeight or 170))
end

local function onCombat(unit, action, descriptor, amount)
    if not (DB and DB.on) then return end
    if DB.debug and not secret(action) then print("MapleHits:", unit, action, secret(amount) and "(secreto)" or amount) end
    local onYou = unit == "player"
    if not onYou and (unit ~= "target" or not UnitCanAttack("player", unit)) then return end
    if secret(action) then action = "WOUND" end
    local kind
    if action == "WOUND" then
        local crit = not secret(descriptor) and descriptor == "CRITICAL"
        kind = onYou and "taken" or crit and "crit" or "hit"
    elseif action == "HEAL" then
        kind = "heal"
    elseif action == "ENERGIZE" then
        return
    else -- miss, dodge, parry, resist, immune...: MapleStory just says MISS
        kind, amount = onYou and "missTaken" or "miss", "MISS"
    end
    if amount == nil or (not secret(amount) and type(amount) == "number" and amount <= 0) then return end
    local x, y = point(unit)
    if x then spawn(unit, x, y, amount, kind) end
end

-- the game's own combat text: off while MapleHits draws; your own settings come back with /mh blizz
local function blizzard(show)
    DB.saved = DB.saved or {}
    for _, cv in ipairs(CVARS) do
        local now = GetCVar(cv)
        if now ~= nil then -- a setting this client has
            if not show and DB.saved[cv] == nil and now ~= "0" then DB.saved[cv] = now end
            pcall(SetCVar, cv, show and (DB.saved[cv] or "1") or "0")
        end
    end
    if show then DB.saved = nil end
end

local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_LOGIN")
f:RegisterEvent("PLAYER_ENTERING_WORLD") -- the game can reapply its settings after login
f:RegisterEvent("UNIT_COMBAT")
f:SetScript("OnEvent", function(_, event, ...)
    if event == "UNIT_COMBAT" then return onCombat(...) end
    MapleHitsDB = MapleHitsDB or {on = true, hideBlizz = true}
    DB = MapleHitsDB
    if DB.on and DB.hideBlizz then blizzard(false) end
end)

SLASH_MAPLEHITS1 = "/mh"
SlashCmdList.MAPLEHITS = function(msg)
    local cmd, arg = msg:match("^(%S*)%s*(.-)$")
    if cmd == "teste" then -- a stack like the footage, a hit, a hit on you, both MISS
        local w, h = UIParent:GetSize()
        for i, v in ipairs({{690, "crit"}, {492, "hit"}, {487, "hit"}, {565, "crit"}}) do
            spawn("teste", w / 2 - 120, h / 2 + 80, v[1], v[2])
        end
        spawn("teste2", w / 2 + 90, h / 2 + 150, 709, "hit")
        spawn("teste3", w / 2 + 90, h / 2 + 90, 318, "taken")
        spawn("teste4", w / 2 + 90, h / 2 + 40, "MISS", "miss")
        spawn("teste5", w / 2 + 90, h / 2 - 10, "MISS", "missTaken")
    elseif cmd == "escala" and tonumber(arg) then
        DB.scale = tonumber(arg)
    elseif cmd == "altura" and tonumber(arg) then -- your hits taken
        DB.height = tonumber(arg)
    elseif cmd == "alvo" and tonumber(arg) then -- your hits on the target
        DB.targetHeight = tonumber(arg)
    elseif cmd == "debug" then -- prints every damage event: which units the client reports
        DB.debug = not DB.debug
        print("MapleHits: debug " .. (DB.debug and "ligado" or "desligado"))
    elseif cmd == "blizz" then
        DB.hideBlizz = not DB.hideBlizz
        blizzard(not DB.hideBlizz)
        print("MapleHits: números do jogo " .. (DB.hideBlizz and "escondidos" or "de volta"))
    elseif cmd == "" then
        DB.on = not DB.on
        blizzard(not (DB.on and DB.hideBlizz))
        print("MapleHits: " .. (DB.on and "ligado" or "desligado"))
    else
        print("MapleHits: /mh  ·  teste  ·  escala 1.2  ·  altura 60 (em você)  ·  alvo 170 (no alvo)  ·  blizz  ·  debug")
    end
end
