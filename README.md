# docker-mothur
Docker image running MOTHUR


### Docker image

[![Docker Repository on Quay](https://quay.io/repository/fhcrc-microbiome/mothur/status "Docker Repository on Quay")](https://quay.io/repository/fhcrc-microbiome/mothur)

The primary product of this repository is a Docker image that runs mothur.
The image also contains a run script that makes it easier to run mothur on
files that are hosted on AWS S3. 


### Run script for classify.seqs

The run script (`run_classify_seqs.py`) provides a mechanism for running the 
classify.seqs command from mothur in a single command, which includes fetching
and returning files to AWS S3. The reason for including this script is to 
facilitate usage of AWS Batch, which is most easily run as a single command
line script. A number of the options for running mothur within this Docker 
image should be accessible via the run script.

```
usage: run_classify_seqs.py [-h] --input INPUT --ref-fasta REF_FASTA
                            --ref-taxonomy REF_TAXONOMY --output-folder
                            OUTPUT_FOLDER [--threads THREADS]
                            [--temp-folder TEMP_FOLDER]

Run the classify.seqs command within mothur.

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         Location for input file(s). Comma-separated.
                        (Supported: sra://, s3://, or ftp://).
  --ref-fasta REF_FASTA
                        Reference FASTA file. (Supported: s3://, ftp://, or
                        local path).
  --ref-taxonomy REF_TAXONOMY
                        Reference taxonomy file. (Supported: s3://, ftp://, or
                        local path).
  --output-folder OUTPUT_FOLDER
                        Folder to place results. (Supported: s3://, or local
                        path).
  --threads THREADS     Number of threads to use.
  --temp-folder TEMP_FOLDER
                        Folder used for temporary files.
```

### Wrapper script for running mothur from paired FASTQ files

Test data (in `/tests/16S_V4_data/`) was downloaded from PRJNA386260, "V4 16S rRNA sequencing of human fecal microbiota Raw sequence reads",
deposited by the University of Michigan.

Workflow adapted from https://mothur.org/wiki/MiSeq_SOP, accessed August 9th, 2018.

Citation: 

Kozich JJ, Westcott SL, Baxter NT, Highlander SK, Schloss PD. (2013): Development of a dual-index sequencing strategy and curation pipeline for analyzing amplicon sequence data on the MiSeq Illumina sequencing platform. Applied and Environmental Microbiology. 79(17):5112-20.

usage: run_mothur_from_fastq.py [-h] --input-folder INPUT_FOLDER
                                --output-folder OUTPUT_FOLDER
                                [--threads THREADS]
                                [--temp-folder TEMP_FOLDER]

Run mothur on a set of FASTQ files.

optional arguments:
  -h, --help            show this help message and exit
  --input-folder INPUT_FOLDER
                        Folder containing input files.
  --output-folder OUTPUT_FOLDER
                        Folder to place results. (Supported: s3://, or local
                        path).
  --threads THREADS     Number of threads to use.
  --temp-folder TEMP_FOLDER
                        Folder used for temporary files.

