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

# Naviga nella cartella
cd "$directory" || exit 1
dir_out="out_$(date +%Y%m%d%H%M%S)"
mkdir -p $dir_out
# Ciclo per ogni file nella cartella
for file in *.fna; do
    if [ -f "$file" ]; then

        # Estrae il nome del file
        filename="${file%.*}"
        
        # minced
        minced $file $dir_out/$filename.crispr $dir_out/$filename.gff
        
        # shorting the gff file
        cat $dir_out/$filename.gff | grep -v "##gff-version 3" > $dir_out/$filename.short.gff 
    fi
done
