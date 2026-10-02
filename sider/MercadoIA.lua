-- MercadoIA.lua
-- Interface do "Mercado IA" (cérebro de transferências que roda fora do jogo).
-- Fluxo: na janela de transferências, abra o overlay neste módulo e aperte 8 ->
--   1) tira uma foto da memória (atributos atuais dos jogadores) em mercado_snap.bin
--   2) cria mercado_pedido.txt
-- Depois SALVE a carreira. O programa vigia.py (rodando junto com o jogo) aplica o mercado no save
-- e escreve mercado_status.txt / mercado_noticias.txt, que este módulo mostra. Então CARREGUE a carreira.
-- Este módulo NÃO escreve na memória do jogo.
-- Obs.: o Sider não oferece pcall/os.* aos módulos.

local m = { version = "1.0" }

local KEY_REQUEST = 0x38 -- 8
local SNAP_FROM, SNAP_TO, BLOCK = 0x00007FF4D7E00000, 0x00007FF4DCC00000, 0x100000
local REFRESH_FRAMES = 90

local msg = "Na janela de transferências: aperte 8, depois SALVE a carreira."
local cached_status, cached_news = "", ""
local frames = REFRESH_FRAMES

local function read_file(name, max_lines)
    local f = io.open(name, "r")
    if not f then return "" end
    local lines, n = {}, 0
    for line in f:lines() do
        n = n + 1
        if n > max_lines then break end
        lines[#lines + 1] = line
    end
    f:close()
    return table.concat(lines, "\n")
end

local function snapshot()
    local f = io.open("mercado_snap.bin", "wb")
    if not f then return false end
    local zeros = string.rep("\0", BLOCK)
    local addr = SNAP_FROM
    while addr < SNAP_TO do
        local b = memory.read(addr, BLOCK)
        if not b or #b ~= BLOCK then b = zeros end
        f:write(b)
        addr = addr + BLOCK
    end
    f:close()
    return true
end

local function request()
    msg = "Lendo os jogadores..."
    if not snapshot() then
        msg = "Erro: não consegui gravar mercado_snap.bin"
        return
    end
    local f = io.open("mercado_pedido.txt", "w")
    if not f then
        msg = "Erro: não consegui gravar mercado_pedido.txt"
        return
    end
    f:write("pedido do mercado\n")
    f:close()
    msg = "Pronto! Agora SALVE a carreira e aguarde o aviso aqui."
    log("[MercadoIA] pedido criado")
    frames = REFRESH_FRAMES
end

local function key_down(ctx, vkey)
    if vkey == KEY_REQUEST then request() end
end

local function overlay_on(ctx)
    frames = frames + 1
    if frames >= REFRESH_FRAMES then
        frames = 0
        cached_status = read_file("mercado_status.txt", 3)
        cached_news = read_file("mercado_noticias.txt", 16)
    end
    local out = "Mercado IA " .. m.version .. "\n" .. msg
    if cached_status ~= "" then out = out .. "\n\n" .. cached_status end
    if cached_news ~= "" then out = out .. "\n\n" .. cached_news end
    return out
end

function m.init(ctx)
    ctx.register("overlay_on", overlay_on)
    ctx.register("key_down", key_down)
end

return m
