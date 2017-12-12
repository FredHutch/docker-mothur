#!/usr/bin/python
"""Functions that help with executing system commands."""

import os
import json
import logging
import subprocess


def run_cmds(commands, retry=0, catchExcept=False):
    """Run commands and write out the log, combining STDOUT & STDERR."""
    logging.info("Commands:")
    logging.info(' '.join(commands))
    p = subprocess.Popen(commands,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    stdout, stderr = p.communicate()
    exitcode = p.wait()
    if stdout:
        logging.info("Standard output of subprocess:")
        for line in stdout.split('\n'):
            logging.info(line)
    if stderr:
        logging.info("Standard error of subprocess:")
        for line in stderr.split('\n'):
            logging.info(line)

    # Check the exit code
    if exitcode != 0 and retry > 0:
        msg = "Exit code {}, retrying {} more times".format(exitcode, retry)
        logging.info(msg)
        run_cmds(commands, retry=retry - 1)
    elif exitcode != 0 and catchExcept:
        msg = "Exit code was {}, but we will continue anyway"
        logging.info(msg.format(exitcode))
    else:
        assert exitcode == 0, "Exit code {}".format(exitcode)


def return_results(out, read_prefix, output_folder, temp_folder):
    """Write out the final results as JSON and copy to the output."""
    # Make a temporary file
    temp_fp = os.path.join(temp_folder, read_prefix + '.json')
    with open(temp_fp, 'wt') as fo:
        json.dump(out, fo)
    # Compress the output
    run_cmds(['gzip', temp_fp])
    temp_fp = temp_fp + '.gz'

    if output_folder.startswith('s3://'):
        # Copy to S3
        run_cmds(
            ['aws', 's3', 'cp', '--quiet',
             '--sse', 'AES256',
             temp_fp, output_folder])
    else:
        # Copy to local folder
        run_cmds(['mv', temp_fp, output_folder])


def fastq_to_fasta(fastq_in, fasta_out):
    """Convert FASTQ to FASTA."""
    n_headers = 0
    n_seqs = 0
    with open(fastq_in, "rt") as fi:
        with open(fasta_out, "wt") as fo:
            for ix, line in enumerate(fi):
                if ix % 4 == 0:
                    # Skip empty lines
                    if len(line) <= 1:
                        continue
                    # Header line
                    assert line[0] == '@', line
                    line = "@{}".format(line[1:])
                    fo.write(line)
                    n_headers += 1
                elif ix % 4 == 1:
                    # Sequence line
                    fo.write(line)
                    n_seqs += 1
                elif ix % 4 == 2:
                    # Spacer line
                    assert line[0] == "+"

    assert n_headers == n_seqs
    logging.info("Converted {} records to FASTA".format(n_headers))
