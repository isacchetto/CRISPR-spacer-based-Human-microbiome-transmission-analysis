# TODO
- [x] Installare tools
    - [x] installare minced
    - [x] installare pilercr
    - [x] installare CRISPRDetect3
        - [x] creare link per environment_CRISPRDetect3.yml di CRISPRDetect
        - [x] rederlo eseguibile come CRISPRDetect (non `perl CRISPRDetect.pl`)
        - [x] scaricare GeneMarkS
            - [x] copiare gmhmmp e gmhmmp.pl in CRISPRDetect e renderli eseguibili
            - [x] aggiungere la key decopressa in ~/.gm_key
    - [x] installare CRISPRidentify
        - [x] rendere eseguibile come CRISPRidentify (non `python3 CRISPRidentify.py`)
    - [x] installare CRISPRCasFinder
        - [x] creare link per ccf.environment.yml di CRISPRCasFinder
        - [x] rendere eseguibile come CRISPRCasFinder (non `perl CRISPRCasFinder.pl`)
- [x] Creare script di run e girare tutto con i parametri del paper
    - [x] minced
    - [x] pilercr (1 e 2)
    - [x] CRISPRDetect
- [x] Creare parsing:
    - [x] creare parsing per minced
    - [x] creare parsing per pilercr
    - [x] creare parsing per CRISPRDetect
- [x] Creare file di output tsv
    - [x] creare file di output per minced
    - [x] creare file di output per pilercr
    - [x] creare file di output per CRISPRDetect
- [x] Creare file tools_difference.txt con un esempio di differenza tra i CRISPR trovati dai tools
- [x] Dividere i CRISPR in base alla distanza tra cas e crispr
    - [x] 0-1000 bp
    - [x] 1000-10.000 bp
    - [x] >10.000 bp
- [x] possibilita di far partire piu tool insieme (in serie) sulla stessa input dir
- [x] capire se usare veramete CRISPRDetect3 e nel caso aggiornare bene l'environment.yml
- [ ] catturare gli errori e metterli in un file di log (catturarli sui thread)
- [ ] ricreare i tool intermedi basandosi su run_tool
- [ ] 


- [ ] fare grafici per ogni tool:
  - [x] lunghezza mediana DR (per capire i valori outlier e fare un successivo cut-off)
  - [x] lunghezza mediana SP (per capire i valori outlier e fare un successivo cut-off)
  - [x] deviazione standard lunghezza DR (per capire se i DR differiscono moltom, ma piu utile forse il coefficente di variazione)
  - [x] deviazione standard lunghezza SP (per capire se gli SP differiscono molto, ma piu utile forse il coefficente di variazione)
  - [x] coefficente di variazione lunghezza DR (utile per uniformare i valori dato che le dimensioni dei DR variano molto tra CRISPR diversi)
  - [x] coefficente di variazione lunghezza SP (utile per uniformare i valori dato che le dimensioni degli SP variano molto tra CRISPR diversi)
  - [x] ratio minlen/maxlen DR (-minrepeatratio in pilercr) (per capire se ci sono CRISPR con DR fuori scala)
  - [ ] conservazione DR (-mincons in pilercr 0.9 (PILER1) e 0.8 (PILER2)) (per capire se i DR sono conservati o se ci sono molti errori/mismatches)

- [x] conforntare i tool e vedere se ci sono sovrapposti
  - [x] colonne: ID crispr , ToolCodename
  - [x] sistemare la colonna ToolCodename in modo che sia un set (non duplicati e ordinati)
  - [x] inserirlo nel multi_tool
  - [ ] creare uno script .py

- [ ] utilizzare colonne cas e prendere solo quelli dei cas vicini ai crispr
  - [x] count
  - [ ] upset
  - [ ] singoli
  - [ ] boxplot
- [x] unique dr quanto aumenta il numero di dr aumentando i tool
- [x] lavorare sui cas vedere quali tool trovano crispr vicino a cas e il numero una colonna per tool e il numero di spacer singoli vicino a cas


- [ ] guardare i tool che girano sulle reads
  - [ ] metaCRAST
  - [ ] metaCRISPR



- [x] UPSET PLOT raggruppando per CRISPR ID
- [x] unire le righe per ID uguale e unendo tutti le DR per poi vedere se la similarità rimane bassa (e quindi sono veramente lo stesso CRISPR)

- [ ] Guardare perche in CRISPRDetect il parse aggiunge piu volte lo stesso crispr


muscle  max 100
mafft >100

matrix informazione -> somma informazione colonna -> media 


db virus 
script per allineare spacer al db virus



ho un dataframe chiamato 'df_exploded' in python che ha un CRISPR per ogni riga e ha queste colonne:
MAG : file dalla quale è stato estratto il CRISPR
Contig : contig dalla quale è stato estratto il CRISPR
Start : start del CRISPR
End : end del CRISPR
Repeats : repeats del CRISPR (separati da virgola)
Spacers : spacers del CRISPR (separati da virgola)
Cas_0-1000 : numero di cas operon a meno di 1000 bp dal CRISPR
Cas_1000-10000 : numero di cas operon tra 1000 e 10000 bp dal CRISPR
Cas_>100000 : numero di cas operon a piu di 10000 bp dal CRISPR
Cas_overlayed : numero di cas operon che sovrappongono il CRISPR
ToolCodename : nome del tool che ha trovato il CRISPR (minced_Default, minced_Relaxed, pilercr_Default, pilercr_Relaxed,CRISPRDetect3_nocpu)
SP_lens : lunghezza dei vari spacers (separati da virgola)
DR_lens : lunghezza dei vari repeats (separati da virgola)
median_DR_len : lunghezza mediana dei repeats
median_SP_len : lunghezza mediana degli spacers
max_DR_len : lunghezza massima dei repeats
min_DR_len : lunghezza minima dei repeats
max_SP_len : lunghezza massima degli spacers
min_SP_len : lunghezza minima degli spacers
std_DR_len : deviazione standard della lunghezza dei repeats
std_SP_len : deviazione standard della lunghezza degli spacers
cv_DR_len : coefficente di variazione della lunghezza dei repeats (std/mean)
cv_SP_len : coefficente di variazione della lunghezza degli spacers (std/mean)
minmax_DR_ratio : rapporto tra la lunghezza minima e massima dei repeats
Nearby_Cas : booleano che indica se ci sono cas operon vicini al CRISPR (<1000 bp)
Closest_Cas : cas operon piu vicino al CRISPR (Cas_0-1000, Cas_1000-10000, Cas_>100000, Cas_overlayed)
Unique_DR : numero di DR unici trovati
nSP_match_VSC5 : numero di spacers del CRISPR trovati nel dataset virale VSC5
nSP_match_GPD : numero di spacers del CRISPR trovati nel dataset virale GPD
nSP_match_MGV : numero di spacers del CRISPR trovati nel dataset virale MGV


voglio ora fare un grafico con seaborn che mi mostri per ogni tool quanti CRISPR hanno spacer che matchano con i virus e quanti no (una barra per ogni dataset virale con etichette legenda e numeri) e che mi faccia anche distinguere dai CRISPR che hanno cas vicini e quelli che non ce l'hanno (Nearby_Cas) sempre con legenda de etichette e numeri