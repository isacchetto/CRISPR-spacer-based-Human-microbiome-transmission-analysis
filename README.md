# CRISPR-spacer-based Human microbiome transmission analysis
This repository contains the code and test data of my internship project at the [Laboratory of Computational Metagenomics](http://segatalab.cibio.unitn.it/) of the [CIBIO Department, University of Trento, Italy](https://www.cibio.unitn.it/).

The project is about the analysis of human microbiome transmission using CRISPR spacers.

The project is supervised by Dr. Nicola Segata and Dr. Matteo Ciciani.
## Project Description
The project aims to investigate the transmission of human microbiome using CRISPR spacers. The project is divided into the following steps:
1. ...
## Project Structure
The repository is structured as follows:
- `scripts/`: contains the scripts that I have written for the analysis.
- `out/`: contains the output directories and files derived from the analysis.
- `samples/`: contains the samples used in the project. Such as MAGs (metagenome-assembled genomes) used in the project for testing scripts.
## Project Dependencies
For this project, mainly make in python, I use Conda to manage the dependencies. The dependencies are listed in the `environment.yml` file. To create the conda environment, run the following command:
```bash
conda env create -f environment.yml
```
To activate the conda environment, run the following command:
```bash
conda activate crispr-transmission
```
## Project Execution

