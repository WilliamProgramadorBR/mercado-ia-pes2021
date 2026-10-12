"""Leitura (SOMENTE LEITURA, por enquanto) da tabela de jogadores da carreira guardada no save da Master League.

Engenharia reversa de 09/10/2026 (save de 2033, Man Utd):
  - O data.dat descriptografado tem, perto do fim (~0x1140000), uma sequência de blocos zlib.
    Cada bloco é precedido por 16 bytes: u32 soma de verificação (?), u32 BE tamanho descomprimido (0x40000),
    u32 BE tamanho comprimido, u32 BE deslocamento. Descomprimidos e emendados dão ~4,68 MB ("blob").
  - No blob, a partir do byte 32, um registro de 156 bytes por jogador da carreira (24.093 no save de 2033).
    TODOS os jogadores da foto de memória estão aqui (mesmo par registro/id).
  - Os ATRIBUTOS NÃO ficam no save: o jogo recalcula ao carregar (base do banco + curva de idade/crescimento).
    Jogadores aposentados são reaproveitados como jovens (mesmo id, outra idade).

Registro de 156 bytes (CONFIRMADO = bate com a memória em 100%; PROVÁVEL = estatística, falta conferir na tela):
  +0   u32 registro na ML                                    CONFIRMADO
  +4   u32 id do jogador (0x8000xxxx = criado pela ML)       CONFIRMADO
  +8   10 x u32 lista (igual à ficha da memória +320); 0xFFFF = vazio. Muda com o tempo (competições/temporadas?)
  +72  u8   PROVÁVEL "Função no time" nativa da ML (0 = nenhuma; 18 = Ídolo — mesmo código da mensagem
            "Troca na função" — Mainoo; William 16 = Virtuoso?). Ver tela Informações do time > Função no time.
  +73..+77  bytes que crescem com a idade e com jogos (b77 corr. idade 0,76) — histórico/experiência?
  +84  u32  SALÁRIO ANUAL: na tela = valor x 430 (R$)        CONFIRMADO (Bruno 48603 -> R$ 20.899.290; Wallace)
  +88  u32  0 / 5000 / ... / 2.000.000 (Gavi emprestado = 800000)  desconhecido (taxa de empréstimo? bônus?)
  +100 data fim do contrato (u16 ano, u8 mês, u8 dia)        CONFIRMADO (Bruno e Wallace 31/8/2036)
  +104 data de chegada ao clube                              PROVÁVEL (2020-01-01 = elenco inicial)
  +112 u16  0..312
  +114 u16  0..3000 para quem tem clube (só cresce; jovens da base travam em 3000); alto para sem clube
  +118 u8   0..100 (100 é o mais comum; veteranos baixos)    PROVÁVEL satisfação/moral?
  +120 u16  bits 0-6: 0..100 (quase todos 100)              QUASE CERTO condição física (cansaço): na tela de
                                                             09/10 os 12 reservas = 100 e os 11 titulares < 100
            bits 7-9: 0..4 (2 é o mais comum)                CONFIRMADO seta de condição (0 vermelha p/ baixo,
                                                             1 laranja diagonal, 2 amarela, 3 verde diagonal,
                                                             4 verde p/ cima): 24 de 24 iguais à tela em 09/10/2026
                                                             ESCRITA PROVADA em 09/10/2026: Lammens 1 -> 4 via
                                                             regravar() e o jogo mostrou verde p/ cima no pré-jogo.
                                                             O jogo recalcula as setas de tempos em tempos.
            bits 10-15: flags raras                           lesão? suspensão?
  +122 u8   0..7 (0 = sem clube)                             tipo/situação de contrato

Fora do blob (data.dat descriptografado, save de 09/10/2026):
  - Logo DEPOIS do último bloco zlib: tabela de CONTRATOS do time do usuário, 50 bytes cada:
    u16 ?, u32 registro, u32 id, u32 salário (x430), u32 taxa de rescisão (x430), data fim, u16 índice, ...,
    data de assinatura, 10 x 0xFF. Renovação gera um contrato novo (o antigo continua na lista).
  - ORÇAMENTO DE TRANSFERÊNCIAS do usuário: u32 (x430) — estava em 0xc7dd00 (não assumir posição fixa).
    Orçamento de salários (R$ 238.450.050 = 554535) ainda não localizado (deve ser calculado).
  - Valor de mercado NÃO está gravado (o jogo calcula).
"""
import struct
import zlib

REC = 156
FIRST = 32


def blocos(d, start=0x1000000):
    """[(offset_no_save, tamanho_comprimido, dados)] dos blocos zlib emendados do save."""
    out = []
    o = d.find(b'\x78', start)
    while 0 <= o < len(d):
        try:
            z = zlib.decompressobj()
            raw = z.decompress(d[o:o + 600000])
            if not z.eof or len(raw) < 1000:
                raise ValueError
            used = min(600000, len(d) - o) - len(z.unused_data)
            out.append((o, used, raw))
            o = d.find(b'\x78', o + used)
        except (zlib.error, ValueError):
            o = d.find(b'\x78', o + 1)
    return out


def blob(data_dat_bytes):
    return b''.join(r for _, _, r in blocos(data_dat_bytes))


def registros(b):
    """{(registro, id): bytes do registro de 156} a partir do blob."""
    out = {}
    for o in range(FIRST, len(b) - REC + 1, REC):
        reg, pid = struct.unpack_from('<II', b, o)
        if pid:
            out[(reg, pid)] = b[o:o + REC]
    return out


def campos(r):
    u120 = struct.unpack_from('<H', r, 120)[0]
    y1, m1, d1 = struct.unpack_from('<HBB', r, 100)
    y2, m2, d2 = struct.unpack_from('<HBB', r, 104)
    return {
        'apelido': struct.unpack_from('<I', r, 80)[0] & 0xFFFF,   # código do apelido nativo (0 = nenhum)
        'funcao': r[72],        # "Função no time" nativa (0 = nenhuma; ver vestiario.FUNCOES)
        'funcao_prog': r[77],   # progresso na função 0-255 (Nv.3 ~ alto, Nv.1 ~ baixo) — provável
        'salario': struct.unpack_from('<I', r, 84)[0],  # x430 = R$ na tela
        'u88': struct.unpack_from('<I', r, 88)[0],
        'contrato_fim': (y1, m1, d1) if y1 != 0xFFFF else None,
        'chegada': (y2, m2, d2) if y2 != 0xFFFF else None,
        'u112': struct.unpack_from('<H', r, 112)[0],
        'u114': struct.unpack_from('<H', r, 114)[0],
        'b118': r[118],
        'lesao': r[116],   # 12/10/2026: contador de recuperação de lesão (0 = apto; só William 7->6 entre 24 mil)
        'condicao': u120 & 0x7F,
        'seta': (u120 >> 7) & 7,
        'flags120': u120 >> 10,
        'b122': r[122],
    }


def set_seta(r, seta):
    """Novo registro (bytes) com a seta de condição trocada (0 pior .. 4 ótima)."""
    assert 0 <= seta <= 4
    r = bytearray(r)
    u = struct.unpack_from('<H', r, 120)[0]
    struct.pack_into('<H', r, 120, (u & ~(7 << 7)) | (seta << 7))
    return bytes(r)


def comprimir_exato(raw, alvo):
    """Stream zlib VÁLIDO e COMPLETO com exatamente `alvo` bytes (sem lixo depois do fim).

    Teste de 09/10/2026: completar o bloco com zeros depois do fim do zlib deixou o jogo em
    loading infinito. Aqui o ajuste é feito DENTRO do stream:
      corpo = zlib comprimido terminando em Z_SYNC_FLUSH (alinhado em byte, sem bloco final)
      + n blocos 'stored' vazios (00 00 00 ff ff = 5 bytes cada, não finais)
      + bloco final vazio: fixo (03 00, 2 bytes) ou stored (01 00 00 ff ff, 5 bytes)
      + adler32 (4 bytes, big-endian) dos dados.
    Com os dois tipos de final, cobre 2 dos 5 restos; os outros vêm variando nível/memória/cortes.
    """
    adler = struct.pack('>I', zlib.adler32(raw))
    finais = (b'\x03\x00', b'\x01\x00\x00\xff\xff')
    vazio = b'\x00\x00\x00\xff\xff'
    cortes = [None] + [len(raw) * i // 32 for i in range(1, 32)]
    for lvl in (9, 8, 7, 6):
        for mem in (9, 8):
            for corte in cortes:
                c = zlib.compressobj(lvl, zlib.DEFLATED, 15, mem)
                if corte is None:
                    corpo = c.compress(raw) + c.flush(zlib.Z_SYNC_FLUSH)
                else:
                    corpo = (c.compress(raw[:corte]) + c.flush(zlib.Z_SYNC_FLUSH) +
                             c.compress(raw[corte:]) + c.flush(zlib.Z_SYNC_FLUSH))
                for fin in finais:
                    falta = alvo - len(corpo) - len(fin) - 4
                    if falta < 0 or falta % 5:
                        continue
                    x = corpo + vazio * (falta // 5) + fin + adler
                    z = zlib.decompressobj()
                    try:
                        ok = z.decompress(x) == raw and z.eof and not z.unused_data
                    except zlib.error:
                        ok = False
                    if ok and len(x) == alvo:
                        return x
    raise RuntimeError('não consegui comprimir no tamanho exato')


def regravar(d, mudancas):
    """Devolve uma cópia do data.dat com registros de jogador substituídos.

    mudancas: {(registro, id): novo registro de 156 bytes}.
    Cada bloco alterado é recomprimido com EXATAMENTE o tamanho comprimido original (ver comprimir_exato),
    então os cabeçalhos e todo o resto do save ficam exatamente no mesmo lugar.
    """
    d = bytearray(d)
    bls = blocos(bytes(d))
    b = bytearray(b''.join(r for _, _, r in bls))
    pos = {}
    for o in range(FIRST, len(b) - REC + 1, REC):
        pos[struct.unpack_from('<II', b, o)] = o
    for k, novo in mudancas.items():
        assert len(novo) == REC and struct.unpack_from('<II', novo, 0) == k, k
        b[pos[k]:pos[k] + REC] = novo
    ini = 0
    for o, used, raw in bls:
        fim = ini + len(raw)
        novo_raw = bytes(b[ini:fim])
        if novo_raw != raw:
            x = comprimir_exato(novo_raw, used)
            assert len(x) == used
            d[o:o + used] = x
        ini = fim
    return bytes(d)


def ler_save(path):
    """Atalho: caminho do data.dat descriptografado -> {(registro, id): campos}."""
    d = open(path, 'rb').read()
    return {k: campos(r) for k, r in registros(blob(d)).items()}
