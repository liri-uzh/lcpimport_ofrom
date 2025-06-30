# OFROM Import Pipeline

This repository contains scripts to download the OFROM files from the NAKALA repository, process them and import the corpus into LCP.

## Run the pipeline

```bash
python main.py
```

## main.py

 1. Download the OFROM TEI and WAV files from Nakala
 2. Convert the TEI files into CSV files prepared for import into LCP
 3. Upload to LCP

## download.py

Uses the Nakala API to list and download the TEI and WAV files of the OFROM corpus

If a file already exists locally and it has the same SHA1 signature, it skips the download step for this file

## convert.py

Goes through all the TEI files and uses `lcpcli.builder.Corpus` to prepare CSV files for import into LCP
