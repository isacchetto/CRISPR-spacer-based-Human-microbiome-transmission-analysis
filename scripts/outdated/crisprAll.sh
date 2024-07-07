#!/bin/bash

# Controlla se è stato fornito il percorso della cartella come argomento
if [ $# -ne 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

directory="$1"

# Controlla se il percorso fornito è una cartella esistente
if [ ! -d "$directory" ]; then
    echo "$directory non è una cartella valida."
    exit 1
fi

# Naviga nella cartella o esce in caso di errore (es. permessi)
cd "$directory" || exit 1

# Crea le cartelle di output univoche
date=$(date +%Y%m%d%H%M%S)
dir_out_minced="out_minced_$date"
dir_out_pilercr="out_pilercr_$date"
mkdir -p ../out/$dir_out_minced
mkdir -p ../out/$dir_out_pilercr
dir_out_minced=$(cd ../out/$dir_out_minced && pwd)
dir_out_pilercr=$(cd ../out/$dir_out_pilercr && pwd)

# Ciclo per ogni file nella cartella
for file in *.fna; do
    if [ -f "$file" ]; then

        # Estrae il nome del file senza estensione
        filename="${file%.*}"
        
        # minced
        minced $file $dir_out_minced/$filename.crispr $dir_out_minced/$filename.gff
        # Shorting the gff file
        cat $dir_out_minced/$filename.gff | grep -v "##gff-version 3" > $dir_out_minced/$filename.short.gff 

        # pilercr
        pilercr -in $file -out $dir_out_pilercr/$filename.crispr -seq $dir_out_pilercr/$filename.crisprDR.fa -noinfo
    fi
done
