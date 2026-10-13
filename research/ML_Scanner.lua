-- Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
-- ML_Scanner.lua
-- Sonda SOMENTE LEITURA da Master League. Não escreve nada na memória.
-- Uso: com uma Master League carregada, abra o overlay (Espaço). O ML Scanner é o primeiro
-- módulo. Aperte 8 UMA vez e aguarde.
-- Obs.: o Sider não oferece pcall/os.* aos módulos; não usar.
-- Histórico:
--  v0.2: elencos NÃO estão como lista contígua de ids u32 (formato do EDIT).
--  v0.4: tudo relevante está na região 1 (0x7FF4D0000000..0x7FF4DFFFFFF0).
--  v0.5: CONFIRMADO com o elenco do usuário (Man Utd, ML 2033). Registro de time:
--        nome UTF-8 em +0 (70 bytes), sigla em +70, elenco em +328: 40 pares
--        (u32 registro_ml, u32 id_jogador), vazio = registro 0xFFFF. Na cópia base
--        (EDIT original) o registro é 0. Registros de time parecem ter 1680 bytes.
--        id com bit 0x80000000 = jogador criado/gerado. registro 0xDA7Exxxx = ? (empréstimo?)
--  v0.6: exporta TODOS os times da cópia da ML para ml_teams.txt.
--  v0.7: pode rodar várias vezes; cada leitura vai para ml_teams_N.txt (N = 1, 2, 3...)
--        e inclui o registro bruto do time âncora (1680 bytes) para comparar antes/depois.

local m = { version = "1.3" }

local REGION = { 0x00007FF4D0000000, 0x00007FF4DFFFFFF0 }
local STRIDE = 1680
local ROSTER = 328
local ANCHOR_NAME = "MANCHESTER UNITED\x00"

local status = "7 = foto | 8 = times | 9 = sonda (somente leitura)"
local state = "idle"
local KEY_SCAN = 0x38 -- 8

local function u32at(addr)
    local b = memory.read(addr, 4)
    if not b then return nil end
    return memory.unpack("u32", b)
end

local function name_at(addr)
    local b = memory.read(addr, 70)
    if not b then return nil end
    local s = b:match("^([^%z]*)")
    if not s or #s < 2 then return nil end
    local c = s:byte(1)
    if c < 0x20 or c == 0xff then return nil end
    return s
end

-- um registro de time válido: nome legível e primeiro par do elenco coerente
local function is_team(addr)
    local nm = name_at(addr)
    if not nm then return nil end
    local e = u32at(addr + ROSTER)
    if e == nil then return nil end
    return nm
end

local function find_ml_anchor()
    local start = REGION[1]
    for _ = 1, 8 do
        local a = memory.safe_search(ANCHOR_NAME, start, REGION[2])
        if not a then return nil end
        local e = u32at(a + ROSTER)
        if e and e ~= 0 and e ~= 0xffff then return a end -- cópia da ML (registro != 0)
        start = a + 1
    end
end

local function next_file()
    local n = 1
    while true do
        local name = string.format("ml_teams_%d.txt", n)
        local h = io.open(name, "r")
        if not h then return name end
        h:close()
        n = n + 1
    end
end

local last_file = ""

local function scan()
    last_file = next_file()
    local f = io.open(last_file, "w")
    if not f then
        status = "Erro: não consegui criar " .. last_file
        return
    end
    log("[ML_Scanner] procurando âncora")
    local anchor = find_ml_anchor()
    if not anchor then
        f:write("ancora nao encontrada\n")
        f:close()
        status = "Âncora não encontrada. Avise o Claude."
        return
    end
    -- volta até o primeiro registro válido da tabela
    local first = anchor
    while is_team(first - STRIDE) do first = first - STRIDE end
    f:write(string.format("# ML_Scanner %s | ancora %s | inicio %s | stride %d\n",
        m.version, tostring(anchor), tostring(first), STRIDE))
    f:write("# indice|endereco|nome|sigla|n|registro:id,...\n")
    local addr, n_teams = first, 0
    while true do
        local nm = is_team(addr)
        if not nm then break end
        local short = (memory.read(addr + 70, 4) or ""):match("^([^%z]*)") or ""
        local pairs_ = {}
        local raw = memory.read(addr + ROSTER, 40 * 8) or ""
        for i = 0, 39 do
            local e = memory.unpack("u32", raw:sub(i * 8 + 1, i * 8 + 4))
            local p = memory.unpack("u32", raw:sub(i * 8 + 5, i * 8 + 8))
            if e == 0xffff then break end
            pairs_[#pairs_ + 1] = string.format("%d:%d", e, p)
        end
        f:write(string.format("%d|%s|%s|%s|%d|%s\n", n_teams, tostring(addr), nm, short, #pairs_,
            table.concat(pairs_, ",")))
        n_teams = n_teams + 1
        addr = addr + STRIDE
        if n_teams > 2000 then break end
    end
    -- registro bruto do time âncora, para comparar antes/depois
    local raw = memory.read(anchor - 96, STRIDE) or ""
    f:write("# RAW ancora (a partir de -96):\n")
    for i = 1, #raw, 32 do
        local line = {}
        for j = i, math.min(i + 31, #raw) do line[#line + 1] = string.format("%02x", raw:byte(j)) end
        f:write(string.format("#RAW %+05d %s\n", i - 1 - 96, table.concat(line)))
    end
    f:close()
    status = string.format("Concluído: %d times -> %s. Aperte 8 de novo para outra leitura.", n_teams, last_file)
    log("[ML_Scanner] " .. status)
end

local function next_name(prefix, ext)
    local n = 1
    while true do
        local name = string.format("%s_%d.%s", prefix, n, ext)
        local h = io.open(name, "r")
        if not h then return name end
        h:close()
        n = n + 1
    end
end

-- ===== v0.8: sonda de contratos (tecla 9) =====
-- Referências tiradas das telas do usuário (ML 2033, Man Utd):
--  Gavi  reg 1158 id 134417: empréstimo sem opção, fim empréstimo 31/12/2033, contrato até 31/8/2036,
--        salário R$ 42.857.670, multa R$ 681.267.920, valor R$ 476.411.190
--  Diop  reg 8914 id 139221: empréstimo com opção (R$ 6.313.690; salário R$ 21.446.250),
--        salário R$ 14.361.140, multa R$ 20.227.630, valor R$ 12.884.090
--  Bruno reg 359 id 60512: contrato normal (controle)
--  Datas da ML: u16 ano, u8 mês, u8 dia (ex.: f1 07 01 15 = 21/1/2033)
local KEY_PROBE = 0x39 -- 9

local function hex_lines(addr, before, len)
    local bytes = memory.read(addr - before, len)
    if not bytes then return "  (ilegível)\n" end
    local out = {}
    for i = 1, #bytes, 16 do
        local line = {}
        for j = i, math.min(i + 15, #bytes) do line[#line + 1] = string.format("%02x", bytes:byte(j)) end
        out[#out + 1] = string.format("  %+05d: %s", i - 1 - before, table.concat(line, " "))
    end
    return table.concat(out, "\n") .. "\n"
end

local function probe_contracts()
    local fname = next_name("ml_probe", "txt")
    local f = io.open(fname, "w")
    if not f then status = "Erro ao criar " .. fname return end
    local function w(s) f:write(s) f:flush() end
    local function u32(v) return memory.pack("u32", v) end
    local RANGES = {
        { 0x00007FF4D0000000, 0x00007FF4DFFFFFF0 }, { 0x00007FF4E0000000, 0x00007FF4EFFFFFF0 },
        { 0x00007FF4F0000000, 0x00007FF4FFFFFFF0 }, { 0x00007FF4C0000000, 0x00007FF4CFFFFFF0 },
    }
    local function probe(label, pattern, max, before, len)
        log("[ML_Scanner] " .. label)
        local hits = {}
        for _, r in ipairs(RANGES) do
            local start = r[1]
            while #hits < max do
                local a = memory.safe_search(pattern, start, r[2])
                if not a then break end
                hits[#hits + 1] = a
                start = a + 1
            end
        end
        w(string.format("== %s: %d ocorrência(s)%s\n", label, #hits, #hits >= max and " (limite)" or ""))
        for _, a in ipairs(hits) do w(string.format(" em %s\n", tostring(a)) .. hex_lines(a, before, len)) end
        w("\n")
    end
    w("ML_Scanner " .. m.version .. " - sonda de contratos\n\n")
    -- v1.3: mapa da tabela de elencos da região 3 (candidata a "fonte da verdade").
    -- Acha o elenco do Man Utd na região 3 e grava 8 KB antes / 2 KB depois em hex contínuo.
    local pat = u32(355) .. u32(140699) .. u32(363) .. u32(134931)
    local hit = memory.safe_search(pat, 0x00007FF4F0000000, 0x00007FF4FFFFFFF0)
    if not hit then
        w("elenco do Man Utd NAO encontrado na regiao 3\n")
    else
        w(string.format("ANCORA_R3 %s\n", tostring(hit)))
        local from, len = hit - 8192, 8192 + 2048
        local raw = memory.read(from, len) or ""
        w(string.format("DUMP_INICIO %s (ancora em +8192)\n", tostring(from)))
        for i = 1, #raw, 32 do
            local line = {}
            for j = i, math.min(i + 31, #raw) do line[#line + 1] = string.format("%02x", raw:byte(j)) end
            w(table.concat(line) .. "\n")
        end
    end
    f:close()
    status = "Sonda concluída -> " .. fname .. ". Avise o Claude."
    log("[ML_Scanner] " .. status)
end

-- ===== v1.0: foto da memória (tecla 7) =====
-- Grava a faixa onde ficam fichas de jogador, times e listas da ML em ml_snap_N.bin, para
-- comparar antes/depois de um evento conhecido (ex.: renovação de contrato) fora do jogo.
-- Blocos ilegíveis são gravados como zeros.
local KEY_SNAP = 0x37 -- 7
local SNAP_FROM, SNAP_TO, BLOCK = 0x00007FF4D7E00000, 0x00007FF4DCC00000, 0x100000

local function snapshot()
    local fname = next_name("ml_snap", "bin")
    local f = io.open(fname, "wb")
    if not f then status = "Erro ao criar " .. fname return end
    local zeros = string.rep("\0", BLOCK)
    local bad = 0
    log(string.format("[ML_Scanner] foto %s de %s a %s", fname, tostring(SNAP_FROM), tostring(SNAP_TO)))
    local addr = SNAP_FROM
    while addr < SNAP_TO do
        local b = memory.read(addr, BLOCK)
        if not b or #b ~= BLOCK then b = zeros bad = bad + 1 end
        f:write(b)
        addr = addr + BLOCK
    end
    f:close()
    status = string.format("Foto concluída -> %s (%d blocos ilegíveis). Avise o Claude.", fname, bad)
    log("[ML_Scanner] " .. status)
end

-- ===== v1.1: PRIMEIRO TESTE DE ESCRITA (tecla 6 aplica, tecla 5 desfaz) =====
-- Move Will Hughes (reg 200, id 101027), último da lista do EVERTON, para a primeira vaga do BRENTFORD.
-- Só escreve se TODAS as conferências passarem. A mudança fica só na memória: fechar o jogo sem
-- salvar descarta tudo. Números de camisa: u16[40] em +662 do registro do time (vazio = 0).
local KEY_APPLY, KEY_UNDO = 0x36, 0x35 -- 6, 5
local NUMBERS = 662
local T_FROM, T_TO = { idx = 8, name = "EVERTON" }, { idx = 3, name = "BRENTFORD" }
local MOVE = { reg = 200, id = 101027, name = "Will Hughes" }
local undo = nil

local function u16at(addr)
    local b = memory.read(addr, 2)
    return b and memory.unpack("u16", b)
end

local function roster_count(team)
    for i = 0, 39 do
        if u32at(team + ROSTER + i * 8) == 0xffff then return i end
    end
    return 40
end

local function write_test()
    local function fail(msg)
        status = "TESTE CANCELADO (nada foi escrito): " .. msg
        log("[ML_Scanner] " .. status)
    end
    if undo then return fail("teste já aplicado; aperte 5 para desfazer primeiro") end
    local anchor = find_ml_anchor()
    if not anchor then return fail("âncora não encontrada") end
    local first = anchor
    while is_team(first - STRIDE) do first = first - STRIDE end
    local a = first + T_FROM.idx * STRIDE
    local b = first + T_TO.idx * STRIDE
    if name_at(a) ~= T_FROM.name then return fail("time origem inesperado: " .. tostring(name_at(a))) end
    if name_at(b) ~= T_TO.name then return fail("time destino inesperado: " .. tostring(name_at(b))) end
    local na, nb = roster_count(a), roster_count(b)
    local la = a + ROSTER + (na - 1) * 8
    if u32at(la) ~= MOVE.reg or u32at(la + 4) ~= MOVE.id then
        return fail(string.format("%s não é o último do %s (achei %s:%s)", MOVE.name, T_FROM.name,
            tostring(u32at(la)), tostring(u32at(la + 4))))
    end
    if nb >= 40 then return fail("destino sem vaga") end
    -- números de camisa coerentes com a quantidade de jogadores?
    local num_a = u16at(a + NUMBERS + (na - 1) * 2)
    if not num_a or num_a == 0 or num_a > 99 or u16at(a + NUMBERS + na * 2) ~= 0 then
        return fail("números de camisa do time origem não estão onde eu esperava")
    end
    if u16at(b + NUMBERS + nb * 2) ~= 0 or (nb > 0 and u16at(b + NUMBERS + (nb - 1) * 2) == 0) then
        return fail("números de camisa do time destino não estão onde eu esperava")
    end
    local used = {}
    for i = 0, nb - 1 do used[u16at(b + NUMBERS + i * 2)] = true end
    local num_b = num_a
    if used[num_b] then
        num_b = 2
        while used[num_b] and num_b < 99 do num_b = num_b + 1 end
    end
    local lb = b + ROSTER + nb * 8
    undo = {
        { la, memory.read(la, 8) }, { a + NUMBERS + (na - 1) * 2, memory.read(a + NUMBERS + (na - 1) * 2, 2) },
        { lb, memory.read(lb, 8) }, { b + NUMBERS + nb * 2, memory.read(b + NUMBERS + nb * 2, 2) },
    }
    -- escrita: destino primeiro, depois libera a vaga na origem
    memory.write(lb, memory.pack("u32", MOVE.reg) .. memory.pack("u32", MOVE.id))
    memory.write(b + NUMBERS + nb * 2, memory.pack("u16", num_b))
    memory.write(la, memory.pack("u32", 0xffff) .. memory.pack("u32", 0))
    memory.write(a + NUMBERS + (na - 1) * 2, memory.pack("u16", 0))
    status = string.format("TESTE APLICADO: %s %s(%d) -> %s(%d), camisa %d. Confira no jogo. 5 = desfazer.",
        MOVE.name, T_FROM.name, roster_count(a), T_TO.name, roster_count(b), num_b)
    log("[ML_Scanner] " .. status)
end

local function undo_test()
    if not undo then
        status = "Nada para desfazer."
        return
    end
    for _, u in ipairs(undo) do memory.write(u[1], u[2]) end
    undo = nil
    status = "Teste DESFEITO: memória voltou ao estado anterior."
    log("[ML_Scanner] " .. status)
end

local function key_down(ctx, vkey)
    if state ~= "idle" then return end
    -- teclas 6/5 (teste de escrita na memória) desativadas: teste concluído em 30/09/2026
    if vkey == KEY_SNAP then
        state = "running"
        status = "Tirando foto da memória..."
        snapshot()
        state = "idle"
        return
    end
    if vkey == KEY_SCAN then
        state = "running"
        status = "Lendo times..."
        scan()
        state = "idle"
    elseif vkey == KEY_PROBE then
        state = "running"
        status = "Sondando contratos..."
        probe_contracts()
        state = "idle"
    end
end

local function overlay_on(ctx)
    return "ML Scanner " .. m.version .. " (somente leitura)\n" .. status
end

function m.init(ctx)
    ctx.register("overlay_on", overlay_on)
    ctx.register("key_down", key_down)
end

return m
