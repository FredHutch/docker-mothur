FROM ubuntu:16.04
MAINTAINER sminot@fredhutch.org

# Install prerequisites
RUN apt update && \
	apt install -y wget unzip python python-pip bats awscli curl

ADD requirements.txt /usr/local/
RUN pip install -r /usr/local/requirements.txt

# Install the SRA toolkit
RUN cd /usr/local/bin && \
	wget https://ftp-trace.ncbi.nlm.nih.gov/sra/sdk/2.8.2/sratoolkit.2.8.2-ubuntu64.tar.gz && \
	tar xzvf sratoolkit.2.8.2-ubuntu64.tar.gz && \
	ln -s /usr/local/bin/sratoolkit.2.8.2-ubuntu64/bin/* /usr/local/bin/ && \
	rm sratoolkit.2.8.2-ubuntu64.tar.gz

# Download mothur binaries
RUN cd /bin && \
	wget https://github.com/mothur/mothur/releases/download/v1.39.5/Mothur.linux_64.zip && \
	unzip Mothur.linux_64.zip && \
	rm Mothur.linux_64.zip

# Add the helper functions to /usr/local/bin
ADD batch_helpers/ /usr/local/bin/batch_helpers/
# Add that directory to the PYTHONPATH
ENV PYTHONPATH="/usr/local/bin/batch_helpers"

# Add the mothur folder to the PATH
ENV PATH="/bin/mothur:${PATH}"

# Add the run scripts and databases to the image in the PATH
ADD dbs/silva.bacteria/silva.bacteria.fasta /usr/local/dbs/
ADD dbs/silva.bacteria/silva.bacteria.gg.tax /usr/local/dbs/
ADD run_classify_seqs.py /bin/
ADD run_mothur_from_fastq.py /bin/

# Use /scratch as the working directory
RUN mkdir /scratch
WORKDIR /scratch

# Run tests
ADD tests/ /usr/local/tests/
RUN bats /usr/local/tests/
