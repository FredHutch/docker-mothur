#!/usr/bin/python
"""Functions that help with downloading or uploading files to S3."""

import os
import boto3
import logging
from exec_helpers import run_cmds
from exec_helpers import fastq_to_fasta
from sra_helpers import get_sra


def s3_path_exists(s3_url):
    """Check to see whether a given path exists on S3."""
    logging.info("Checking whether {} already exists on S3".format(s3_url))
    bucket = s3_url[5:].split('/')[0]
    prefix = '/'.join(s3_url[5:].split('/')[1:])
    client = boto3.client('s3')
    results = client.list_objects(Bucket=bucket, Prefix=prefix)
    if 'Contents' in results:
        logging.info("Output already exists, skipping ({})".format(s3_url))
        return True
    return False


def get_reads_from_url(input_str, temp_folder):
    """Get a set of reads from a URL -- return the downloaded filepath."""
    logging.info("Getting reads from {}".format(input_str))

    filename = input_str.split('/')[-1]
    local_path = os.path.join(temp_folder, filename)

    if not input_str.startswith(('s3://', 'sra://', 'ftp://', 'https://', 'http://')):
        logging.info("Treating as local path")
        assert os.path.exists(input_str)
        logging.info("Making symbolic link in temporary folder")
        os.symlink(input_str, local_path)
        return local_path

    # Make sure the temp folder ends with '/'
    if not temp_folder.endswith("/"):
        temp_folder = "{}/".format(temp_folder)

    logging.info("Filename: " + filename)
    logging.info("Local path: " + local_path)

    # Get files from AWS S3
    if input_str.startswith('s3://'):
        logging.info("Getting reads from S3")
        run_cmds([
            'aws',
            's3',
            'cp',
            '--quiet',
            '--sse',
            'AES256',
            input_str,
            temp_folder
            ])
        return local_path

    # Get files from an FTP server or HTTP
    elif input_str.startswith('ftp://', 'https://', 'http://'):
        logging.info("Getting reads from FTP / HTTP(S)")
        run_cmds(['wget', '-P', temp_folder, input_str])
        return local_path

    # Get files from SRA
    elif input_str.startswith('sra://'):
        accession = filename
        logging.info("Getting reads from SRA: " + accession)
        local_path = get_sra(accession, temp_folder)

        return local_path

    else:
        msg = "Did not recognize prefix to fetch reads: " + input_str
        raise Exception(msg)


def get_file(url, temp_folder):
    """Get a file, return the local filepath."""

    # Get files from AWS S3
    if url.startswith('s3://'):
        logging.info("Getting file from S3: " + url)

        # Set the local path
        local_fp = os.path.join(temp_folder, url.split('/')[-1])

        # Make sure we aren't overwriting anything
        assert os.path.exists(local_fp) is False

        logging.info("Saving file to " + local_fp)
        run_cmds(['aws', 's3', 'cp', '--quiet',
                  '--sse', 'AES256',
                  url, local_fp])

        return local_fp

    else:
        # Treat the input as a local path
        logging.info("Getting reference database from local path: " + url)
        assert os.path.exists(url)

        return url
