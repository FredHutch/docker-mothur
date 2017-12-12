# docker-mothur
Docker image running MOTHUR


### Docker image

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
