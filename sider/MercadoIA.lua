-- Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
-- MercadoIA.lua
-- Interface do "Mercado IA" / "Vestiário IA" (cérebros que rodam fora do jogo).
-- Tecla 8 (mercado, na janela de transferências) ou 9 (vestiário, depois de cada jogo): cria o pedido
-- (mercado_pedido.txt / vestiario_pedido.txt). O vigia.py tira a foto da memória DE FORA do jogo
-- (Windows, sem risco) e, quando você SALVAR a carreira, aplica no save. Então CARREGUE a carreira.
-- Status e notícias: mercado_status.txt, mercado_noticias.txt, vestiario_noticias.txt (mostrados aqui).
-- v1.2 (09/10/2026): este módulo NÃO lê nem escreve memória. A v1.0/1.1 lia endereços fixos com
-- memory.read e derrubou o jogo quando a tabela de jogadores mudou de lugar.
-- v1.3: teclas 1/2/3 respondem ao pedido de conversa de um jogador (vestiario_decisao.txt ->
-- vestiario_resposta.txt); a resposta vale na reunião seguinte.
-- Obs.: o Sider não oferece pcall/os.* aos módulos.

local m = { version = "1.3" }

local KEY_REQUEST = 0x38 -- 8 = mercado (janela de transferências)
local KEY_VESTIARIO = 0x39 -- 9 = vestiário (depois de cada jogo: moral -> setas + notícias)
local REFRESH_FRAMES = 90

local msg = "8 = mercado (na janela)   9 = vestiário (depois de cada jogo). Depois SALVE a carreira."
local cached_status, cached_news, cached_vest = "", "", ""
local cached_dec, cached_resp = "", ""
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

local function create_request(file, text, label)
    local f = io.open(file, "w")
    if not f then
        msg = "Erro: não consegui gravar " .. file
        return
    end
    f:write(text .. "\n")
    f:close()
    msg = label .. ": pedido feito. Aguarde 'foto tirada' e então SALVE a carreira."
    log("[MercadoIA] " .. file .. " criado")
    frames = REFRESH_FRAMES
end

local function request()
    create_request("mercado_pedido.txt", "pedido do mercado", "Mercado")
end

local function request_vestiario()
    create_request("vestiario_pedido.txt", "pedido do vestiario", "Vestiário")
end

-- teclas 1, 2, 3: resposta ao pedido de conversa de um jogador (só quando há decisão pendente)
local function answer(option)
    if read_file("vestiario_decisao.txt", 1) == "" then return end
    local f = io.open("vestiario_resposta.txt", "w")
    if not f then
        msg = "Erro: não consegui gravar vestiario_resposta.txt"
        return
    end
    f:write(option .. "\n")
    f:close()
    msg = "Resposta registrada: opção " .. option .. ". Vale na próxima reunião (tecla 9 depois do jogo)."
    log("[MercadoIA] resposta do vestiario: " .. option)
    frames = REFRESH_FRAMES
end

local function key_down(ctx, vkey)
    if vkey == KEY_REQUEST then request() end
    if vkey == KEY_VESTIARIO then request_vestiario() end
    if vkey == 0x31 then answer("1") end
    if vkey == 0x32 then answer("2") end
    if vkey == 0x33 then answer("3") end
end

local function overlay_on(ctx)
    frames = frames + 1
    if frames >= REFRESH_FRAMES then
        frames = 0
        cached_status = read_file("mercado_status.txt", 3)
        cached_news = read_file("mercado_noticias.txt", 16)
        cached_vest = read_file("vestiario_noticias.txt", 20)
        cached_dec = read_file("vestiario_decisao.txt", 12)
        cached_resp = read_file("vestiario_resposta.txt", 1)
    end
    local out = "Mercado IA " .. m.version .. "\n" .. msg
    if cached_dec ~= "" then
        out = out .. "\n\n" .. cached_dec
        if cached_resp ~= "" then out = out .. "\n  >> Sua resposta: " .. cached_resp end
    end
    if cached_status ~= "" then out = out .. "\n\n" .. cached_status end
    if cached_vest ~= "" then out = out .. "\n\n" .. cached_vest end
    if cached_news ~= "" then out = out .. "\n\n" .. cached_news end
    return out
end

function m.init(ctx)
    ctx.register("overlay_on", overlay_on)
    ctx.register("key_down", key_down)
end

return m
