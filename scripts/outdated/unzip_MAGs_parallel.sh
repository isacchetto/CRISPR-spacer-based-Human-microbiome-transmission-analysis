#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

export input_folder=$1

# Check if input folder exists or not
if [ ! -d "$input_folder" ]; then
    echo "$input_folder non è una cartella valida."
    exit 1
fi

# Funzione per decomprimere un file .bz2 e mantenerlo nella stessa struttura della directory
decompress_bz2() {
    local input_file="$1"
    local output_dir="$2"
    local relative_path="${input_file#"$input_folder"}"
    local output_file="$output_dir${relative_path%.bz2}"
    # echo "Decompressione di $input_file in $output_file"

    # Crea la directory di output se non esiste
    mkdir -p "$(dirname "$output_file")"
    
    # Decomprimi il file .bz2
    bunzip2 -kc "$input_file" > "$output_file"
}

decompress_bz2_parallel() {
    local input_file="$1"
    local output_dir="$2"
    local relative_path="${input_file#"$input_folder"}"
    local output_file="$output_dir${relative_path%.bz2}"
    # echo "Decompressione di $input_file in $output_file"

    # Crea la directory di output se non esiste
    mkdir -p "$(dirname "$output_file")"
    
    # Decomprimi il file .bz2
    bunzip2 -kc "$input_file" > "$output_file"
}
export -f decompress_bz2_parallel

# Percorsi delle cartelle di input e output
output_folder=$1
date=$(date +%Y%m%d%H%M%S)
output_folder="$1_unzip_$date"
mkdir -p $output_folder


# Impostiamo il numero di processi paralleli
NUM_PARALLEL=$(sysctl -n hw.ncpu)
# NUM_PARALLEL=$((5 * $(sysctl -n hw.ncpu)))

echo "Input folder: $input_folder"
echo "Output folder: $output_folder"
echo "Number of parallel processes: $NUM_PARALLEL"
echo "Running..."

# Troviamo tutti i file .bz2 nella cartella di input e nelle sue sottocartelle e li passiamo a parallel per la decompressione
find "$input_folder" -type f -name "*.bz2" | parallel -j "$NUM_PARALLEL" decompress_bz2_parallel {} "$output_folder"

# Non in parallelo
# find "$input_folder" -type f -name "*.bz2" | while read -r file; do
#     decompress_bz2 "$file" "$output_folder"
# done

echo "Done."