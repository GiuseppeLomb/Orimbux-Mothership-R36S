# Help for every section: hold SELECT anywhere -> controls + a tip. First visit -> a short tutorial card.
import random

from engine import C, W, H

# key -> (title, what it is, [steps for the first visit], [(button, action)], [tips])
# Every music app shares: SELECT tap = Bridge, hold SELECT = this help, START tap = next app, hold START = music menu.
HELP = {
    "bridge": ("MOTHERSHIP", "O menu da nave: escolhe uma app.",
               ["Esq/dir muda de categoria: MÚSICA, JOGOS e SISTEMA.", "Cima/baixo escolhe a app, A entra.",
                "A MISSÃO à esquerda ensina-te o caminho, passo a passo."],
               [("cima/baixo", "escolher app"), ("esq/dir", "categoria"), ("A", "entrar"),
                ("SELECT", "segura: ajuda em qualquer app"), ("START", "segura: menu da música"),
                ("SELECT+START", "sair da nave")],
               ["As apps de MÚSICA estão por ordem: 1 tempo, 2 ritmo, 3 sons, 4 ao vivo... segue os números.",
                "O teu Xeno Pet aparece no canto: se precisar de algo, vês aqui."]),
    "intro": ("ORIMBUX MOTHERSHIP", "A nave das apps de música e jogos.", [],
              [("START / A", "embarcar"), ("esq/dir", "mudar o ambiente da música")],
              ["Há 5 ambientes: melancólico, alegre, energético, triste e zangado. Um calha ao acaso."]),
    "reactor": ("LOOP REACTOR", "8 pads de loops e sons, sempre no tempo da nave.",
                ["Cada botão (setas e X/Y/A/B) é um pad: carrega para tocar.",
                 "Os loops entram no início do compasso; carrega outra vez para parar.",
                 "L1/R1 troca de banco: há 13, de HIP HOP a ROCK, mais os teus ritmos (FORGE) e fatias (CHOP)."],
                [("setas + X/Y/A/B", "8 pads"), ("L1/R1", "banco"), ("L2", "parar tudo"),
                 ("R2", "segura: som abafado"), ("analogico dir.", "volume"),
                 ("SELECT+cima/baixo", "BPM"), ("SELECT+A", "gravar sessão")],
                ["Banco FORGE = os teus ritmos do Beat Forge, banco CHOP = as tuas fatias do Abductor.",
                 "Liga o Beat Forge e volta aqui: o ritmo continua a tocar por baixo dos loops."]),
    "forge_grid": ("BEAT FORGE · GRELHA", "Caixa de ritmos: 8 pistas, até 32 passos.",
                   ["Setas movem o cursor, A liga um passo, B põe a tocar.",
                    "L2 troca de modo: GRELHA, CONSTRUTOR (ritmos prontos) e ARRANJO (música inteira).",
                    "Segura R2 para mudar o som, o tom e o volume da pista."],
                   [("setas", "cursor"), ("A", "liga/desliga passo"), ("B", "tocar/parar"), ("X", "força"),
                    ("Y", "rajada 1-4"), ("L1/R1", "padrão A-H"), ("L2", "modo"),
                    ("R2+esq/dir", "som"), ("R2+cima/baixo", "tom"), ("R2+X/Y", "volume"),
                    ("R2+A / R2+B", "pan / silenciar"), ("R2+L2", "solo"), ("R2+L1/R1", "passos 8-32"),
                    ("SELECT+L2/R2", "desfazer/refazer"), ("SELECT+X", "padrão para o Reactor"),
                    ("SELECT+Y", "copiar padrão"), ("SELECT+R1", "probabilidade"),
                    ("SELECT+esq/dir", "swing"), ("SELECT+L1", "2x: apagar")],
                   ["Os teus sons: põe .wav em ports/mothership/samples, ou usa gravações e fatias.",
                    "Rajada x3 nos pratos no fim do compasso = rolls de trap.",
                    "Probabilidade 50% num prato dá vida ao ritmo: nunca toca igual."]),
    "forge_build": ("BEAT FORGE · CONSTRUTOR", "Ritmos prontos por estilo, pista a pista.",
                    ["Esq/dir escolhe o estilo: o BPM, o swing e os sons ajustam-se sozinhos.",
                     "Cima/baixo escolhe a pista e A troca a variação dessa pista.",
                     "X lança o dado: tudo ao acaso. Depois afina na GRELHA (L2)."],
                    [("esq/dir", "estilo"), ("cima/baixo", "pista"), ("A / Y", "variação seguinte/anterior"),
                     ("X", "dado: tudo ao acaso"), ("B", "tocar/parar"), ("L1/R1", "padrão de destino"),
                     ("L2", "modo"), ("SELECT+L2/R2", "desfazer/refazer")],
                    ["Cria A com um estilo, copia para B e muda só os pratos: tens uma variação.",
                     "O construtor escreve no padrão que está no ecrã: o que lá estava pode ser desfeito."]),
    "forge_song": ("BEAT FORGE · ARRANJO", "Junta padrões numa música inteira.",
                   ["Cada bloco é um padrão. Esq/dir anda nos blocos, cima/baixo muda a letra.",
                    "A insere um bloco, Y apaga. X liga o modo MÚSICA.",
                    "SELECT+X exporta: a música aparece no Beat Duel e no Twin Decks."],
                   [("esq/dir", "bloco"), ("cima/baixo", "padrão do bloco"), ("A", "inserir bloco"),
                    ("Y", "apagar bloco"), ("X", "modo música"), ("B", "tocar/parar"), ("L2", "modo"),
                    ("SELECT+X", "exportar música"), ("SELECT+L2/R2", "desfazer/refazer")],
                   ["Estrutura clássica: A A B B A A C B (intro, verso, refrão...).",
                    "A música exportada já traz pista para o Beat Duel."]),
    "xeno": ("XENO SYNTH", "Um teclado alien: cada botão é uma nota da escala, não há notas erradas.",
             ["Toca com as setas e com X/Y/A/B.", "L1/R1 sobe ou desce a oitava.",
              "Analógico esquerdo dobra a nota, o direito muda o filtro."],
             [("setas + X/Y/A/B", "notas"), ("L1/R1", "oitava"), ("L2", "segurar notas"), ("R2", "acorde"),
              ("analogico esq.", "dobrar a nota"), ("analogico dir.", "filtro"), ("SELECT+esq/dir", "onda"),
              ("SELECT+cima/baixo", "escala"), ("SELECT+A", "gravar sessão")],
             ["Toca por cima do Beat Forge: o ritmo continua quando mudas de app.",
              "Notas seguradas numa sessão viram notas longas no Beat Duel."]),
    "pulsar": ("PULSAR", "O coração da nave: o BPM daqui manda em todas as apps.",
               ["Esq/dir muda o BPM, um a um.", "Ou carrega A ao ritmo de uma música para o descobrir.",
                "B liga o clique do metrónomo."],
               [("esq/dir", "BPM"), ("A", "bater o tempo"), ("cima/baixo", "compasso"), ("X", "subdivisão"),
                ("B", "clique on/off")],
               ["90 BPM = hip hop, 120-128 = house, 140 = trap, 170-174 = drum & bass."]),
    "abductor_rec": ("ABDUCTOR · GRAVAR", "Grava a tua voz ou sons com um micro USB.",
                     ["A grava e para.", "Sem micro? R1 leva-te ao CORTAR, que corta qualquer música."],
                     [("A", "gravar/parar"), ("X", "ouvir"), ("B", "parar de ouvir"), ("Y", "mandar para um pad"),
                      ("cima/baixo", "entrada"), ("L1/R1", "GRAVAR / CORTAR / TOCAR")],
                     ["Depois de gravar, R1 abre logo a gravação no CORTAR."]),
    "abductor_cut": ("ABDUCTOR · CORTAR", "Corta uma música ou gravação em fatias.",
                     ["A escolhe o ficheiro.", "L2 encaixa a janela em 1, 2 ou 4 compassos.",
                      "Cima/baixo escolhe um marcador, esq/dir move-o. Y ouve a fatia."],
                     [("A", "ouvir janela / escolher"), ("cima/baixo", "marcador"), ("esq/dir", "mover"),
                      ("R2", "segura: mover fino"), ("X", "4/8/16 fatias"), ("Y", "ouvir fatia"),
                      ("L2", "janela 1/2/4 compassos"), ("B", "outro ficheiro"), ("SELECT+L2/R2", "desfazer/refazer"),
                      ("SELECT+X", "fatias para o Reactor"), ("SELECT+Y", "uma fatia de cada vez")],
                     ["Põe cada marcador mesmo antes do ataque do som: as fatias ficam secas e no tempo."]),
    "abductor_play": ("ABDUCTOR · TOCAR", "As fatias nos 8 botões.",
                      ["Toca com as setas e com X/Y/A/B.", "Com 16 fatias, L2/R2 muda de página."],
                      [("setas + X/Y/A/B", "fatias"), ("L2/R2", "página"), ("SELECT+Y", "uma de cada vez"),
                       ("SELECT+A", "gravar sessão"), ("SELECT+X", "fatias para o Reactor"),
                       ("SELECT+L2/R2", "desfazer/refazer")],
                      ["Uma fatia de cada vez (SELECT+Y) soa como uma MPC."]),
    "warp": ("WARP FLOOR", "Ouve as tuas músicas com luzes e passagem automática.",
             ["Copia músicas ou música de jogos (.spc .nsf .vgm...) para ports/mothership/music.",
              "A música do menu da consola (pasta bgmusic) também aparece aqui.",
              "A toca e pausa, esq/dir muda de faixa."],
             [("A", "tocar/pausa"), ("esq/dir", "faixa"), ("X", "aleatório"), ("B", "parar")],
             ["Cada música é convertida quando a escolhes; as mais antigas saem da cache se faltar espaço."]),
    "decks": ("TWIN DECKS", "Dois leitores de DJ para misturar a ouvido.",
              ["SELECT+L1 carrega o deck A, SELECT+R1 o deck B.", "L1/R1 põe cada um a tocar.",
               "Iguala o tempo com o pitch e passa de um para o outro com o analógico esquerdo."],
              [("L1 / R1", "tocar A / B"), ("L2 / R2", "cue A / B"), ("cima/baixo", "pitch A"), ("X / B", "pitch B"),
               ("esq/dir", "empurrar A"), ("Y / A", "empurrar B"), ("analogico esq.", "crossfader e filtro A"),
               ("analogico dir.", "filtro B"), ("L3 / R3", "filtro ao centro"), ("SELECT+L1/R1", "carregar"),
               ("SELECT+cima / X", "bater o BPM A / B"), ("SELECT+Y", "SYNC"), ("SELECT+A", "ouvir o cue"),
               ("START", "segura e Y: gravar a mistura")],
              ["Filtro para baixo abafa o som, para cima tira os graves.",
               "Truque de DJ: tira os graves da música que entra e devolve-os no 1 do compasso."]),
    "orimbox": ("ORIMBOX", "Uma tripulação de 7 aliens que canta e faz beatbox: tu escolhes o som de cada um.",
                ["Escolhe um som em baixo (esq/dir) e carrega A: um alien canta-o.",
                 "Tudo toca a tempo e no mesmo tom: qualquer mistura soa bem.",
                 "Cima vai para o palco: A silencia, X solo, B tira o som.",
                 "5 SEGREDOS: certas combinações de sons dão um coro bónus."],
                [("esq/dir", "escolher som / alien"), ("L1/R1", "grupo de sons"), ("A", "dar som / silenciar"),
                 ("B", "tirar som"), ("X", "solo (no palco)"), ("cima/baixo", "palco / sons"), ("Y", "mistura ao acaso"),
                 ("L2", "palco vazio"), ("START", "gravar a mistura")],
                ["Grava com START: a mistura aparece no BEAT DUEL e no TWIN DECKS.",
                 "Pista de segredo: três sons que combinam pelo nome do segredo... e a tripulação completa.",
                 "Os sons usam samples livres (CC0) do Sonic Pi e da VCSL; as vozes são sintetizadas."]),
    "quiz": ("DISCO VOADOR", "Concurso de música: sozinho até ao Disco de Diamante, ou em FESTA até 10 jogadores.",
             ["JOGAR: 15 perguntas, do fácil ao especialista. As 5 e 10 são patamares garantidos.",
              "FESTA: escolhe quantos jogadores (2 a 10) e as rondas. Passem a consola: cada um responde à sua.",
              "Setas escolhem a resposta, A responde. X ouve outra vez o som da pergunta."],
             [("setas", "escolher resposta"), ("A", "responder / confirmar"), ("X", "ouvir outra vez"),
              ("L1", "ajuda 50:50"), ("R1", "sondagem da tripulação"), ("L2", "pergunta ao Xeno"),
              ("B", "desistir / voltar")],
             ["Na FESTA, responder depressa dá pontos extra; as perguntas difíceis valem mais.",
              "Cada ajuda só se usa uma vez por jogo (as ajudas são só no modo JOGAR).",
              "No TREINO LIVRE as perguntas ficam mais difíceis se acertares seguidas.",
              "Acordes alegres são maiores, tristes são menores."]),
    "vox": ("VOX NEBULA", "Canta com efeitos (micro USB).",
            ["Liga os auscultadores e o micro.", "R2 liga o micro.", "Cada botão é um efeito."],
            [("R2", "micro on/off"), ("setas + X/Y/A/B", "efeitos"), ("L2", "eco por cima"), ("L1/R1", "ganho"),
             ("SELECT+cima/baixo", "corta ruído"), ("SELECT+A", "gravar sessão")],
            ["Sem auscultadores o micro apanha a coluna e apita.",
             "HANGAR > BUFFER AUDIO 512 baixa o atraso (reinicia a app)."]),
    "pet": ("XENO PET", "O teu bicho alien: vive 30 dias.",
            ["Esq/dir escolhe a ação, A faz.", "Quando aparece um balão, ele precisa dessa coisa."],
            [("esq/dir", "ação"), ("A", "fazer"), ("Y", "no Estado: memorial")],
            ["Ele continua a viver com a consola desligada.", "Cuida bem dele em criança: decide a forma adulta."]),
    "voidrunner": ("VOID RUNNER", "A tua música é o nível: foge do Grave e das hordas que crescem com o ritmo.",
                   ["Escolhe a música (cima/baixo) e o mundo (esq/dir).",
                    "Setas ou analógico para mover: as armas disparam sozinhas, mais com a música alta.",
                    "O GRAVE puxa-te: começa fraco e cresce com a música. A ou B = dash.",
                    "Nos DROPS: onda, armas a 150% e um BAÚ. Aguenta até ao fim da música."],
                   [("setas", "mover"), ("A / B", "dash"), ("START", "pausa e a tua build"),
                    ("Y", "no nível: trocar cartas"), ("X", "no nível: banir carta")],
                   ["Cristais de cores valem mais XP: azul no nível 5, verde 10, dourado 15, rubi 21, prisma 28.",
                    "Os baús melhoram o que já tens e trazem as evoluções primeiro.",
                    "Músicas curtas dão mais XP: dá para evoluir na mesma.",
                    "Arma no nível 5 + o passivo certo = carta de EVOLUÇÃO.",
                    "O baixo do Grave chega a quase todo o mapa: longe é só uma brisa, perto puxa a sério.",
                    "Logo a seguir a um DROP caem muito mais cristais raros.",
                    "Se ficar lento: pausa > INIMIGOS: MENOS."]),
    "beatduel": ("BEAT DUEL", "Jogo de ritmo a dois na mesma consola.",
                 ["Escolhe a música e carrega A. X muda o modo.", "DUELO: um jogador usa as setas, o outro Y B X A.",
                  "FRENTE A FRENTE: consola deitada entre os dois, cada um vê a sua metade direita.",
                  "Notas longas: mantém carregado até ao fim."],
                 [("cima/baixo", "música"), ("esq/dir", "dificuldade"), ("X", "modo"), ("A", "jogar"),
                  ("Y", "editor de pista"), ("L1", "acertar o atraso do som"), ("START", "sair do jogo")],
                 ["Acerta o atraso (L1) uma vez: as notas ficam certas com o teu som.",
                  "As tuas sessões do Loop Reactor, Xeno Synth, Beat Forge e Abductor aparecem aqui."]),
    "trailer": ("TRAILER", "A apresentação da nave.", [], [("A / B / START", "sair")],
                ["As imagens das apps são reais: capturadas da própria app."]),
    "credits": ("CRÉDITOS", "Quem construiu a nave.", [], [("cima/baixo", "mais rápido / devagar"),
                                                           ("A / B / START", "sair")],
                ["Os sons vêm da biblioteca do Sonic Pi (CC0)."]),
    "hangar": ("HANGAR", "Ajustes da nave.",
               ["Cima/baixo escolhe, esq/dir ou A muda."],
               [("cima/baixo", "escolher"), ("esq/dir / A", "mudar"), ("B", "voltar")],
               ["BUFFER AUDIO 512 = menos atraso, mais trabalho para a consola (reinicia a app).",
                "REVER TUTORIAIS mostra outra vez os cartões da primeira vez."]),
}


def key_for(app):
    name = app.cur_name
    cur = app.cur
    if name == "abductor":
        return "abductor_" + getattr(cur, "panel", "rec")
    if name == "forge":
        return "forge_" + getattr(cur, "mode", "grid")
    return name


class Help(object):
    def __init__(self, app):
        self.app = app
        self.tip = {}
        self.tutorial = None

    # ---- first visit
    def maybe_tutorial(self, name):
        self.tutorial = None
        cfg = self.app.cfg
        seen = cfg.setdefault("seen", [])
        k = key_for(self.app) if name in ("forge", "abductor") else name
        h = HELP.get(k)
        if h and h[2] and k not in seen:
            self.tutorial = k

    def dismiss(self):
        if self.tutorial:
            self.app.cfg.setdefault("seen", []).append(self.tutorial)
            self.tutorial = None
            self.app.save_cfg()

    # ---- drawing
    def draw_overlay(self, g):
        import ui
        k = key_for(self.app)
        h = HELP.get(k)
        if not h:
            return
        title, about, _, keys, tips = h
        if k not in self.tip:
            self.tip[k] = random.choice(tips) if tips else ""
        cat, step, col = ui.where(self.app.cur_name)
        g.rect(0, 0, W, H, C["void"], 150)
        x, y, w = 20, 34, W - 40
        two = len(keys) > 8
        rows = (len(keys) + 1) // 2 if two else len(keys)
        tip_lines = ui.wrap(g, ui.SMALL, self.tip[k], w - 60) if self.tip[k] else []
        ab = ui.wrap(g, ui.SMALL, about, w - 32)
        extra = 18 * (len(ab) - 1)
        hh = min(H - 50, 92 + extra + rows * 26 + (24 + len(tip_lines) * 18 if tip_lines else 0) + 12)
        ui.panel(g, x, y, w, hh, col, "AJUDA")
        tf = ui.TITLE if g.tw(ui.TITLE, title) <= w - 32 else ui.HEAD
        g.text(tf, title, x + 16, y + 14 + (6 if tf != ui.TITLE else 0), C["text"])
        for i, l in enumerate(ab):
            g.text(ui.SMALL, l, x + 16, y + 54 + i * 18, C["soft"])
        cy = y + 82 + extra
        colw = (w - 32) // 2 if two else w - 32
        cols = [keys[:rows], keys[rows:]] if two else [keys]
        for ci, items in enumerate(cols):
            bx = x + 16 + ci * colw
            kw = max([ui.keys_w(g, b) for b, _ in items] + [0]) + 10
            kw = min(kw, colw - 96)
            for r, (b, act) in enumerate(items):
                yy = cy + r * 26
                ui.keys(g, b, bx, yy)
                g.text(ui.SMALL, ui.fit(g, ui.SMALL, act, colw - kw - 10), bx + kw, yy - 1, C["text"])
        if tip_lines:
            ty = cy + rows * 26 + 8
            g.rect(x + 16, ty - 4, w - 32, 1, C["hullhi"])
            g.text(ui.SMALL, "★", x + 18, ty + 2, C["orange"])
            for i, line in enumerate(tip_lines):
                g.text(ui.SMALL, line, x + 40, ty + 2 + i * 18, C["orange"])
        cw = g.tw(ui.SMALL, "solta SELECT para fechar") + 16
        ui.box(g, x + w - cw - 14, y - 9, cw, 18, C["hull"])
        g.text(ui.SMALL, "solta SELECT para fechar", x + w - 22, y - 9, C["muted"], 255, "right")

    def draw_tutorial(self, g, t):
        import ui
        h = HELP.get(self.tutorial)
        if not h:
            return
        title, about, steps, _, _ = h
        cat, step, col = ui.where(self.app.cur_name)
        x, y, w = 36, 60, W - 72
        lines = []
        for i, s in enumerate(steps):
            for j, l in enumerate(ui.wrap(g, ui.BODY, s, w - 84)):
                lines.append(("%d" % (i + 1) if j == 0 else "", l))
        ab = ui.wrap(g, ui.SMALL, about, w - 40)
        extra = 18 * (len(ab) - 1)
        hh = 150 + extra + len(lines) * 30
        y = max(8, min(y, H - 8 - hh))
        g.rect(0, 0, W, H, C["void"], 170)
        ui.panel(g, x, y, w, hh, col, "PRIMEIRA VEZ AQUI")
        tf = ui.TITLE if g.tw(ui.TITLE, title) <= w - 40 else ui.HEAD
        g.text(tf, title, x + 20, y + 16 + (6 if tf != ui.TITLE else 0), col)
        for i, l in enumerate(ab):
            g.text(ui.SMALL, l, x + 20, y + 58 + i * 18, C["soft"])
        for i, (n, l) in enumerate(lines):
            yy = y + 92 + extra + i * 30
            if n:
                ui.box(g, x + 20, yy + 2, 26, 26, col)
                g.text(ui.HEAD, n, x + 33, yy - 1, C["void"], 255, "center")
            g.text(ui.BODY, l, x + 60, yy, C["text"])
        by = y + hh - 44
        xe = ui.keys(g, "SELECT", x + 20, by + 2)
        g.text(ui.SMALL, "segura a qualquer momento: todos os controlos", xe + 6, by + 1, C["muted"])
        if int(t * 2) % 2 == 0:
            g.text(ui.SMALL, "carrega num botão para começar", x + w // 2, by + 22, C["cyan"], 255, "center")
