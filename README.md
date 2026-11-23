# MapleHits

Números de dano no estilo MapleStory para WoW Forever (Interface 16001): dígitos em degradê com borda branca que
saltam, empilham e sobem.

- hit: vermelho-laranja a amarelo · crítico: carmesim a rosa, com brilho · dano em você: violeta a magenta
- MISS nas suas cores quando você erra, violeta quando o mob erra você
- esconde os números do próprio jogo enquanto está ligado (`/mh blizz` traz de volta)

## Instalar

Baixe `MapleHits.zip` em [Releases](https://github.com/hberdu/MapleHits/releases/latest) e extraia dentro de
`World of Warcraft\_forever_\Interface\AddOns`. Tem que ficar `AddOns\MapleHits\MapleHits.toc`.

O "Download ZIP" do botão Code gera `MapleHits-main` (e o Windows às vezes cria `MapleHits-main\MapleHits-main`): o
WoW não lista assim. Renomeie a pasta que tem o `.toc` para `MapleHits` e coloque direto em `AddOns`.

## Comandos

`/mh` liga/desliga · `/mh teste` · `/mh escala 1.2` · `/mh altura 60` · `/mh blizz` · `/mh debug`

## Arte

Sem arte do jogo: os dígitos são desenhados a partir da fonte Bowlby One (SIL Open Font License, ver
`OFL-BowlbyOne.txt`) por `py make_maplehits_art.py` e `py make_maplehits_font.py`. Teste: `py test_maplehits.py`
(precisa de `pip install lupa`).

Licença MIT (`LICENSE`), exceto as fontes `BowlbyOne-Regular.ttf` e `MapleHitsDigits.ttf`, que seguem a SIL Open Font
License. Projeto de fã, sem ligação com a Nexon ou a Blizzard.
