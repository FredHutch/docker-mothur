#!/usr/bin/python
"""Functions that help getting data from NCBI's SRA."""

import os
import logging
import subprocess
from exec_helpers import run_cmds


def get_sra(accession, temp_folder):
    """Get the FASTQ for an SRA accession via ENA."""
    local_path = os.path.join(temp_folder, accession + ".fastq")
    # Download from ENA via FTP
    # See https://www.ebi.ac.uk/ena/browse/read-download for URL format
    url = "ftp://ftp.sra.ebi.ac.uk/vol1/fastq"
    folder1 = accession[:6]
    url = "{}/{}".format(url, folder1)
    if len(accession) > 9:
        if len(accession) == 10:
            folder2 = "00" + accession[-1]
        elif len(accession) == 11:
            folder2 = "0" + accession[-2:]
        elif len(accession) == 12:
            folder2 = accession[-3:]
        else:
            logging.info("This accession is too long: " + accession)
            assert len(accession) <= 12
        url = "{}/{}".format(url, folder2)
    # Add the accession to the URL
    url = "{}/{}/{}".format(url, accession, accession)
    logging.info("Base info for downloading from ENA: " + url)
    # There are three possible file endings
    file_endings = ["_1.fastq.gz", "_2.fastq.gz", ".fastq.gz"]
    # Try to download each file
    for end in file_endings:
        run_cmds(["curl",
                  "-o", os.path.join(temp_folder, accession + end),
                  url + end], catchExcept=True)
    # If none of those URLs downloaded, fall back to trying NCBI
    if any([os.path.exists("{}/{}{}".format(temp_folder, accession, end))
            for end in file_endings]):
        # Combine them all into a single file
        logging.info("Combining into a single FASTQ file")
        with open(local_path, "wt") as fo:
            cmd = "gunzip -c {}/{}*fastq.gz".format(temp_folder, accession)
            gunzip = subprocess.Popen(cmd, shell=True, stdout=fo)
            gunzip.wait()

        # Clean up the temporary files
        logging.info("Cleaning up temporary files")
        for end in file_endings:
            fp = "{}/{}{}".format(temp_folder, accession, end)
            if os.path.exists(fp):
                os.unlink(fp)
    else:
        logging.info("No files found on ENA, trying SRA")
        run_cmds(["fastq-dump", "--outdir", temp_folder, accession])

        # Check to see if the file was downloaded
        msg = "File could not be downloaded from SRA: {}".format(accession)
        assert os.path.exists(local_path), msg

    # Return the path to the file
    logging.info("Done fetching " + accession)
    return local_path
