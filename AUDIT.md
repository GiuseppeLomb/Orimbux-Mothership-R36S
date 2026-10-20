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
- Reprodução (`repro_saves.py`, sobre o `main`):

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
  é reescrito (`repro_saves.py`: `REWRITTEN`).
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

### Verificado e sem problemas

- **Texturas SDL:** as do nível do Void Runner, do logótipo da intro, do trailer, dos créditos e das vistas do
  FRENTE A FRENTE são destruídas ao sair; as que ficam (fontes, scanlines, sprites, texturas partilhadas do Void
  Runner) são criadas uma vez e reutilizadas.
- **Acesso ao misturador:** as listas `voices`, `streams` e `synth` só são alteradas com o `mixer.lock`; as leituras
  sem lock na thread principal são só de leitura (seguras com o GIL). A única corrida encontrada é a M4.
- **Caminhos:** usam sempre `os.path.join`; a app corre igual a partir do `.bat` (que define `PYTHONUTF8=1`).
- **Python 3.7:** nada a corrigir.
