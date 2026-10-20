# Auditoria de código: Orimbux Mothership (ramo `audit`)

Auditoria ao código de `ports/mothership/*.py`, `tools/*.py` e dos dois lançadores, feita a partir do commit
`6841748` do `main`. O objetivo foi encontrar e corrigir bugs, fragilidades e código mau sem mudar a app:
o que ela faz, o aspeto, os textos, os sons, os controlos e o equilíbrio dos jogos.

Ambiente de medição: Windows 11, Python 3.14.7, pysdl2-dll 2.32.10, audioop-lts 0.2.2, Pillow e numpy só para
as ferramentas. Os testes correm headless (`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`). Não há uma R36S
neste ambiente: o que depende do ArkOS está assinalado com **[consola]**.

---

## 1. Estado de partida (medido antes de qualquer alteração)

### pyflakes

`pyflakes ports/mothership/*.py tools/*.py`: **10 avisos**, todos em `tools/`:

```
tools/bd_face_test.py:3:1: 'time' imported but unused
tools/bd_test.py:3:1: 'glob' imported but unused
tools/build_extra.py:235:9: undefined name 'build_kid_font'
tools/decks_test.py:2:1: 'json' imported but unused
tools/decks_test.py:2:1: 'shutil' imported but unused
tools/quiz_party_test.py:3:1: 'time' imported but unused
tools/render_trailer.py:29:5: 'credits' imported but unused
tools/v17_test.py:3:1: 'json' imported but unused
tools/v18_test.py:19:1: 'credits as crm' imported but unused
tools/v19_test.py:2:1: 'ctypes' imported but unused
```

O pysdl2 incluído (`lib/sdl2`) dá 484 avisos de pyflakes: é código de terceiros e não lhe mexi.

### Compatibilidade com Python 3.7

Não há Python 3.7 para Windows no `uv` nem neste PC, por isso a verificação é estática: `vermin -t=3.7-`
diz que a app precisa de **Python 3.6** no mínimo (as ferramentas, 3.7). Nenhum walrus, `match`, `dict | dict`,
`removeprefix`, genéricos em runtime ou `f"{x=}"`.

### Testes headless

| Teste | Resultado | Notas |
|---|---|---|
| `v19_test.py` | passa | deixa uma sessão gravada em `recordings/` |
| `v18_test.py` | passa | |
| `v17_test.py` | **falha** | `AssertionError` na linha 104: no Windows não consegue apagar a gravação que está a tocar (ver A4) |
| `forge_test.py` | passa | |
| `decks_test.py` | passa | |
| `chop_test.py` | passa | |
| `vox_test.py` | passa | |
| `bd_test.py` | passa | |
| `bd_face_test.py` | passa | |
| `quiz_party_test.py` | passa | |
| `vr_gems_test.py` | passa | |
| `vr_test.py OUT 0,2,5` | passa | ver tempos abaixo |
| `text_bounds.py` | corre | 9 textos fora do ecrã, todos no TRAILER (números `1`..`8` e `▶` a deslizar para dentro: é a animação) |

### Tempos de partida (PC)

`vr_test.py OUT 0,2,5` (o bot joga os mundos 1, 3 e 6):

| Mundo | update | draw |
|---|---|---|
| 1 | 0.32 ms | 1.03 ms |
| 3 | 0.41 ms | 1.08 ms |
| 6 | 0.39 ms | 1.16 ms |

`tools/perf_test.py` (ferramenta nova desta auditoria, corrida sobre o `main`): ms por frame, melhor de 5 × 200
frames, e o custo de um callback de áudio com carga típica (Beat Forge + 2 loops + acorde no Xeno + uma música).

| Ecrã | ms/frame |
|---|---|
| bridge | 1.92 |
| forge (a tocar) | 1.67 |
| reactor (2 loops) | 1.61 |
| hangar | 1.07 |
| quiz | 1.80 |
| pet | 0.94 |
| xeno | 2.13 |
| **áudio** `render(1024)` | mediana 268 µs, hash do áudio `6b54d35091d19331` |

Um perfil (`cProfile`) dos ecrãs mostra para onde vai o tempo: `Gfx.text` (uma chamada SDL por letra, 8 campos
ctypes escritos por letra), `Gfx.rects` (um `SDL_Rect` Python criado por retângulo) e `ui.tokens` (9 expressões
regulares por cada tecla desenhada, em cada frame). No Void Runner, `Gfx.text` é o maior custo do draw.

---

## 2. Falhas encontradas

Cada falha tem o ficheiro e a linha (no commit `6841748`), o problema, como se reproduz e a correção proposta.

### Crítica

**C1. Um ficheiro guardado com conteúdo inesperado impede a app de arrancar ou de abrir uma secção.**
- Onde: `forge.py:118-152` (`load`), `quiz.py:61-71`, `pet.py:203-210` e `pet.py:228`, `app.py:59-65` (`load_cfg`)
  com `app.py:1907-1908`, `missions.py:27`, `help.py:198`, `voidrunner.py:1892-1899` e `2005`,
  `beatduel.py:555-559`.
- Problema: os ficheiros são lidos com `json.load` e usados sem validar tipos nem domínios. Um JSON válido mas
  com a forma errada rebenta no arranque (`App.__init__` constrói todas as secções), ou mais tarde a desenhar.
- Reprodução (sobre o `main`; os mesmos casos estão em `tools/saves_test.py`):

  | Ficheiro | Conteúdo | Resultado |
  |---|---|---|
  | `forge.json` | `[]` | crash no arranque: `'list' object has no attribute 'get'` |
  | `forge.json` | `{"tracks": [{"vol": "x", "pan": 7}]}` | crash no arranque: `int('x')` |
  | `forge.json` | um passo `[9, 1]` em vez de `[vel, rajada, prob]` | crash ao tocar: `not enough values to unpack` |
  | `quiz.json` | `[1, 2]` | crash no arranque |
  | `quiz.json` | `{"party_cfg": {"n": 50}}` | crash na FESTA: `IndexError` |
  | `pet.json` | `{"last_seen": "ontem"}` | crash no arranque: `float('ontem')` |
  | `pet.json` | `{"form": "dragon"}` | crash na ponte em cada frame: `KeyError: 'dragon'` |
  | `config.json` | `{"volume": "alto", "bpm": "x"}` | crash no arranque |
  | `config.json` | `{"joy_map": {"a": [1]}}` | crash no arranque |
  | `vr_save.json` | `{"unlocked": "6"}` | crash ao abrir o Void Runner |
  | `bd_save.json` | `[]` | crash ao abrir o Beat Duel |

- Correção: validar o tipo e o domínio de cada campo ao ler, campo a campo; o que vem da própria app passa
  intacto, só o que rebentaria é substituído pelo valor por omissão.

**C2. Um ficheiro guardado ilegível é substituído em silêncio pelos valores por omissão.**
- Onde: `pet.py:203-210`, `forge.py:121-124`, `quiz.py:61-64`, `voidrunner.py:1893-1899`, `beatduel.py:556-559`,
  `app.py:61-64`.
- Problema: quando o JSON não se lê (truncado, cheio de zeros depois de um corte de energia), a app arranca com os
  valores por omissão e grava-os por cima na primeira gravação. O `pet.json` estragado passa a um ovo novo e o pet
  antigo desaparece ao fim de 30 s; o `forge.json` passa aos padrões de demonstração.
- Reprodução: `pet.json` truncado a meio, ou 200 bytes `\0`, ou `forge.json` truncado: a app arranca e o ficheiro
  é reescrito na gravação seguinte (casos em `tools/saves_test.py`).
- Correção: antes de recomeçar, guardar o ficheiro estragado ao lado com o nome `<ficheiro>.bad-AAAAMMDD-HHMMSS`
  (nunca se apaga nada). O mesmo quando a validação de C1 tem de corrigir algum campo.

**C3. Escrita não atómica de ficheiros guardados.**
- Onde: `config.json` (`app.py:1965`), `vr_save.json` (`voidrunner.py:1903`), `bd_save.json` (`beatduel.py:563`),
  as pistas e sessões reescritas no editor do Beat Duel (`beatduel.py:797-802`), os metadados das sessões gravadas
  (`app.py:421`), da música exportada pelo Forge (`forge.py:493`) e dos loops do Forge (`app.py:229`).
- Problema: `json.dump(obj, open(path, "w"))` trunca o ficheiro e só depois escreve; um crash, o cartão cheio ou um
  corte de energia a meio deixam-no vazio ou truncado (e cai em C2). Os que já usavam `.tmp` + `os.replace`
  (`pet.py:212-220`, `forge.py:158-165`, `quiz.py:88-93`, `earlab.py:79-85`, `songscan.py:77`) não fazem `fsync`
  antes do `os.replace`, e três deles nem fecham o ficheiro explicitamente antes de o substituir
  (`forge.py:161`, `quiz.py:90`, `earlab.py:82`).
- Reprodução: simular a falha a meio da escrita (exceção dentro do `json.dump`): o ficheiro antigo fica truncado.
- Correção: uma função única, `engine.write_json`, que escreve `<ficheiro>.tmp`, faz `flush` e `fsync` e só depois
  `os.replace`. O `fsync` fica nas gravações importantes (sair da app, sair de uma secção, fim de um jogo, pistas e
  sessões) e sai nas gravações periódicas (pet a cada 30 s, Forge 2 s depois de uma edição) para um cartão SD lento
  nunca parar um frame a meio de um jogo de ritmo.

### Alta

**A1. Thread de áudio: uma fonte que falha cala tudo.**
- Onde: `engine.py:805-864` (`Mixer.render` e `_callback`).
- Problema: uma exceção em qualquer voz ou stream faz perder o buffer inteiro (silêncio). A fonte que falhou fica na
  lista; se voltar a falhar, o som fica mudo para sempre e cada callback acrescenta uma linha ao `log.txt`
  (~43 por segundo, no cartão SD). O log é aberto sem ser fechado (`engine.py:862`).
- Reprodução: uma voz cujo `read()` levanta exceção põe todas as chamadas seguintes de `render()` a falhar. Casos
  reais: `PlaylistVoice._wrap` (`engine.py:712-724`) quando um ficheiro da lista desaparece; um WAV do jogador
  truncado a meio de uma amostra num formato que não é 44,1 kHz/16 bits/estéreo, aberto pelo Beat Duel ou pelas
  GRAVAÇÕES (`audioop.error: not a whole number of frames`).
- Correção: isolar cada fonte: a que falha é retirada (e fechada) e as outras continuam a tocar; o log regista só a
  primeira ocorrência de cada erro.

**A2. Ao sair por erro, nada é gravado e o gravador pode ficar a correr.**
- Onde: `app.py:2149-2174` (`App.run`).
- Problema: as gravações de saída (config, pet, Forge, sessão em curso) e o fim do `arecord` só acontecem no caminho
  normal. Uma exceção numa secção salta tudo: o pet perde até 30 s, o Forge até 2 s de edições, e um `arecord` do
  ABDUCTOR a gravar para ficheiro fica órfão a encher o cartão **[consola]**. No caminho normal, se `rec.stop()`
  falhar (cartão cheio) as gravações seguintes também não acontecem.
- Correção: `try/finally` à volta do ciclo, com cada passo de encerramento protegido à parte.

**A3. Relógio de parede no ciclo principal, no transporte sem áudio e no relógio do Beat Duel.**
- Onde: `app.py:2150-2166`, `engine.py:876-885` (`Mixer.pump`), `beatduel.py:99-106` (`Clock.frames`).
- Problema: `time.time()` salta quando a hora do sistema muda. Para trás: `SDL_Delay` recebe um valor enorme e a app
  congela. Para a frente, sem dispositivo de áudio: `pump()` tenta renderizar de uma vez todo o áudio do salto e
  congela. A R36S não tem pilha de relógio e acerta a hora pelo NTP quando o Wi-Fi liga **[consola]**.
- Reprodução: com `mixer.ok = False`, avançar `time.time` 10⁷ s faz `pump()` querer renderizar ~4×10⁸ buffers.
- Correção: `time.perf_counter()` (monotónico e de alta resolução, existe no Python 3.7) nesses três sítios. O Xeno
  Pet continua a usar a hora real, de propósito.

**A4. Windows: apagar uma gravação que está a tocar falha sempre.**
- Onde: `recmgr.py:101-113`.
- Problema: o `stop()` só pede um fade; o stream continua com o ficheiro aberto e no Windows o `os.remove` falha
  ("Não consegui apagar."). No Linux funciona. É a falha do `v17_test.py`.
- Correção: se o `os.remove` falhar e o ficheiro for o que está a tocar, fechar o stream e tentar outra vez
  (no Linux nada muda).

### Média

**M1. O lançador da consola extrai qualquer `mothership*.zip` por inteiro.**
- Onde: `ports/Orimbux Mothership.sh:31`.
- Problema: o `zipfile` do Python já neutraliza `..` e caminhos absolutos (verificado: `../../evil.txt` cai dentro
  de `ports/`). Mas um zip que traga `mothership/pet.json`, `config.json` ou `recordings/...` (por exemplo feito à mão
  a partir de uma cópia do PC) apaga os jogos guardados da consola, ao contrário do que o lançador promete, e os
  membros fora de `mothership/` vão parar a outras pastas de `ports/`.
- Correção: extrair só membros dentro de `mothership/`, nunca os ficheiros e pastas do jogador, e recusar nomes
  absolutos ou com `..` explicitamente. Os zips feitos pelo `package.py` continuam a instalar exatamente os mesmos
  ficheiros.

**M2. Ficheiros que ficam abertos.**
- Onde: `decks.py:66-91` (`_peaks` não fecha o WAV quando se troca de faixa a meio do cálculo, nem quando há
  exceção: no Windows o ficheiro fica bloqueado), `songscan.py:33-48` (o WAV fica aberto se a leitura falhar),
  `recmgr.py:36-38`, e quase todos os `json.load(open(...))` (por exemplo `app.py:62`, `app.py:209`, `forge.py:122`,
  `pet.py:205`, `beatduel.py:49`). No CPython fecham-se pela contagem de referências, mas não é garantido.
- Correção: `with` e `try/finally`; uma função `engine.read_json` (que também aceita o BOM do Bloco de Notas).

**M3. A análise de música do Void Runner continua depois de cancelada.**
- Onde: `voidrunner.py:2046-2048` e `2076-2078`, `songscan.py:175-196`.
- Problema: cancelar (B ou SELECT) só larga a referência; a thread continua. Cancelar e escolher outra música põe
  duas análises a competir pelo CPU.
- Correção: `Scanner.cancel()`, verificado entre ficheiros.

**M4. Corrida no VOX NEBULA.**
- Onde: `vox.py:191-195`.
- Problema: o stream verifica `v.mic` e usa-o na linha seguinte; se o micro for desligado entre as duas (thread
  principal), há um `AttributeError` na thread de áudio e perde-se um buffer.
- Correção: guardar a referência numa variável local.

**M5. Trabalho repetido em cada frame e no callback de áudio.**
- `ui.tokens` corre 9 `re.sub` por cada tecla desenhada, em cada frame (`ui.py:115-138`).
- `Gfx.text` escreve 8 campos ctypes por letra (`engine.py:182-202`); `Gfx.rects` cria um `SDL_Rect` Python por
  retângulo antes de o copiar para o array (`engine.py:159-165`).
- `ui.wrap` e `ui.fit` refazem a quebra de linhas do mesmo texto em cada frame (`ui.py:44-74`).
- `Timeline.onsets` percorre todos os onsets da música em cada frame do Void Runner (`songscan.py:158-159`).
- Misturador: multiplicações por exatamente 1,0 (`engine.py:833`, e os ganhos estáveis em `SynthVoice.read` e
  `StreamVoice.read`).
- Correção: caches e saltar as multiplicações por 1,0, com resultado idêntico: píxeis comparados byte a byte e
  áudio comparado por hash.

**M6. `tools/build_extra.py` rebenta e, se não rebentasse, estragava as fontes.**
- Onde: `tools/build_extra.py:222-235`.
- Problema: o bloco `if __name__ == "__main__"` chama `build_kid_font()` antes de a função estar definida
  (`NameError`, o aviso de pyflakes). Se fosse alcançada, regeneraria `k16`..`k48` com um atlas antigo só ASCII, sem
  acentos e sem o campo `top`, por cima das fontes atuais feitas por `build_font.py`.
- Correção: retirar o construtor de fontes obsoleto; `font` passa a indicar `build_font.py`.

**M7. Outros ficheiros do jogador lidos sem validação** (encontrada durante as correções).
- Onde: `beatduel.py:45-87` (`find_songs`: sessões `recordings/session_*.json` e `*.chart.json`), `decks.py:250-263`,
  `recmgr.py:42-47`, `app.py:206-211` (o `forge_X.json` de um loop do Forge), `songscan.py:28-31` (a cache).
- Problema: as notas, o título, o bpm e os "beats" eram usados tal como vinham do ficheiro.
- Reprodução (sobre o `main`): uma sessão com a nota `[3.0, 7]` rebenta o Beat Duel ao jogar (`IndexError`); uma
  sessão com `"title": 5` rebenta a lista de músicas (`TypeError`); `"beats": 0` num loop do Forge rebenta o
  reamostrador ao tocar o pad; uma cache de análise com a forma errada torna a música impossível de jogar.
- Correção: validar as notas (`[tempo, pista 0-3]` ou `[tempo, pista, duração]`) e descartar as danificadas, saltar
  sessões sem `file`, dar valores seguros ao título e ao bpm, analisar outra vez uma cache danificada.

### Baixa

**B1. Imports não usados** em `tools/` (os 9 restantes avisos de pyflakes).

**B2. Código morto:** `app._old_header` e `app._old_footer` (`app.py:76-117`) e `help.wrap` (`help.py:174-185`)
não são chamados em lado nenhum. A parte de secção do `earlab.py` (menu, desenho, estatísticas) também não é usada,
mas fica: o `quiz.py` usa os sons dele.

**B3. Testes que deixam lixo:** `v19_test.py` grava uma sessão em `recordings/` e não a apaga; `v17_test.py` deixa um
`rec_*.wav` quando falha.

**B4. `package.py`** tem a sua própria lista de ficheiros do jogador e empacotaria um `*.tmp` ou `*.bad-*` que
estivesse na pasta (uma gravação interrompida).

**B5.** `engine.py:27` lê o `config.json` ao importar sem `with` nem codificação; `load_cfg` não aceita o BOM UTF-8.

**B6. `chop_test.py` é instável** (encontrada na verificação final): em headless o relógio do misturador só anda com
o tempo real, e dois toques gravados podiam cair no mesmo bloco de áudio e fundir-se numa nota. No `main` falhou 2
vezes em 5; com os frames mais rápidos, mais vezes.

### Verificado e sem problemas

- **Texturas SDL:** as do nível do Void Runner, do logótipo da intro, do trailer, dos créditos e das vistas do
  FRENTE A FRENTE são destruídas ao sair; as que ficam (fontes, scanlines, sprites, texturas partilhadas do Void
  Runner) são criadas uma vez e reutilizadas.
- **Acesso ao misturador:** as listas `voices`, `streams` e `synth` só são alteradas com o `mixer.lock`; as leituras
  sem lock na thread principal são só de leitura (seguras com o GIL). A única corrida encontrada é a M4.
- **Caminhos:** usam sempre `os.path.join`; a app corre igual a partir do `.bat` (que define `PYTHONUTF8=1`).
- **Python 3.7:** nada a corrigir.

---

## 3. O que foi corrigido

Um commit por assunto, cada um com o teste que o prova em `tools/`. Os testes novos falham no `main` (reproduzem as
falhas) e passam neste ramo.

| Falha | O que mudou | Commit | Teste |
|---|---|---|---|
| C3 | `engine.write_json`: escreve `<ficheiro>.tmp`, `flush`, `fsync`, `os.replace`, em todas as gravações. Sem `fsync` nas periódicas (pet a cada 30 s, gravação automática do Forge, Void Runner a meio do jogo, cache) para um cartão lento nunca parar um frame | `a78e44c` | `saves_test.py` |
| C2 | `engine.load_save`: um ficheiro ilegível passa a `<ficheiro>.bad-AAAAMMDD-HHMMSS` antes de a app recomeçar | `56955b8` | `saves_test.py` |
| C1 | validação campo a campo de `config`, `pet`, `forge`, `quiz`, `vr_save` e `bd_save`; quando corrige algo, guarda primeiro uma cópia `.bad` do original | `08f4d83` | `saves_test.py` (9 casos, ida e volta, formatos antigos) |
| M7 | notas, títulos, bpm, "beats" e cache validados ao ler | `cae1082` | `files_test.py` |
| A1 | cada fonte de som lida à parte: a que falha é marcada, fechada e retirada; cada erro vai ao log uma vez | `2f8b462` | `audio_test.py` |
| A2 | `try/finally` no ciclo; `shutdown()` com cada passo protegido | `933f854` | `robust_test.py` |
| A3 | `time.perf_counter()` no ciclo, em `Mixer.pump` e no relógio do Beat Duel | `c67f366` (+ `af532a3`: os relógios falsos dos testes) | `robust_test.py` |
| A4 | se o `os.remove` falhar, fecha o stream desse ficheiro e tenta outra vez | `6098de9` | `v17_test.py` passa a passar |
| M1 + B4 | o lançador só extrai `mothership/`, nunca os ficheiros do jogador; `package.py` deixa de fora `*.tmp`, `*.bad-*`, `missions.json` | `87ec129` | `launcher_test.py` (inclui o `.sh` inteiro no bash) |
| M2 + B5 | `with`/`try-finally` no Twin Decks, no Warp e nas leituras; `os.replace` no Warp | `b146a99` | `robust_test.py` |
| M3 | `Scanner.cancel()` | `b3f748f` | `robust_test.py` |
| M4 | o micro é lido uma vez por callback | `0fbad12` | `audio_test.py` |
| M5 | texto: retângulos das letras em cache; retângulos: array `c_int` direto | `14dce76` | `perf_equal_test.py`, `screens_test.py` |
| M5 | cache de `ui.tokens`, `ui.wrap`, `ui.fit` | `e76e8c8` | `perf_equal_test.py` |
| M5 | onsets do Void Runner por bisseção (com o filtro antigo como recurso) | `fde89ef` | `perf_equal_test.py`, `vr_test.py` |
| M5 | misturador: saltar multiplicações por exatamente 1,0 | `70fd697` | `perf_equal_test.py`, hash do áudio no `perf_test.py` |
| M6 | construtor de fontes obsoleto retirado do `build_extra.py` | `a779954` | `tools_test.py` |
| B1 + B3 | imports não usados; `v19_test` apaga a sessão que grava | `4131a10` | pyflakes, `v19_test.py` |
| B2 | código morto retirado | `f401efc` | `screens_test.py` |
| B6 | `chop_test` faz o áudio avançar em passos fixos | `5f08944` | `chop_test.py` (6 em 6) |

Ferramentas novas de medição: `tools/perf_test.py` (`84b62f6`) e `tools/screens_test.py` (`f24370f`).

**O que pode notar-se depois destas correções.** Nada no aspeto, nos textos, nos sons, nos controlos ou no equilíbrio:
os 50 ecrãs são idênticos ao `main`, o áudio tem o mesmo hash e o bot do `vr_test` termina os três mundos com os mesmos
abatidos e estados. As únicas diferenças visíveis são as correções de falhas, e mais uma: um ficheiro guardado estragado
deixa um `<nome>.bad-...` ao lado, que nunca é apagado. Um `forge.json` no formato v1 também é guardado assim, uma vez,
antes de ser convertido.

---

## 4. Resultados antes e depois

### Análise estática

| | `main` | `audit` |
|---|---|---|
| pyflakes (`ports/mothership/*.py tools/*.py`) | 10 avisos | **0** |
| vermin, Python mínimo da app | 3.6 | 3.6 |
| vermin, Python mínimo das ferramentas | 3.7 | 3.7 |

### Testes

| Teste | `main` | `audit` |
|---|---|---|
| `v19_test`, `v18_test`, `forge_test`, `decks_test`, `vox_test`, `bd_test`, `bd_face_test`, `quiz_party_test`, `vr_gems_test`, `vr_test 0,2,5` | passam | passam |
| `v17_test` | **falha** (Windows, A4) | passa |
| `chop_test` | passa às vezes (falhou 2 em 5, B6) | passa sempre (6 em 6) |
| `text_bounds` | 9 textos fora do ecrã (animação do trailer) | os mesmos 9 |
| `saves_test`, `files_test`, `audio_test`, `robust_test`, `launcher_test`, `perf_equal_test`, `tools_test` (novos) | falham (reproduzem as falhas) | passam |
| `screens_test` (novo) | 50 hashes | **os mesmos 50 hashes** |

### Tempos (PC)

Medidos lado a lado com o `main`, em rondas alternadas, ficando o melhor de 3. O PC mudou de estado de energia durante
a sessão (o `main` mediu 1,92 ms na ponte no início e 1,48 ms no fim), por isso só a comparação lado a lado é válida.

`tools/perf_test.py` (ms por frame; áudio: um callback de 1024 amostras com carga típica):

| Ecrã | `main` | `audit` | |
|---|---|---|---|
| bridge | 1.48 | 1.12 | -24% |
| forge (a tocar) | 1.31 | 1.01 | -23% |
| reactor (2 loops) | 1.37 | 1.13 | -18% |
| hangar | 0.92 | 0.66 | -28% |
| quiz | 1.55 | 1.14 | -27% |
| pet | 0.81 | 0.67 | -18% |
| xeno | 1.77 | 1.39 | -22% |
| **áudio** `render(1024)` | 231 µs | 210 µs | -9%, hash `6b54d35091d19331` igual |

`tools/vr_test.py OUT 0,2,5`:

| Mundo | update `main` → `audit` | draw `main` → `audit` | resultado (igual nos dois) |
|---|---|---|---|
| 1 | 0.23 → 0.20 ms | 0.73 → 0.64 ms | colapso, 1240 abatidos |
| 3 | 0.27 → 0.24 ms | 0.71 → 0.60 ms | morto, 314 abatidos |
| 6 | 0.27 → 0.23 ms | 0.80 → 0.73 ms | morto, 718 abatidos |

Custo novo: a validação do `forge.json` acrescenta cerca de 1 ms ao arranque no PC (1,7 ms contra 0,8 ms), com um
caminho rápido para os passos já válidos.

---

## 5. O que ficou por fazer e porquê

- **Nada foi testado na R36S** (não há consola neste ambiente). Dependem do ArkOS:
  - o `os.replace` sobre um ficheiro que já existe no cartão (exFAT ou FAT). O `pet.json` já o usava em versões
    anteriores, por isso deve funcionar;
  - o custo do `fsync` num cartão SD lento. Foi por isso que ficou fora das gravações periódicas;
  - o `arecord` do ABDUCTOR e do VOX (micro USB) e o seu fim no encerramento;
  - o relógio sem pilha e o acerto da hora pelo NTP (simulado nos testes);
  - o lançador `.sh`: testado no Git Bash com um `python3` falso, mas não no bash da consola;
  - os ganhos de desempenho, medidos no PC. Como são custos de Python, a proporção no RK3326 deve ser parecida, mas não
    está medida.
- **Python 3.7 real:** só verificação estática (vermin). Não há Python 3.7 para Windows aqui. Nada do que foi escrito
  usa sintaxe posterior a 3.6.
- **Temporizadores de interface** em `time.time()`: ver P3. Mudar ~100 sítios é um diff grande para um caso raro.
- **Desenhar o texto numa só chamada SDL** (`SDL_RenderGeometry`) exige SDL 2.0.18+, que não é garantido no ArkOS.
- **`bd_scores.json`** aparece na lista de ficheiros de jogos guardados, mas nenhum código o lê ou escreve. Só existe nas
  listas de exclusão do `package.py` e do lançador, que o protegem.

---

## 6. Propostas que mudariam a app (não aplicadas)

**P1. Cache do Warp Floor com nomes repetidos.** `music/a/song.mp3` e `music/b/song.mp3` partilham
`music/.cache/song.mp3.wav` (`Warp.cache_path` em `app.py`, `find_songs` em `beatduel.py`), por isso toca a música
errada. Corrigir muda o nome da cache dos ficheiros em subpastas, que seriam convertidos outra vez, uma vez.

**P2. Comando no PC.** Desligar e voltar a ligar o comando não o reabre: `engine.Input` só abre comandos se não houver
nenhum aberto, e `SDL_JOYDEVICEREMOVED` não é tratado.

**P3. Temporizadores de interface** (suspense do quiz, colapso do Void Runner, toasts, repetição das setas) usam
`time.time()`. Com um salto da hora para trás podem ficar parados até a hora "alcançar". A correção é passar esses
sítios para um relógio monotónico.

**P4. Beat Duel:** a nota é julgada no momento em que o evento é processado. Usar o timestamp do evento SDL tornaria o
julgamento independente de um frame lento.

**P5. ABDUCTOR:** o medidor de nível lê o fim do ficheiro em gravação em cada frame (`Abductor.update`). Ler a cada 3
frames pouparia leituras no cartão, mas o medidor mexeria menos vezes.

**P6. Gestor de GRAVAÇÕES:** chama `os.statvfs` em cada frame (`RecManager.draw`). Bastaria fazê-lo ao abrir e ao
apagar.

**P7. Entrar no Beat Duel com o micro ligado** desliga-o com o `mixer.lock` apanhado (`proc.wait` até 1 s), o que pode
dar um corte breve de som. A correção é parar o micro fora do lock.

**P8. Twin Decks no Windows:** apagar no gestor um ficheiro que está carregado num deck falha ("Não consegui apagar"),
porque o deck o tem aberto. Descarregar o deck mudaria o que o jogador vê.

**P9. Lançador:** fora da consola, a limpeza final de `/dev/tty0` faz o script terminar com código 1. É inofensivo (o
EmulationStation ignora o código), e pôr `2>/dev/null` antes do `>` silenciava-o.

---

## 7. Como repetir as verificações

```bash
pyflakes ports/mothership/*.py tools/*.py
python3 tools/saves_test.py && python3 tools/files_test.py && python3 tools/audio_test.py
python3 tools/robust_test.py && python3 tools/launcher_test.py && python3 tools/perf_equal_test.py
python3 tools/tools_test.py
python3 tools/perf_test.py                      # tempos e hash do áudio
python3 tools/screens_test.py > audit.txt       # e no main: python3 tools/screens_test.py OUTRA/ports/mothership
python3 tools/vr_test.py /tmp/vr 0,2,5
```

Os testes antigos (`v17_test` a `v19_test`, `forge_test`, `decks_test`, `chop_test`, `vox_test`, `bd_test`,
`bd_face_test`, `quiz_party_test`, `vr_gems_test`, `text_bounds`) correm como antes, com
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`.
