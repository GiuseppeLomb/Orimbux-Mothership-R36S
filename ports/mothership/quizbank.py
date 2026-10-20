# DISCO VOADOR - the question bank. Difficulty: 1 FÁCIL, 2 MÉDIO, 3 DIFÍCIL, 4 ESPECIALISTA.
# TRIVIA rows: (level, category, question, right answer, wrong, wrong, wrong).
# THEORY generators build endless music-theory questions that are always correct (computed, not typed).
import random

LEVELS = ["FÁCIL", "MÉDIO", "DIFÍCIL", "ESPECIALISTA"]

TRIVIA = [
    # ------------------------------------------------------------ geral / no dia a dia
    (1, "GERAL", "Cantar em grupo chama-se cantar em...", "Coro", "Solo", "Silêncio", "Eco"),
    (1, "GERAL", "Uma música só com instrumentos, sem voz, é...", "Instrumental", "A capella", "Um dueto", "Um karaoke"),
    (1, "GERAL", "Cantar por cima de uma música sem a voz original chama-se...", "Karaoke", "Ópera", "Rap", "Recital"),
    (1, "GERAL", "O refrão é a parte da música que...", "Se repete e fica no ouvido", "Só aparece uma vez",
     "Não tem música", "Está sempre no fim"),
    (1, "GERAL", "Um dueto é cantado por...", "Duas pessoas", "Uma pessoa", "Três pessoas", "Um coro inteiro"),
    (1, "GERAL", "Que aparelho aumenta o som de uma guitarra elétrica?", "Amplificador", "Microfone", "Metrónomo",
     "Afinador"),
    (1, "GERAL", "BPM quer dizer...", "Batidas por minuto", "Baixo por música", "Bateria por medida",
     "Bits por minuto"),
    (1, "GERAL", "Para que serve um metrónomo?", "Marcar o tempo", "Afinar guitarras", "Gravar a voz",
     "Misturar músicas"),
    (1, "GERAL", "Um 'loop' é...", "Um pedaço de música que se repete", "Uma nota muito aguda",
     "Um tipo de microfone", "O volume no máximo"),
    (1, "GERAL", "Que aparelho transforma a voz em sinal elétrico?", "Microfone", "Altifalante", "Amplificador",
     "Metrónomo"),
    (1, "GERAL", "Quantos músicos tem um quarteto?", "4", "3", "5", "8"),
    (2, "GERAL", "Uma 'demo' é...", "Uma gravação de amostra, antes do disco final", "Um concerto ao vivo",
     "Um videoclip", "Uma letra escrita"),
    (2, "GERAL", "Um 'single' é...", "Uma música lançada sozinha", "Um álbum duplo", "Um instrumento de uma corda",
     "Um concerto a solo"),
    (2, "GERAL", "Um 'EP' tem normalmente...", "Menos músicas do que um álbum", "Uma só música",
     "Mais de 30 músicas", "Só vídeos"),
    (2, "GERAL", "Fazer um 'cover' é...", "Tocar uma música de outro artista", "Desenhar a capa do disco",
     "Cantar sem microfone", "Gravar só a bateria"),
    (2, "GERAL", "Um concerto 'unplugged' é...", "Acústico", "Ao ar livre", "Sem público", "Só com DJs"),
    (2, "GERAL", "Um BPM de 60 quer dizer...", "Uma batida por segundo", "60 batidas por segundo",
     "Uma batida por hora", "Duas batidas por segundo"),
    (2, "GERAL", "O que é um remix?", "Uma nova versão de uma música", "Uma música ao vivo", "Um instrumento",
     "Um microfone"),
    (2, "GERAL", "Música 'a capella' é cantada...", "Sem instrumentos", "Com orquestra", "Só com piano",
     "Muito depressa"),
    (3, "GERAL", "O 'riff' é...", "Uma frase curta que se repete", "O nome do baixista", "Um tipo de corda",
     "O fim de um concerto"),
    (3, "GERAL", "Uma 'jam session' é...", "Tocar juntos de improviso", "Gravar com pauta em estúdio",
     "Um concurso de canto", "Uma aula de solfejo"),
    (3, "GERAL", "A 'setlist' é...", "A lista de músicas de um concerto", "O preço dos bilhetes",
     "A letra de uma música", "O nome do palco"),
    (3, "GERAL", "Um 'mashup' é...", "Várias músicas misturadas numa só", "Um instrumento de sopro",
     "Uma pausa longa", "Um erro de gravação"),
    (3, "GERAL", "Usar pedaços de gravações noutras músicas chama-se...", "Sampling", "Tuning", "Mastering",
     "Panning"),
    (3, "GERAL", "A masterização é...", "O último passo, que acerta o som final", "Escrever a letra",
     "Ensaiar a banda", "Imprimir os discos"),

    # ------------------------------------------------------------ instrumentos
    (1, "INSTRUMENTOS", "Qual destes é um instrumento de cordas?", "Violino", "Trompete", "Flauta", "Tambor"),
    (1, "INSTRUMENTOS", "Qual destes instrumentos tem teclas?", "Piano", "Guitarra", "Bateria", "Violino"),
    (1, "INSTRUMENTOS", "Quantas cordas tem uma guitarra normal?", "6", "4", "5", "12"),
    (1, "INSTRUMENTOS", "Qual destes é um instrumento de sopro?", "Saxofone", "Violoncelo", "Harpa", "Xilofone"),
    (1, "INSTRUMENTOS", "Que instrumento se toca com baquetas?", "Bateria", "Flauta", "Violino", "Guitarra"),
    (1, "INSTRUMENTOS", "Que instrumento se toca com um arco?", "Violino", "Guitarra", "Piano", "Trompete"),
    (1, "INSTRUMENTOS", "Qual destes é um instrumento de percussão?", "Tambor", "Clarinete", "Violino", "Trombone"),
    (1, "INSTRUMENTOS", "O ukulele parece uma guitarra pequena com quantas cordas?", "4", "6", "8", "2"),
    (1, "INSTRUMENTOS", "A harpa é um instrumento de...", "Cordas", "Sopro", "Percussão", "Teclas"),
    (1, "INSTRUMENTOS", "A bateria é um conjunto de instrumentos de...", "Percussão", "Cordas", "Sopro", "Teclas"),
    (1, "INSTRUMENTOS", "Que instrumento usa um DJ para tocar discos de vinil?", "Gira-discos", "Piano", "Violino",
     "Megafone"),
    (1, "INSTRUMENTOS", "Que instrumento de metal se toca com uma varinha e faz 'tim'?", "Triângulo", "Tuba",
     "Bombo", "Contrabaixo"),
    (1, "INSTRUMENTOS", "Qual destes instrumentos tem pedais para os pés?", "Piano", "Flauta", "Violino", "Ukulele"),
    (2, "INSTRUMENTOS", "Quantas teclas tem um piano normal?", "88", "61", "100", "76"),
    (2, "INSTRUMENTOS", "Que instrumento de 4 cordas toca as notas graves numa banda?", "Baixo", "Violino",
     "Ukulele", "Bandolim"),
    (2, "INSTRUMENTOS", "Um sintetizador produz som...", "Eletronicamente", "Com cordas", "Soprando", "Com peles"),
    (2, "INSTRUMENTOS", "Que instrumento português de 12 cordas acompanha o fado?", "Guitarra portuguesa",
     "Cavaquinho", "Bandolim", "Viola da gamba"),
    (2, "INSTRUMENTOS", "Que instrumento tem fole e teclas?", "Acordeão", "Órgão de tubos", "Gaita de foles",
     "Piano"),
    (2, "INSTRUMENTOS", "Qual é o instrumento de metal mais grave da orquestra?", "Tuba", "Trompete", "Trompa",
     "Flauta"),
    (2, "INSTRUMENTOS", "Que instrumento de sopro tem uma vara que desliza?", "Trombone", "Trompete", "Tuba",
     "Clarinete"),
    (2, "INSTRUMENTOS", "O oboé e o clarinete pertencem aos...", "Sopros de madeira", "Sopros de metal",
     "Instrumentos de cordas", "Instrumentos de percussão"),
    (2, "INSTRUMENTOS", "A flauta transversal é de metal, mas é da família das...", "Madeiras", "Metais", "Cordas",
     "Percussões"),
    (2, "INSTRUMENTOS", "Que instrumento de teclas, típico das igrejas, toca com tubos e ar?", "Órgão de tubos",
     "Cravo", "Acordeão", "Sintetizador"),
    (2, "INSTRUMENTOS", "No piano, as cordas são...", "Batidas por martelos", "Beliscadas", "Tocadas com arco",
     "Sopradas"),
    (2, "INSTRUMENTOS", "Que instrumento tem lâminas de madeira tocadas com baquetas?", "Xilofone", "Timbales",
     "Pratos", "Pandeireta"),
    (2, "INSTRUMENTOS", "O cajón é um instrumento de percussão em forma de...", "Caixa", "Tubo", "Anel", "Sino"),
    (2, "INSTRUMENTOS", "Que instrumento indiano de cordas ficou famoso com Ravi Shankar?", "Sitar", "Banjo",
     "Bouzouki", "Koto"),
    (2, "INSTRUMENTOS", "O banjo é muito usado em que estilo americano?", "Bluegrass", "Reggae", "Techno", "Ópera"),
    (2, "INSTRUMENTOS", "A gaita de foles também é tradicional em que região portuguesa?", "Trás-os-Montes",
     "Algarve", "Madeira", "Alentejo"),
    (2, "INSTRUMENTOS", "Que pedal de guitarra faz o som 'uá-uá'?", "Wah-wah", "Delay", "Chorus", "Looper"),
    (3, "INSTRUMENTOS", "O maior instrumento da família do violino é o...", "Contrabaixo", "Violoncelo", "Viola",
     "Violino"),
    (3, "INSTRUMENTOS", "Quantas cordas tem um cavaquinho?", "4", "6", "8", "12"),
    (3, "INSTRUMENTOS", "No cravo, as cordas são...", "Beliscadas", "Batidas com martelos", "Tocadas com arco",
     "Sopradas"),
    (3, "INSTRUMENTOS", "Que instrumento, um pouco maior que o violino, também se toca ao ombro?", "Viola d'arco",
     "Violoncelo", "Contrabaixo", "Bandolim"),
    (3, "INSTRUMENTOS", "O theremin toca-se...", "Sem lhe tocar, mexendo as mãos no ar", "Soprando",
     "Com um arco", "Com baquetas"),
    (3, "INSTRUMENTOS", "Que instrumento de teclas foi o antepassado do piano no Barroco?", "Cravo",
     "Órgão Hammond", "Melódica", "Celesta"),
    (3, "INSTRUMENTOS", "A TR-808 é uma famosa caixa de ritmos de que marca?", "Roland", "Yamaha", "Korg", "Casio"),
    (3, "INSTRUMENTOS", "O Minimoog é um famoso...", "Sintetizador", "Microfone", "Amplificador", "Gira-discos"),
    (3, "INSTRUMENTOS", "O didgeridoo é um instrumento de sopro de que país?", "Austrália", "Índia", "Peru",
     "Quénia"),
    (3, "INSTRUMENTOS", "Os tambores de aço ('steel drums') nasceram em...", "Trinidad e Tobago", "Jamaica", "Cuba",
     "Brasil"),
    (3, "INSTRUMENTOS", "Que instrumento havaiano descende de instrumentos da Madeira?", "Ukulele", "Banjo",
     "Bandolim", "Charango"),
    (3, "INSTRUMENTOS", "Que instrumento de sopro usa uma palheta dupla?", "Oboé", "Clarinete", "Saxofone",
     "Flauta"),
    (3, "INSTRUMENTOS", "Em que instrumento de metal o músico põe a mão dentro da campânula?", "Trompa", "Tuba",
     "Trombone", "Trompete"),
    (3, "INSTRUMENTOS", "O 'talk box' faz a guitarra soar como...", "Uma voz a falar", "Um piano", "Uma bateria",
     "Um coro de igreja"),
    (4, "INSTRUMENTOS", "O Hammond B-3 é um famoso...", "Órgão elétrico", "Sintetizador modular",
     "Piano de cauda", "Pedal de guitarra"),
    (4, "INSTRUMENTOS", "Quantas cordas tem uma harpa de concerto?", "47", "24", "36", "60"),
    (4, "INSTRUMENTOS", "Quantos pedais tem uma harpa de concerto?", "7", "3", "2", "12"),
    (4, "INSTRUMENTOS", "O mellotron tocava sons gravados em...", "Fitas magnéticas", "Discos de vinil",
     "Cartões perfurados", "Chips de memória"),
    (4, "INSTRUMENTOS", "O contrabaixo de orquestra tem normalmente quantas cordas?", "4", "5", "6", "3"),

    # ------------------------------------------------------------ teoria e notação
    (1, "TEORIA", "Quantas linhas tem uma pauta musical?", "5", "4", "6", "7"),
    (1, "TEORIA", "Que nota vem logo a seguir ao DÓ?", "RÉ", "MI", "SI", "FÁ"),
    (1, "TEORIA", "Num compasso de 4/4, quantas batidas há?", "4", "3", "2", "8"),
    (1, "TEORIA", "Qual destas NÃO é uma nota musical?", "PÁ", "RÉ", "MI", "FÁ"),
    (1, "TEORIA", "Várias notas tocadas ao mesmo tempo formam...", "Um acorde", "Uma escala", "Uma pausa",
     "Um compasso"),
    (1, "TEORIA", "Um acorde maior costuma soar...", "Alegre", "Triste", "Assustador", "Sem som nenhum"),
    (1, "TEORIA", "Uma pausa na pauta quer dizer...", "Silêncio", "Tocar mais forte", "Repetir", "Acabar a música"),
    (1, "TEORIA", "Quantas notas básicas há, do DÓ ao SI?", "7", "5", "8", "12"),
    (2, "TEORIA", "A valsa tem um ritmo de quantos tempos?", "3", "4", "2", "5"),
    (2, "TEORIA", "Quantos meios-tons tem uma oitava?", "12", "8", "7", "10"),
    (2, "TEORIA", "Que acorde formam as notas DÓ, MI e SOL?", "Dó maior", "Dó menor", "Lá menor", "Sol maior"),
    (2, "TEORIA", "Que nota fica entre DÓ e RÉ?", "Dó sustenido", "Si bemol", "Mi", "Fá sustenido"),
    (2, "TEORIA", "Quantas teclas pretas há em cada oitava do piano?", "5", "7", "6", "4"),
    (2, "TEORIA", "Tocar as notas de um acorde uma de cada vez chama-se...", "Arpejo", "Glissando", "Staccato",
     "Acorde fechado"),
    (2, "TEORIA", "Quantas notas tem uma escala pentatónica?", "5", "7", "6", "8"),
    (2, "TEORIA", "O sustenido faz a nota...", "Subir meio-tom", "Descer meio-tom", "Ficar mais curta",
     "Ficar em silêncio"),
    (2, "TEORIA", "O bemol faz a nota...", "Descer meio-tom", "Subir meio-tom", "Durar mais", "Ficar mais forte"),
    (2, "TEORIA", "A linha vertical que separa os compassos chama-se...", "Barra de compasso", "Clave", "Pauta",
     "Fermata"),
    (2, "TEORIA", "Dois pontos antes de uma barra dupla mandam...", "Repetir", "Parar", "Acelerar",
     "Tocar mais baixo"),
    (2, "TEORIA", "Uma colcheia vale metade de uma...", "Semínima", "Mínima", "Semibreve", "Semicolcheia"),
    (2, "TEORIA", "Que intervalo há entre DÓ e SOL?", "Quinta perfeita", "Terceira maior", "Quarta perfeita",
     "Sexta maior"),
    (3, "TEORIA", "Que acorde formam as notas LÁ, DÓ e MI?", "Lá menor", "Lá maior", "Dó maior", "Mi menor"),
    (3, "TEORIA", "A clave de sol mostra na pauta onde fica a nota...", "SOL", "DÓ", "FÁ", "LÁ"),
    (3, "TEORIA", "A clave de fá usa-se para notas...", "Graves", "Agudas", "Só de percussão", "Só cantadas"),
    (3, "TEORIA", "Uma escala maior segue os intervalos...", "Tom, tom, meio, tom, tom, tom, meio",
     "Tom, meio, tom, tom, meio, tom, tom", "Meio-tom entre todas as notas", "Tom entre todas as notas"),
    (3, "TEORIA", "Um ponto a seguir a uma nota aumenta a duração em...", "Metade", "O dobro", "Um quarto",
     "Nada"),
    (3, "TEORIA", "Uma tercina são...", "3 notas no tempo de 2", "3 compassos seguidos", "3 notas iguais",
     "Uma nota 3 vezes mais longa"),
    (3, "TEORIA", "Um acorde de sétima tem quantas notas?", "4", "3", "5", "2"),
    (3, "TEORIA", "A escala de LÁ menor natural tem...", "Nenhum sustenido nem bemol", "Só sustenidos",
     "Só bemóis", "Duas notas"),
    (3, "TEORIA", "Uma síncope é...", "Um acento fora do tempo forte", "Uma pausa longa", "Um acorde menor",
     "Uma nota muito aguda"),
    (3, "TEORIA", "O ciclo de quintas organiza...", "As tonalidades", "Os instrumentos", "Os compassos",
     "Os andamentos"),
    (3, "TEORIA", "Que acorde formam DÓ, MI bemol e SOL?", "Dó menor", "Dó maior", "Mi bemol maior",
     "Sol menor"),
    (3, "TEORIA", "O blues clássico tem quantos compassos?", "12", "8", "16", "32"),
    (4, "TEORIA", "Um acorde diminuto é formado por...", "Duas terceiras menores", "Duas terceiras maiores",
     "Uma quarta e uma quinta", "Quintas seguidas"),
    (4, "TEORIA", "Um acorde aumentado é formado por...", "Duas terceiras maiores", "Duas terceiras menores",
     "Terceira menor e quarta", "Duas quartas"),
    (4, "TEORIA", "Quantos meios-tons tem um trítono?", "6", "5", "7", "4"),
    (4, "TEORIA", "O modo dórico é como a escala menor, mas com a...", "Sexta maior", "Sétima maior",
     "Segunda menor", "Quarta aumentada"),
    (4, "TEORIA", "O modo lídio tem a quarta...", "Aumentada", "Diminuta", "Perfeita", "Repetida"),
    (4, "TEORIA", "O modo frígio começa com um intervalo de...", "Meio-tom", "Tom", "Terceira", "Quinta"),
    (4, "TEORIA", "A progressão II-V-I é a base de muito...", "Jazz", "Fado", "Heavy metal", "Kuduro"),
    (4, "TEORIA", "O acorde construído no 5º grau de uma escala chama-se...", "Dominante", "Tónica",
     "Subdominante", "Mediante"),
    (4, "TEORIA", "Numa escala maior, o 4º grau chama-se...", "Subdominante", "Dominante", "Sensível", "Tónica"),
    (4, "TEORIA", "O 7º grau, meio-tom abaixo da tónica, chama-se...", "Sensível", "Dominante", "Mediante",
     "Supertónica"),
    (4, "TEORIA", "No ciclo de quintas, depois de DÓ (pelos sustenidos) vem...", "SOL", "FÁ", "RÉ", "MI"),

    # ------------------------------------------------------------ géneros e origens
    (1, "GÉNEROS", "O fado é música tradicional de que país?", "Portugal", "Espanha", "Brasil", "Itália"),
    (1, "GÉNEROS", "O reggae nasceu em que país?", "Jamaica", "Cuba", "Brasil", "Nigéria"),
    (1, "GÉNEROS", "O samba é típico de que país?", "Brasil", "Argentina", "México", "Portugal"),
    (1, "GÉNEROS", "O flamenco é típico de que país?", "Espanha", "Portugal", "Itália", "México"),
    (1, "GÉNEROS", "Que estilo tem DJs, batidas eletrónicas e pistas de dança?", "Música eletrónica", "Fado",
     "Ópera", "Canto gregoriano"),
    (1, "GÉNEROS", "O rap faz parte de que cultura?", "Hip hop", "Fado", "Música clássica", "Country"),
    (1, "GÉNEROS", "Que estilo é famoso por guitarras muito distorcidas e voz forte?", "Heavy metal",
     "Bossa nova", "Música de câmara", "Canto gregoriano"),
    (1, "GÉNEROS", "A ópera é teatro...", "Cantado", "Sem música", "Só dançado", "Com marionetas"),
    (1, "GÉNEROS", "O kuduro nasceu em que país?", "Angola", "Brasil", "Cabo Verde", "Moçambique"),
    (1, "GÉNEROS", "A morna é música tradicional de...", "Cabo Verde", "Angola", "Brasil", "Guiné-Bissau"),
    (2, "GÉNEROS", "Em que país nasceu o hip hop?", "Estados Unidos", "Jamaica", "Inglaterra", "França"),
    (2, "GÉNEROS", "Chiptune é música feita com sons de...", "Consolas e computadores antigos", "Uma orquestra",
     "Um coro", "Pianos de cauda"),
    (2, "GÉNEROS", "Em que década nasceu o rock and roll?", "Anos 50", "Anos 30", "Anos 70", "Anos 90"),
    (2, "GÉNEROS", "Cesária Évora, a 'diva dos pés descalços', era de...", "Cabo Verde", "Angola",
     "São Tomé e Príncipe", "Moçambique"),
    (2, "GÉNEROS", "A bossa nova nasceu em que país?", "Brasil", "Portugal", "Cuba", "Argentina"),
    (2, "GÉNEROS", "O jazz nasceu em que cidade americana?", "Nova Orleães", "Nova Iorque", "Los Angeles",
     "Seattle"),
    (2, "GÉNEROS", "O grunge nasceu em que cidade?", "Seattle", "Londres", "Miami", "Detroit"),
    (2, "GÉNEROS", "O punk rock explodiu em que década?", "Anos 70", "Anos 50", "Anos 90", "Anos 2000"),
    (2, "GÉNEROS", "Que estilo jamaicano, mais rápido, veio antes do reggae?", "Ska", "Salsa", "Cumbia",
     "Afrobeat"),
    (2, "GÉNEROS", "O K-pop é música pop de que país?", "Coreia do Sul", "Japão", "China", "Tailândia"),
    (2, "GÉNEROS", "O afrobeat foi criado por Fela Kuti, de que país?", "Nigéria", "Gana", "Senegal", "Quénia"),
    (2, "GÉNEROS", "O merengue é típico de que país?", "República Dominicana", "Brasil", "Espanha", "Colômbia"),
    (2, "GÉNEROS", "O reggaeton ganhou fama a partir de...", "Porto Rico", "Espanha", "Argentina", "Portugal"),
    (2, "GÉNEROS", "Na música house, o bombo toca...", "Em todos os tempos do compasso", "Só no início",
     "Nunca", "Só no refrão"),
    (3, "GÉNEROS", "O tango nasceu na Argentina e no...", "Uruguai", "Chile", "Peru", "Paraguai"),
    (3, "GÉNEROS", "A música house nasceu em que cidade?", "Chicago", "Paris", "Berlim", "Lisboa"),
    (3, "GÉNEROS", "O techno nasceu em que cidade?", "Detroit", "Londres", "Ibiza", "Tóquio"),
    (3, "GÉNEROS", "O drum & bass nasceu em que país?", "Reino Unido", "Brasil", "Japão", "Estados Unidos"),
    (3, "GÉNEROS", "Que estilo eletrónico anda à volta dos 170-175 BPM?", "Drum & bass", "Hip hop", "Reggae",
     "Bossa nova"),
    (3, "GÉNEROS", "O dubstep nasceu em que cidade?", "Londres", "Berlim", "Nova Iorque", "Kingston"),
    (3, "GÉNEROS", "O trap nasceu em que cidade americana?", "Atlanta", "Boston", "Seattle", "Denver"),
    (3, "GÉNEROS", "O drill nasceu em Chicago e ganhou força em...", "Londres", "Lisboa", "Paris", "Tóquio"),
    (3, "GÉNEROS", "O lo-fi hip hop é conhecido por ser...", "Calmo, com ruído de vinil", "Muito rápido",
     "Cantado em ópera", "Só com orquestra"),
    (3, "GÉNEROS", "A salsa ganhou fama em que cidade, nos anos 60 e 70?", "Nova Iorque", "Madrid", "Lisboa",
     "Buenos Aires"),
    (3, "GÉNEROS", "O gospel é música de origem...", "Religiosa", "Militar", "Desportiva", "Publicitária"),
    (3, "GÉNEROS", "O semba, antepassado da kizomba, é de que país?", "Angola", "Brasil", "Cabo Verde",
     "Moçambique"),
    (3, "GÉNEROS", "A kizomba nasceu em que país?", "Angola", "Cabo Verde", "Brasil", "Portugal"),
    (3, "GÉNEROS", "O synthwave inspira-se na música e nos filmes dos anos...", "80", "50", "2010", "20"),
    (4, "GÉNEROS", "O trip-hop ficou associado a que cidade inglesa?", "Bristol", "Liverpool", "Manchester",
     "Leeds"),
    (4, "GÉNEROS", "O acid house é famoso pelo som de que sintetizador?", "Roland TB-303", "Minimoog",
     "Yamaha DX7", "Korg M1"),
    (4, "GÉNEROS", "O baile funk nasceu em que cidade?", "Rio de Janeiro", "São Paulo", "Salvador", "Recife"),
    (4, "GÉNEROS", "O chip de som da consola NES tinha quantos canais?", "5", "2", "8", "16"),
    (4, "GÉNEROS", "Que estilo jamaicano usa muito eco e remistura faixas instrumentais?", "Dub", "Ska", "Mento",
     "Calypso"),

    # ------------------------------------------------------------ clássica
    (1, "CLÁSSICA", "Que grupo tem violinos, flautas, trompetes e um maestro?", "Orquestra", "Banda de garagem",
     "Duo", "DJ set"),
    (1, "CLÁSSICA", "Quem dirige uma orquestra?", "O maestro", "O baterista", "O DJ", "O técnico de som"),
    (2, "CLÁSSICA", "Qual destes compositores ficou surdo e continuou a compor?", "Beethoven", "Mozart", "Vivaldi",
     "Chopin"),
    (2, "CLÁSSICA", "Quem compôs 'As Quatro Estações'?", "Vivaldi", "Bach", "Mozart", "Beethoven"),
    (2, "CLÁSSICA", "Em que cidade nasceu Mozart?", "Salzburgo", "Viena", "Paris", "Roma"),
    (2, "CLÁSSICA", "Beethoven nasceu em que cidade?", "Bona", "Viena", "Berlim", "Praga"),
    (2, "CLÁSSICA", "'O Lago dos Cisnes' é um bailado de...", "Tchaikovsky", "Mozart", "Bach", "Vivaldi"),
    (2, "CLÁSSICA", "Quem compôs 'Para Elisa'?", "Beethoven", "Mozart", "Chopin", "Haydn"),
    (2, "CLÁSSICA", "'A Flauta Mágica' é uma ópera de...", "Mozart", "Verdi", "Puccini", "Wagner"),
    (2, "CLÁSSICA", "Chopin era de que país?", "Polónia", "Rússia", "Áustria", "Hungria"),
    (2, "CLÁSSICA", "'O Quebra-Nozes' é de que compositor?", "Tchaikovsky", "Stravinsky", "Rachmaninoff",
     "Prokofiev"),
    (2, "CLÁSSICA", "Johann Sebastian Bach era de que país?", "Alemanha", "Itália", "França", "Inglaterra"),
    (3, "CLÁSSICA", "Bach é um compositor de que período?", "Barroco", "Romântico", "Clássico", "Moderno"),
    (3, "CLÁSSICA", "Chopin compôs sobretudo para...", "Piano", "Orquestra", "Guitarra", "Coro"),
    (3, "CLÁSSICA", "A 9ª Sinfonia de Beethoven acaba com a famosa...", "Ode à Alegria", "Marcha Turca",
     "Primavera", "Valsa do Minuto"),
    (3, "CLÁSSICA", "'Carmen' é uma ópera de...", "Bizet", "Verdi", "Rossini", "Puccini"),
    (3, "CLÁSSICA", "Verdi era de que país?", "Itália", "Espanha", "França", "Áustria"),
    (3, "CLÁSSICA", "O 'Bolero', que repete o mesmo tema a crescer, é de...", "Ravel", "Debussy", "Satie", "Bizet"),
    (3, "CLÁSSICA", "Quem compôs 'Clair de Lune'?", "Debussy", "Ravel", "Chopin", "Liszt"),
    (3, "CLÁSSICA", "O 'Rondó alla Turca' (Marcha Turca para piano) é de...", "Mozart", "Vivaldi", "Schubert",
     "Haydn"),
    (3, "CLÁSSICA", "A 'Cavalgada das Valquírias' é de...", "Wagner", "Mozart", "Verdi", "Puccini"),
    (3, "CLÁSSICA", "Que família de compositores austríacos ficou famosa pelas valsas?", "Strauss", "Bach",
     "Mozart", "Haydn"),
    (3, "CLÁSSICA", "'O Danúbio Azul' é uma...", "Valsa", "Marcha", "Ópera", "Missa"),
    (3, "CLÁSSICA", "Uma sinfonia é escrita para...", "Orquestra", "Um só piano", "Coro sem instrumentos",
     "Banda de rock"),
    (4, "CLÁSSICA", "Vivaldi era chamado 'o padre...'", "Ruivo", "Surdo", "Cego", "Gigante"),
    (4, "CLÁSSICA", "Quantas sinfonias completou Beethoven?", "9", "5", "12", "41"),
    (4, "CLÁSSICA", "'A Sagração da Primavera', escândalo em 1913, é de...", "Stravinsky", "Debussy", "Ravel",
     "Mahler"),
    (4, "CLÁSSICA", "Que compositor é chamado 'pai da sinfonia'?", "Haydn", "Mozart", "Bach", "Handel"),
    (4, "CLÁSSICA", "'O Messias', com o famoso 'Aleluia', é de...", "Handel", "Bach", "Vivaldi", "Purcell"),
    (4, "CLÁSSICA", "As 'Gymnopédies' de Erik Satie são para...", "Piano", "Orquestra", "Órgão", "Coro"),
    (4, "CLÁSSICA", "'Pedro e o Lobo', com um instrumento por personagem, é de...", "Prokofiev", "Tchaikovsky",
     "Mussorgsky", "Rimsky-Korsakov"),
    (4, "CLÁSSICA", "'O Voo do Moscardo' é de...", "Rimsky-Korsakov", "Tchaikovsky", "Borodin", "Glinka"),
    (4, "CLÁSSICA", "Que Fernando foi um grande compositor português do século XX?", "Lopes-Graça", "Pessoa",
     "Mendes", "Namora"),

    # ------------------------------------------------------------ pop e rock
    (1, "POP & ROCK", "Michael Jackson é conhecido como o 'Rei do...'", "Pop", "Rock", "Jazz", "Fado"),
    (1, "POP & ROCK", "Elvis Presley é conhecido como o 'Rei do...'", "Rock and roll", "Pop", "Reggae", "Blues"),
    (1, "POP & ROCK", "Bob Marley ficou famoso a cantar...", "Reggae", "Fado", "Ópera", "Heavy metal"),
    (1, "POP & ROCK", "Os Beatles eram uma banda de que país?", "Inglaterra", "Estados Unidos", "Austrália",
     "Irlanda"),
    (2, "POP & ROCK", "Que instrumento tocava Jimi Hendrix?", "Guitarra", "Bateria", "Piano", "Saxofone"),
    (2, "POP & ROCK", "Freddie Mercury foi o vocalista de que banda?", "Queen", "The Beatles", "Rolling Stones",
     "U2"),
    (2, "POP & ROCK", "De que cidade eram os Beatles?", "Liverpool", "Londres", "Manchester", "Dublin"),
    (2, "POP & ROCK", "Quantos membros tinham os Beatles?", "4", "3", "5", "6"),
    (2, "POP & ROCK", "Qual destes era um dos Beatles?", "Paul McCartney", "Mick Jagger", "Freddie Mercury",
     "Bono"),
    (2, "POP & ROCK", "Mick Jagger é o vocalista dos...", "Rolling Stones", "Beatles", "Queen", "U2"),
    (2, "POP & ROCK", "Bono é o vocalista de que banda irlandesa?", "U2", "Coldplay", "Oasis", "Queen"),
    (2, "POP & ROCK", "'Bohemian Rhapsody' é uma música dos...", "Queen", "Beatles", "ABBA", "U2"),
    (2, "POP & ROCK", "Os ABBA eram de que país?", "Suécia", "Noruega", "Dinamarca", "Holanda"),
    (2, "POP & ROCK", "Que artista lançou o álbum 'Thriller'?", "Michael Jackson", "Prince", "Madonna",
     "Whitney Houston"),
    (2, "POP & ROCK", "Madonna é conhecida como a 'Rainha do...'", "Pop", "Soul", "Rock", "Country"),
    (2, "POP & ROCK", "Que banda tocava 'Smells Like Teen Spirit'?", "Nirvana", "Metallica", "Pearl Jam",
     "Green Day"),
    (2, "POP & ROCK", "Os Daft Punk eram um duo eletrónico de que país?", "França", "Alemanha", "Bélgica", "Suíça"),
    (2, "POP & ROCK", "Os Coldplay são de que país?", "Reino Unido", "Estados Unidos", "Canadá", "Austrália"),
    (2, "POP & ROCK", "Que cantora é conhecida pelos álbuns '21' e '25'?", "Adele", "Rihanna", "Beyoncé",
     "Shakira"),
    (2, "POP & ROCK", "Shakira é de que país?", "Colômbia", "México", "Espanha", "Argentina"),
    (2, "POP & ROCK", "Que DJ sueco fez 'Wake Me Up' e 'Levels'?", "Avicii", "David Guetta", "Calvin Harris",
     "Tiësto"),
    (2, "POP & ROCK", "David Guetta é um DJ de que país?", "França", "Holanda", "Suécia", "Alemanha"),
    (2, "POP & ROCK", "Elton John é famoso por tocar...", "Piano", "Bateria", "Violino", "Saxofone"),
    (3, "POP & ROCK", "Que banda gravou 'The Dark Side of the Moon'?", "Pink Floyd", "Led Zeppelin", "The Who",
     "Genesis"),
    (3, "POP & ROCK", "'Stairway to Heaven' é dos...", "Led Zeppelin", "Deep Purple", "Black Sabbath", "The Doors"),
    (3, "POP & ROCK", "Ozzy Osbourne foi o vocalista dos...", "Black Sabbath", "Iron Maiden", "AC/DC", "Metallica"),
    (3, "POP & ROCK", "Os AC/DC formaram-se em que país?", "Austrália", "Reino Unido", "Estados Unidos",
     "Nova Zelândia"),
    (3, "POP & ROCK", "Que banda tem a mascote 'Eddie' nas capas?", "Iron Maiden", "Metallica", "Megadeth",
     "Slayer"),
    (3, "POP & ROCK", "Que guitarrista dos Queen fez a sua guitarra com o pai?", "Brian May", "Eric Clapton",
     "Jimmy Page", "Slash"),
    (3, "POP & ROCK", "'Purple Rain' é de...", "Prince", "Jimi Hendrix", "David Bowie", "Stevie Wonder"),
    (3, "POP & ROCK", "Que personagem espacial criou David Bowie?", "Ziggy Stardust", "Rocket Man",
     "Captain Fantastic", "Starlord"),
    (3, "POP & ROCK", "Que cantor é conhecido como 'The Boss'?", "Bruce Springsteen", "Bon Jovi", "Elton John",
     "Billy Joel"),
    (3, "POP & ROCK", "Os Kraftwerk, pioneiros da eletrónica, são de que país?", "Alemanha", "França", "Japão",
     "Holanda"),
    (3, "POP & ROCK", "Que banda lançou 'OK Computer'?", "Radiohead", "Blur", "Oasis", "Muse"),
    (3, "POP & ROCK", "Quem canta 'Rolling in the Deep'?", "Adele", "Amy Winehouse", "Duffy", "Lana Del Rey"),
    (3, "POP & ROCK", "Amy Winehouse ficou famosa com o álbum...", "Back to Black", "Born to Die", "21",
     "Lemonade"),
    (3, "POP & ROCK", "Kurt Cobain era o vocalista dos...", "Nirvana", "Foo Fighters", "Radiohead", "Oasis"),
    (4, "POP & ROCK", "Em que ano os Beatles se separaram?", "1970", "1965", "1980", "1975"),
    (4, "POP & ROCK", "Que festival de 1969 juntou meio milhão de pessoas numa quinta?", "Woodstock",
     "Glastonbury", "Coachella", "Lollapalooza"),
    (4, "POP & ROCK", "O 'Clube dos 27' é de músicos que morreram com...", "27 anos", "27 discos de ouro",
     "27 concertos", "27 dias de tour"),
    (4, "POP & ROCK", "Qual destes NÃO fez parte dos Beatles?", "Brian Jones", "George Harrison", "Ringo Starr",
     "John Lennon"),
    (4, "POP & ROCK", "Que álbum dos Pink Floyd tem um prisma na capa?", "The Dark Side of the Moon", "The Wall",
     "Wish You Were Here", "Animals"),
    (4, "POP & ROCK", "Jimi Hendrix tocou o hino americano à guitarra em que festival?", "Woodstock", "Monterey",
     "Isle of Wight", "Coachella"),

    # ------------------------------------------------------------ música portuguesa
    (1, "PORTUGAL", "Amália Rodrigues é conhecida como a rainha do...", "Fado", "Samba", "Flamenco", "Jazz"),
    (1, "PORTUGAL", "Que cantor português ganhou a Eurovisão em 2017?", "Salvador Sobral", "Rui Veloso",
     "Tony Carreira", "Diogo Piçarra"),
    (1, "PORTUGAL", "Qual destes é um fadista famoso?", "Carlos do Carmo", "Bob Marley", "Elvis Presley",
     "Mick Jagger"),
    (1, "PORTUGAL", "Que festas de Lisboa têm marchas e manjericos?", "Santos Populares", "Carnaval de Ovar",
     "Queima das Fitas", "Feira de São Mateus"),
    (2, "PORTUGAL", "'Amar pelos dois' ganhou que concurso?", "Eurovisão", "Grammy", "Óscar",
     "Festival de Paredes de Coura"),
    (2, "PORTUGAL", "O Festival da Canção escolhe a música portuguesa para...", "A Eurovisão", "Os Óscares",
     "Os Grammy", "O Mundial"),
    (2, "PORTUGAL", "'Grândola, Vila Morena', senha do 25 de Abril, é de...", "Zeca Afonso", "Sérgio Godinho",
     "Carlos Paredes", "Rui Veloso"),
    (2, "PORTUGAL", "Quem é chamado o 'pai do rock português'?", "Rui Veloso", "Tony Carreira",
     "Pedro Abrunhosa", "Jorge Palma"),
    (2, "PORTUGAL", "Os Xutos & Pontapés são uma banda de...", "Rock", "Fado", "Pimba", "Ópera"),
    (2, "PORTUGAL", "Mariza e Ana Moura são conhecidas pelo...", "Fado", "Rap", "Kuduro", "Heavy metal"),
    (2, "PORTUGAL", "Os GNR são uma banda de rock de que cidade?", "Porto", "Lisboa", "Coimbra", "Faro"),
    (2, "PORTUGAL", "Em Coimbra, o fado é tradicionalmente cantado por...", "Estudantes de capa e batina",
     "Pescadores no barco", "Crianças na escola", "Soldados a marchar"),
    (2, "PORTUGAL", "A voz dos Madredeus era...", "Teresa Salgueiro", "Dulce Pontes", "Mariza", "Cristina Branco"),
    (2, "PORTUGAL", "O pimba é um estilo português de música...", "Popular e brejeira", "Clássica",
     "Eletrónica experimental", "Religiosa"),
    (2, "PORTUGAL", "Quem foi um mestre da guitarra portuguesa, autor de 'Verdes Anos'?", "Carlos Paredes",
     "Rui Veloso", "Mário Laginha", "Sérgio Godinho"),
    (3, "PORTUGAL", "Os Buraka Som Sistema ficaram famosos com que estilo?", "Kuduro progressivo",
     "Fado eletrónico", "Heavy metal", "Música clássica"),
    (3, "PORTUGAL", "O Rock in Rio também se faz em que cidade portuguesa?", "Lisboa", "Porto", "Braga", "Coimbra"),
    (3, "PORTUGAL", "O festival de Paredes de Coura é em que região?", "Minho", "Algarve", "Alentejo", "Açores"),
    (3, "PORTUGAL", "Que cantora ficou conhecida no mundo pela 'Canção do Mar'?", "Dulce Pontes", "Mariza",
     "Ana Moura", "Cuca Roseta"),
    (3, "PORTUGAL", "Que cantor gravou 'Chico Fininho'?", "Rui Veloso", "Jorge Palma", "Sérgio Godinho",
     "Paulo Gonzo"),
    (3, "PORTUGAL", "José Afonso era conhecido como...", "Zeca", "Tozé", "Zé Pedro", "Johnny"),
    (3, "PORTUGAL", "Qual destas é uma banda portuguesa de metal famosa no mundo?", "Moonspell", "Metallica",
     "Sepultura", "Iron Maiden"),
    (3, "PORTUGAL", "O cavaquinho é tradicional do...", "Minho", "Algarve", "Alentejo", "Ribatejo"),
    (3, "PORTUGAL", "O cante alentejano é cantado...", "Em coro, sem instrumentos", "Com guitarra elétrica",
     "Com orquestra", "Só por crianças"),
    (3, "PORTUGAL", "O fado é Património Imaterial da Humanidade desde...", "2011", "1990", "2001", "2020"),
    (3, "PORTUGAL", "Que instrumento tocam os Zés Pereiras nas festas do Minho?", "Bombo", "Harpa", "Violino",
     "Piano"),
    (3, "PORTUGAL", "Que cantor é autor de 'Encosta-te a mim'?", "Jorge Palma", "Tony Carreira",
     "Pedro Abrunhosa", "Rui Veloso"),
    (3, "PORTUGAL", "'A Minha Casinha' foi um grande êxito rock de que banda?", "Xutos & Pontapés", "GNR",
     "Delfins", "UHF"),
    (4, "PORTUGAL", "O cante alentejano é Património da Humanidade desde...", "2014", "2011", "2008", "2019"),
    (4, "PORTUGAL", "Em que ano nasceu Amália Rodrigues?", "1920", "1940", "1900", "1955"),
    (4, "PORTUGAL", "'Barco Negro' é um fado famoso na voz de...", "Amália Rodrigues", "Carlos do Carmo",
     "Camané", "Ana Moura"),
    (4, "PORTUGAL", "Que pianista de jazz fez dupla com a cantora Maria João?", "Mário Laginha", "Rão Kyao",
     "Carlos Bica", "Jorge Palma"),
    (4, "PORTUGAL", "Os Ornatos Violeta eram de que cidade?", "Porto", "Lisboa", "Setúbal", "Évora"),
    (4, "PORTUGAL", "O DJ e produtor Branko fez parte de que grupo?", "Buraka Som Sistema", "Xutos & Pontapés",
     "GNR", "Madredeus"),
    (4, "PORTUGAL", "O Boom Festival realiza-se perto de...", "Idanha-a-Nova", "Sines", "Lagos", "Viseu"),

    # ------------------------------------------------------------ eletrónica, DJ e produção
    (1, "ELETRÓNICA", "O que faz um DJ?", "Mistura músicas", "Afina pianos", "Dirige orquestras",
     "Constrói guitarras"),
    (1, "ELETRÓNICA", "Fazer 'scratch' é mexer o disco...", "Para a frente e para trás", "Fora do gira-discos",
     "Sempre mais devagar", "Até o partir"),
    (2, "ELETRÓNICA", "O 'drop' na música eletrónica é...", "O momento de mais energia depois da subida",
     "Uma pausa total", "O fim da música", "Um erro do DJ"),
    (2, "ELETRÓNICA", "Para que serve um crossfader?", "Passar de uma música para outra", "Mudar o tom", "Gravar",
     "Afinar"),
    (2, "ELETRÓNICA", "O que é um 'beat'?", "A batida de uma música", "Um tipo de guitarra", "Uma nota aguda",
     "Um microfone"),
    (2, "ELETRÓNICA", "O que faz o 'sync' numa mesa de DJ?", "Iguala o BPM das duas músicas", "Grava a mistura",
     "Liga as luzes", "Corta o som"),
    (2, "ELETRÓNICA", "Um 'sample' é...", "Um pedaço de som gravado", "Um tipo de bateria acústica", "Um cabo",
     "Uma pauta"),
    (2, "ELETRÓNICA", "Um equalizador (EQ) serve para mexer em...", "Graves, médios e agudos", "O BPM",
     "A letra", "A afinação"),
    (2, "ELETRÓNICA", "O efeito que repete o som como um eco chama-se...", "Delay", "Reverb", "Distorção",
     "Compressor"),
    (3, "ELETRÓNICA", "Para que serve o MIDI?", "Enviar notas entre aparelhos musicais", "Gravar vídeo",
     "Medir o volume", "Afinar tambores"),
    (3, "ELETRÓNICA", "Um DAW é...", "Um programa para fazer música no computador", "Um tipo de microfone",
     "Uma dança", "Um festival"),
    (3, "ELETRÓNICA", "O efeito que dá a sensação de uma sala grande chama-se...", "Reverb", "Delay", "Flanger",
     "Phaser"),
    (3, "ELETRÓNICA", "Um compressor de áudio serve para...", "Controlar as diferenças de volume",
     "Encolher o ficheiro", "Mudar a nota", "Acelerar a música"),
    (3, "ELETRÓNICA", "O 'sidechain' faz o baixo...", "Baixar quando bate o bombo", "Ficar mais agudo",
     "Desaparecer da música", "Tocar ao contrário"),
    (3, "ELETRÓNICA", "O autotune corrige...", "A afinação da voz", "O volume da bateria", "O BPM",
     "O ruído da sala"),
    (3, "ELETRÓNICA", "Um vocoder faz a voz soar...", "Robótica", "Mais grave sem efeito", "Como um coro",
     "Sem som"),
    (3, "ELETRÓNICA", "Um filtro passa-baixo deixa passar...", "Os graves", "Os agudos", "Só os médios", "Nada"),
    (3, "ELETRÓNICA", "Num sintetizador, o ADSR controla...", "Como o som começa, dura e acaba", "A cor do ecrã",
     "O BPM", "O volume do microfone"),
    (3, "ELETRÓNICA", "A onda mais 'pura', sem harmónicos, é a...", "Sinusoidal", "Dente de serra", "Quadrada",
     "Ruído branco"),
    (3, "ELETRÓNICA", "O 'build-up' na música eletrónica é...", "A subida de tensão antes do drop",
     "O fim da música", "O nome do DJ", "Um silêncio"),
    (3, "ELETRÓNICA", "Quantizar é...", "Alinhar as notas à grelha do tempo", "Aumentar o volume",
     "Gravar em vinil", "Mudar de tom"),
    (4, "ELETRÓNICA", "O MIDI foi lançado em que década?", "Anos 80", "Anos 60", "Anos 2000", "Anos 90"),
    (4, "ELETRÓNICA", "Num sintetizador, um LFO é...", "Um oscilador lento que mexe noutros controlos",
     "Um filtro de agudos", "Um tipo de microfone", "Um botão de gravar"),
    (4, "ELETRÓNICA", "O Yamaha DX7, famoso nos anos 80, usava síntese...", "FM", "Subtrativa analógica",
     "Granular", "Por amostras"),
    (4, "ELETRÓNICA", "Uma amostragem de 44 100 Hz é a do...", "CD", "Telefone fixo", "Vinil", "Cassete"),
    (4, "ELETRÓNICA", "Para gravar sons até 20 000 Hz é preciso amostrar a pelo menos...", "40 000 Hz",
     "20 000 Hz", "10 000 Hz", "80 000 Hz"),

    # ------------------------------------------------------------ ciência do som
    (1, "CIÊNCIA", "O som é feito de...", "Vibrações", "Luz", "Eletricidade estática", "Magnetismo"),
    (1, "CIÊNCIA", "Ouvir música muito alta durante muito tempo pode causar...", "Perda de audição",
     "Ouvido melhor", "Olhos vermelhos", "Cabelos brancos"),
    (1, "CIÊNCIA", "O som consegue viajar no espaço, onde não há ar?", "Não, precisa de ar ou matéria",
     "Sim, ainda mais rápido", "Sim, igual ao da Terra", "Só perto das estrelas"),
    (2, "CIÊNCIA", "O que viaja mais depressa?", "A luz", "O som", "São iguais", "Depende do dia"),
    (2, "CIÊNCIA", "Vemos o relâmpago antes de ouvir o trovão porque...", "A luz é mais rápida que o som",
     "O trovão acontece depois", "O som vem de outro sítio", "Os olhos são mais rápidos"),
    (2, "CIÊNCIA", "O eco acontece quando o som...", "Bate numa superfície e volta", "Fica mais agudo",
     "Desaparece", "Passa pela água"),
    (2, "CIÊNCIA", "Uma corda mais curta, a vibrar, dá um som mais...", "Agudo", "Grave", "Forte", "Lento"),
    (2, "CIÊNCIA", "Uma corda mais esticada dá um som mais...", "Agudo", "Grave", "Fraco", "Longo"),
    (2, "CIÊNCIA", "O Hertz (Hz) mede...", "Vibrações por segundo", "O volume", "A duração", "A distância"),
    (2, "CIÊNCIA", "O volume de um som mede-se em...", "Decibéis", "Hertz", "BPM", "Metros"),
    (2, "CIÊNCIA", "Quanto mais vibrações por segundo, o som é mais...", "Agudo", "Grave", "Forte", "Lento"),
    (2, "CIÊNCIA", "O tempo (velocidade) de uma música mede-se em...", "BPM", "Hertz", "Decibéis", "Volts"),
    (3, "CIÊNCIA", "Sons acima dos 20 000 Hz chamam-se...", "Ultrassons", "Infrassons", "Supersons", "Megassons"),
    (3, "CIÊNCIA", "Sons abaixo dos 20 Hz chamam-se...", "Infrassons", "Ultrassons", "Graves especiais", "Subsons"),
    (3, "CIÊNCIA", "Que animal usa ultrassons para se orientar no escuro?", "Morcego", "Cavalo", "Galinha", "Gato"),
    (3, "CIÊNCIA", "O som viaja mais depressa...", "Na água", "No ar", "No vácuo", "É igual em todo o lado"),
    (3, "CIÊNCIA", "A parte do ouvido que vibra com o som é o...", "Tímpano", "Lóbulo", "Nariz", "Cérebro"),
    (3, "CIÊNCIA", "O LÁ usado para afinar instrumentos costuma ter...", "440 Hz", "400 Hz", "432 Hz", "512 Hz"),
    (3, "CIÊNCIA", "Uma oitava acima de um LÁ de 440 Hz dá...", "880 Hz", "660 Hz", "220 Hz", "1000 Hz"),
    (3, "CIÊNCIA", "A velocidade do som no ar é de cerca de...", "340 metros por segundo",
     "3 metros por segundo", "30 metros por segundo", "300 000 km por segundo"),
    (3, "CIÊNCIA", "O ouvido humano ouve sons de cerca de...", "20 a 20 000 Hz", "2 a 200 Hz", "200 a 2 000 Hz",
     "1 a 1 milhão de Hz"),
    (3, "CIÊNCIA", "O que transforma o sinal elétrico de volta em som?", "Altifalante", "Microfone", "Cabo",
     "Pedal"),
    (4, "CIÊNCIA", "O efeito Doppler explica porque a sirene de uma ambulância...", "Muda de tom ao passar",
     "Soa mais forte à noite", "Tem duas notas", "Não se ouve na água"),
    (4, "CIÊNCIA", "Subir uma oitava é...", "Duplicar a frequência", "Somar 100 Hz", "Triplicar a frequência",
     "Dividir a frequência por dois"),
    (4, "CIÊNCIA", "Os harmónicos de um som de 100 Hz estão em...", "200, 300, 400 Hz...", "150, 250 Hz...",
     "50, 25 Hz...", "101, 102 Hz..."),
    (4, "CIÊNCIA", "A escala dos decibéis é...", "Logarítmica", "Linear", "Circular", "Musical"),
    (4, "CIÊNCIA", "Junto às colunas de um concerto de rock há cerca de...", "110 decibéis", "30 decibéis",
     "60 decibéis", "200 decibéis"),
    (4, "CIÊNCIA", "A cóclea, no ouvido interno, tem a forma de...", "Um caracol", "Uma estrela", "Um cubo",
     "Uma flauta"),

    # ------------------------------------------------------------ cinema e jogos
    (2, "CINEMA & JOGOS", "Quem compôs a música de 'Star Wars'?", "John Williams", "Hans Zimmer", "Mozart",
     "Elton John"),
    (2, "CINEMA & JOGOS", "A música do filme 'Tubarão' é famosa por duas notas que...",
     "Se repetem cada vez mais depressa", "Nunca se repetem", "São cantadas por um coro",
     "São tocadas num piano de brincar"),
    (2, "CINEMA & JOGOS", "Que filme da Disney tem a canção 'Let It Go'?", "Frozen", "Moana", "Encanto", "Coco"),
    (2, "CINEMA & JOGOS", "Que jogo de ritmo usa uma guitarra de plástico com botões coloridos?", "Guitar Hero",
     "Just Dance", "Tetris", "FIFA"),
    (2, "CINEMA & JOGOS", "'My Heart Will Go On' é a canção de que filme?", "Titanic", "Avatar",
     "O Guarda-Costas", "Top Gun"),
    (2, "CINEMA & JOGOS", "Quem canta 'My Heart Will Go On'?", "Céline Dion", "Whitney Houston", "Mariah Carey",
     "Adele"),
    (2, "CINEMA & JOGOS", "A música do Tetris vem de uma canção tradicional de...", "Rússia", "Japão",
     "Estados Unidos", "Alemanha"),
    (2, "CINEMA & JOGOS", "Que consola de 1989 ficou famosa pelo som chiptune?", "Game Boy", "PlayStation", "Xbox",
     "Wii"),
    (3, "CINEMA & JOGOS", "Quem fez a música de 'O Rei Leão' (1994) e 'Gladiador'?", "Hans Zimmer",
     "John Williams", "Ennio Morricone", "Danny Elfman"),
    (3, "CINEMA & JOGOS", "Que compositor japonês criou a música do Super Mario?", "Koji Kondo", "Nobuo Uematsu",
     "Yoko Shimomura", "Hideo Kojima"),
    (3, "CINEMA & JOGOS", "Nobuo Uematsu é famoso pela música de que saga?", "Final Fantasy", "Sonic", "Pokémon",
     "Street Fighter"),
    (3, "CINEMA & JOGOS", "Ennio Morricone ficou famoso pela música de filmes...", "Western (cowboys)",
     "De terror japonês", "Mudos dos anos 20", "De super-heróis"),
    (3, "CINEMA & JOGOS", "Quem compôs a música de 'Harry Potter e a Pedra Filosofal'?", "John Williams",
     "Hans Zimmer", "Howard Shore", "James Horner"),
    (3, "CINEMA & JOGOS", "Que saga de jogos tem a famosa ocarina mágica?", "The Legend of Zelda", "Metroid",
     "Kirby", "Castlevania"),
    (4, "CINEMA & JOGOS", "A música de 'Missão Impossível' está em que compasso?", "5/4", "4/4", "3/4", "2/4"),
    (4, "CINEMA & JOGOS", "Howard Shore compôs a música de que trilogia?", "O Senhor dos Anéis", "Star Wars",
     "Matrix", "Regresso ao Futuro"),
    (4, "CINEMA & JOGOS", "Quem compôs a música de 'Interstellar', com um órgão gigante?", "Hans Zimmer",
     "Ludwig Göransson", "John Williams", "Max Richter"),
    (4, "CINEMA & JOGOS", "A Game Boy tinha quantos canais de som?", "4", "2", "8", "16"),
    (4, "CINEMA & JOGOS", "Que jogo de 1978 tinha música que acelerava com os inimigos a descer?",
     "Space Invaders", "Pac-Man", "Pong", "Tetris"),
]
CATEGORIES = sorted(set(t[1] for t in TRIVIA))

# ====================================================================== generated theory questions
NOTE_PT = {"C": "DÓ", "D": "RÉ", "E": "MI", "F": "FÁ", "G": "SOL", "A": "LÁ", "B": "SI"}
LETTERS = "CDEFGAB"
NAT = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def pt_note(letter, acc):
    """'F', 1 -> 'Fá#' ; 'B', -1 -> 'Sib' (as written in Portugal)"""
    name = NOTE_PT[letter].capitalize()
    return name + {0: "", 1: "#", -1: "b", 2: "##", -2: "bb"}[acc]


def spell(root_letter, root_acc, steps, semis):
    """the note `steps` letters and `semis` semitones above the root, correctly spelled"""
    li = (LETTERS.index(root_letter) + steps) % 7
    letter = LETTERS[li]
    target = (NAT[root_letter] + root_acc + semis) % 12
    acc = (target - NAT[letter] + 6) % 12 - 6
    return letter, acc


def triad(root_letter, root_acc, minor):
    third = spell(root_letter, root_acc, 2, 3 if minor else 4)
    fifth = spell(root_letter, root_acc, 4, 7)
    return [(root_letter, root_acc), third, fifth]


def chord_name(letter, acc, minor):
    return "%s %s" % (pt_note(letter, acc), "menor" if minor else "maior")


ROOTS = {3: [("C", 0), ("G", 0), ("F", 0), ("D", 0), ("A", 0)],
         4: [("E", 0), ("B", -1), ("E", -1), ("A", -1), ("B", 0), ("F", 1)]}
SHARPS = [("G", 0, 1), ("D", 0, 2), ("A", 0, 3), ("E", 0, 4), ("B", 0, 5), ("F", 1, 6)]
FLATS = [("F", 0, 1), ("B", -1, 2), ("E", -1, 3), ("A", -1, 4), ("D", -1, 5)]
FIGURES = [("semibreve", "4", 2), ("mínima", "2", 2), ("semínima", "1", 2), ("colcheia", "½", 3),
           ("semicolcheia", "¼", 3)]
ITALIAN = [  # term, meaning, level
    ("Allegro", "Rápido e alegre", 2), ("Adagio", "Lento", 2), ("Presto", "Muito rápido", 3),
    ("Largo", "Muito lento e solene", 3), ("Andante", "Ao passo, calmo", 3), ("Moderato", "Moderado", 2),
    ("Piano", "Suave", 2), ("Forte", "Forte", 1), ("Pianissimo", "Muito suave", 3),
    ("Fortissimo", "Muito forte", 2), ("Crescendo", "Cada vez mais forte", 2),
    ("Diminuendo", "Cada vez mais suave", 3), ("Ritardando", "A abrandar", 3), ("Accelerando", "A acelerar", 3),
    ("Staccato", "Notas curtas e separadas", 3), ("Legato", "Notas ligadas", 3),
    ("Fermata", "Segurar a nota mais tempo", 4), ("Da capo", "Voltar ao princípio", 4), ("Tutti", "Todos juntos", 4),
    ("A tempo", "Voltar ao tempo de antes", 4), ("Rubato", "Tempo livre, a respirar", 4),
    ("Mezzo-forte", "Meio forte", 3), ("Dolce", "Docemente", 4), ("Vivace", "Vivo e rápido", 4),
]
FAMILIES = ["Cordas", "Sopros de madeira", "Sopros de metal", "Percussão", "Teclas"]
INSTR_FAMILY = [  # instrument, family index, level
    ("Violino", 0, 1), ("Violoncelo", 0, 2), ("Contrabaixo", 0, 2), ("Harpa", 0, 2), ("Guitarra", 0, 1),
    ("Flauta", 1, 2), ("Clarinete", 1, 2), ("Oboé", 1, 3), ("Fagote", 1, 3), ("Saxofone", 1, 4),
    ("Trompete", 2, 1), ("Trombone", 2, 2), ("Trompa", 2, 3), ("Tuba", 2, 2),
    ("Timbales", 3, 2), ("Xilofone", 3, 2), ("Pratos", 3, 1), ("Triângulo", 3, 1), ("Castanholas", 3, 2),
    ("Piano", 4, 1), ("Órgão", 4, 2), ("Cravo", 4, 3), ("Acordeão", 4, 3),
]
INTERVALS = [("segunda menor", 1, 3), ("segunda maior", 2, 3), ("terceira menor", 3, 3),
             ("terceira maior", 4, 3), ("quarta perfeita", 5, 3), ("trítono", 6, 4), ("quinta perfeita", 7, 3),
             ("sexta menor", 8, 4), ("sexta maior", 9, 4), ("sétima menor", 10, 4), ("sétima maior", 11, 4),
             ("oitava", 12, 2)]
RELATIVE = [(("C", 0), ("A", 0)), (("G", 0), ("E", 0)), (("D", 0), ("B", 0)), (("A", 0), ("F", 1)),
            (("E", 0), ("C", 1)), (("F", 0), ("D", 0)), (("B", -1), ("G", 0)), (("E", -1), ("C", 0))]


def _opts(right, wrongs):
    wrongs = [w for w in dict.fromkeys(wrongs) if w != right]
    random.shuffle(wrongs)
    opts = [right] + wrongs[:3]
    random.shuffle(opts)
    return opts


def gen_theory(level, rnd=random):
    """one generated question at about this level: (text, right, [4 options]) - or None"""
    kinds = {1: ["family", "italian", "english"], 2: ["figure", "italian", "family", "english", "bps"],
             3: ["figure", "chord", "interval", "italian", "family", "sharps"],
             4: ["chord", "interval", "sharps", "flats", "relative", "italian"]}[max(1, min(4, level))]
    k = rnd.choice(kinds)
    if k == "figure":
        pool = [f for f in FIGURES if f[2] <= level] or FIGURES
        name, val, _ = rnd.choice(pool)
        right = val
        opts = _opts(right, [v for _, v, _ in FIGURES])
        return ("Num compasso de 4/4, quantos tempos vale uma %s?" % name, right, opts)
    if k == "italian":
        pool = [t for t in ITALIAN if abs(t[2] - level) <= 1] or ITALIAN
        term, meaning, _ = rnd.choice(pool)
        return ("Na música, '%s' quer dizer..." % term, meaning, _opts(meaning, [m for _, m, _ in ITALIAN]))
    if k == "english":
        letter = rnd.choice(LETTERS)
        return ("A nota %s, no sistema inglês (letras), é..." % NOTE_PT[letter], letter,
                _opts(letter, list(LETTERS)))
    if k == "family":
        pool = [t for t in INSTR_FAMILY if t[2] <= level + 1] or INSTR_FAMILY
        inst, fam, _ = rnd.choice(pool)
        return ("A que família de instrumentos pertence: %s?" % inst, FAMILIES[fam], _opts(FAMILIES[fam], FAMILIES))
    if k == "bps":
        n = rnd.choice([1, 2, 3, 4])
        right = "%d BPM" % (60 * n)
        return ("Uma música com %d batida%s por segundo tem quantos BPM?" % (n, "s" if n > 1 else ""), right,
                _opts(right, ["%d BPM" % v for v in (30, 60, 90, 100, 120, 150, 180, 240, 300) if v != 60 * n]))
    if k == "chord":
        roots = ROOTS[3] + (ROOTS[4] if level >= 4 else [])
        letter, acc = rnd.choice(roots)
        minor = rnd.random() < (0.5 if level >= 4 else 0.25)
        notes = triad(letter, acc, minor)
        right = " ".join(pt_note(l2, a2) for l2, a2 in notes)
        wrongs = []
        other = triad(letter, acc, not minor)                       # major <-> minor
        wrongs.append(" ".join(pt_note(l2, a2) for l2, a2 in other))
        for ol, oa in roots:
            if (ol, oa) != (letter, acc):
                wrongs.append(" ".join(pt_note(l2, a2) for l2, a2 in triad(ol, oa, minor)))
        wrongs = [wrongs[0]] + rnd.sample(wrongs[1:], min(4, len(wrongs) - 1))
        return ("Que notas formam o acorde de %s?" % chord_name(letter, acc, minor), right, _opts(right, wrongs))
    if k == "interval":
        pool = [t for t in INTERVALS if t[2] <= level] or INTERVALS
        name, semis, _ = rnd.choice(pool)
        right = "%d" % semis
        return ("Quantos meios-tons tem uma %s?" % name, right,
                _opts(right, ["%d" % v for v in range(1, 13) if abs(v - semis) <= 3]))
    if k == "sharps":
        letter, acc, n = rnd.choice(SHARPS[:3] if level < 4 else SHARPS)
        right = "%d" % n
        return ("Quantos sustenidos tem a escala de %s maior?" % pt_note(letter, acc), right,
                _opts(right, ["%d" % v for v in range(0, 8)]))
    if k == "flats":
        letter, acc, n = rnd.choice(FLATS)
        right = "%d" % n
        return ("Quantos bemóis tem a escala de %s maior?" % pt_note(letter, acc), right,
                _opts(right, ["%d" % v for v in range(0, 7)]))
    if k == "relative":
        (ml, ma), (rl, ra) = rnd.choice(RELATIVE)
        right = chord_name(rl, ra, True)
        wrongs = [chord_name(l2, a2, True) for _, (l2, a2) in RELATIVE if (l2, a2) != (rl, ra)]
        return ("Qual é a tonalidade relativa menor de %s?" % chord_name(ml, ma, False), right,
                _opts(right, wrongs))
    return None
