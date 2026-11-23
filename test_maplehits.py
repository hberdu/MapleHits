"""Runs MapleHits on Lua 5.1 against stubbed WoW APIs; checks the digit textures exist. Needs: py -m pip install lupa"""
from pathlib import Path

from lupa.lua51 import LuaRuntime

DIR = Path(__file__).parent
for name in ("hit", "crit", "taken", "heal", "miss_hit", "miss_taken", "burst"):
    assert (DIR / "art" / f"{name}.tga").exists(), name  # make_maplehits_art.py draws them

STUBS = r"""
NOW, FRAMES, CVAR, PLATES, ENEMY, TARGETED, SHOWN = 100, {}, {}, {}, {}, {}, {}
SECRET = setmetatable({}, {__add = error, __sub = error, __mul = error, __div = error, __lt = error, __le = error,
    __concat = error, __len = error, __unm = error})   -- a secret value: no math, no comparing, no joining
function GetTime() return NOW end
function issecretvalue(v) return v == SECRET end
CVAR.enableFloatingCombatText, CVAR.floatingCombatTextCombatDamage, CVAR.floatingCombatTextCombatDamage_v2 = "1", "1", "2"
function SetCVar(k, v) CVAR[k] = v end
function GetCVar(k) return CVAR[k] end
function UnitCanAttack(_, u) return ENEMY[u] or false end
function UnitIsUnit(a) return TARGETED[a] or false end
C_NamePlate = {GetNamePlateForUnit = function(u) return PLATES[u] end}
local function plate(x, top)
    return {GetCenter = function() return x, 0 end, GetTop = function() return top end,
            GetEffectiveScale = function() return 1 end}
end
PLATES.nameplate1, ENEMY.nameplate1, ENEMY.target = plate(500, 300), true, true
PLATES.target = PLATES.nameplate1                       -- the target is that mob
local mt = {}
function mock() return setmetatable({}, mt) end
local function set(k) return function(self, ...) rawset(self, "_" .. k, {...}) end end
mt.__index = function(_, k)
    if k == "SetText" then return function(self, s) rawset(self, "text", s); SHOWN[#SHOWN + 1] = s end end
    if k == "SetTexture" or k == "SetTexCoord" or k == "SetPoint" or k == "SetSize" or k == "SetFrameLevel" then return set(k) end
    if k == "Show" then return function(self) rawset(self, "on", true) end end
    if k == "Hide" then return function(self) rawset(self, "on", false) end end
    if k == "SetShown" then return function(self, v) rawset(self, "on", v and true or false) end end
    if k == "SetScript" then return function(self, name, fn) rawset(self, name, fn) end end
    if k == "CreateTexture" then return function(self) return mock() end end
    if k == "GetSize" then return function() return 1000, 800 end end
    if k == "GetEffectiveScale" then return function() return 1 end end
    return function() return mock() end
end
UIParent = mock()
SlashCmdList = {}
NUMS = {}
function CreateFrame(_, _, parent)
    local o = mock()
    FRAMES[#FRAMES + 1] = o
    if parent == UIParent then NUMS[#NUMS + 1] = o end -- a damage number
    return o
end
"""

SCENARIO = r"""
local driver, events = FRAMES[1], FRAMES[2]
local function ev(...) events.OnEvent(events, ...) end
local function tick() driver.OnUpdate(driver, 0.01) end
local function digits(n)                                 -- the shown digits of a number: strip and digit
    local out = {}
    for _, t in ipairs(n.digits) do
        if rawget(t, "on") then
            out[#out + 1] = rawget(t, "_SetTexture")[1]:match("art\\(%w+)$") .. math.floor(rawget(t, "_SetTexCoord")[1] * 16 + 0.5)
        end
    end
    return table.concat(out, " ")
end
local function word(n) return rawget(n.word, "on") and rawget(n.word, "_SetTexture")[1]:match("art\\([%w_]+)$") end
ev("PLAYER_LOGIN")
assert(CVAR.floatingCombatTextCombatDamage == "0" and CVAR.floatingCombatTextCombatDamage_v2 == "0" and CVAR.enableFloatingCombatText == "0")
assert(CVAR.floatingCombatTextPetMeleeDamage == nil)                   -- settings this client lacks stay untouched
ev("PLAYER_ENTERING_WORLD"); assert(MapleHitsDB.saved.floatingCombatTextCombatDamage_v2 == "2")  -- yours kept once
ev("UNIT_COMBAT", "target", "WOUND", "", 120, 1)
local a = NUMS[#NUMS]
assert(digits(a) == "hit1 hit2 hit0", digits(a))
local d1, d2 = a.digits[1], a.digits[2]
assert(math.abs(rawget(d1, "_SetSize")[1] - 78) < 1e-9 and rawget(d2, "_SetSize")[1] == 60)   -- first digit 1.3x
local ink = NS.INK                                       -- bottoms lined up, then the bob: 2nd down, 3rd up
assert(math.abs(rawget(d1, "_SetPoint")[5] - 78 * ink / 2) < 1e-9 and math.abs(rawget(d2, "_SetPoint")[5] - (60 * ink / 2 - 2)) < 1e-9 and math.abs(rawget(a.digits[3], "_SetPoint")[5] - (60 * ink / 2 + 2)) < 1e-9)
local n = #NUMS
ev("UNIT_COMBAT", "nameplate1", "WOUND", "", 120, 1)    -- nameplates: Forever won't let them be measured, skipped
ev("UNIT_COMBAT", "party1", "WOUND", "", 50, 1)
assert(#NUMS == n)
ev("UNIT_COMBAT", "target", "WOUND", "CRITICAL", 900, 1)
local b = NUMS[#NUMS]
assert(digits(b) == "crit9 crit0 crit0" and rawget(b.burst, "on"))
NOW = NOW + 0.1; tick()
assert(math.abs((b._SetPoint[5] - a._SetPoint[5]) - 60 * NS.INK * 0.67) < 1e-9)  -- stacked a tight line up
ev("UNIT_COMBAT", "player", "WOUND", "", 30, 1)
assert(digits(NUMS[#NUMS]) == "taken3 taken0" and not rawget(NUMS[#NUMS].burst, "on"))
ev("UNIT_COMBAT", "target", "DODGE", "", 0, 1)
assert(word(NUMS[#NUMS]) == "miss_hit" and digits(NUMS[#NUMS]) == "")                      -- you missed: your colors
ev("UNIT_COMBAT", "player", "MISS", "", 0, 1)
assert(word(NUMS[#NUMS]) == "miss_taken")                                                  -- the mob missed you: violet
ev("UNIT_COMBAT", "target", "WOUND", SECRET, SECRET, 1)              -- secret: whole, layered, never computed with
local sn = NUMS[#NUMS]
assert(rawget(sn.fill, "text") == SECRET and rawget(sn.fill, "on") and digits(sn) == "")
for _, fs in ipairs(sn.secret) do assert(rawget(fs, "text") == SECRET and rawget(fs, "on")) end
assert(#sn.secret == 12 + 12 + 1 + 9)                                                      -- outline, rim, fill, nine bands
for i, band in ipairs(sn.bands) do assert(band._SetFrameLevel[1] == sn._SetFrameLevel[1] + i) end  -- bands stacked in order
n = #NUMS
ENEMY.target = false; ev("UNIT_COMBAT", "target", "WOUND", "", 10, 1); ENEMY.target = true
assert(#NUMS == n)                                                                          -- friendly: nothing
NOW = NOW + 5; tick()                                                                       -- all done: pooled
ev("UNIT_COMBAT", "target", "WOUND", "", 77, 1)
assert(#NUMS == n)                                                                          -- reused, no new number
local reused
for _, x in ipairs(NUMS) do if digits(x) == "hit7 hit7" then reused = x end end
for _, fs in ipairs(reused.secret) do assert(not rawget(fs, "on")) end                     -- the secret layers hidden
SlashCmdList.MAPLEHITS("alvo 200"); assert(MapleHitsDB.targetHeight == 200)
SlashCmdList.MAPLEHITS("blizz"); assert(CVAR.floatingCombatTextCombatDamage == "1" and CVAR.floatingCombatTextCombatDamage_v2 == "2" and CVAR.enableFloatingCombatText == "1" and MapleHitsDB.saved == nil)
SlashCmdList.MAPLEHITS("debug"); ev("UNIT_COMBAT", "target", "WOUND", "", 8, 1); SlashCmdList.MAPLEHITS("debug")
SlashCmdList.MAPLEHITS("teste")
"""

lua = LuaRuntime()
lua.execute(STUBS)
load = lua.eval("function(src, name) return assert(loadstring(src, name)) end")
ns = lua.table()
load((DIR / "Art.lua").read_text(encoding="utf-8"), "Art.lua")("MapleHits", ns)
load((DIR / "MapleHits.lua").read_text(encoding="utf-8"), "MapleHits.lua")("MapleHits", ns)
lua.globals().NS = ns
lua.execute(SCENARIO)
print("ok")
