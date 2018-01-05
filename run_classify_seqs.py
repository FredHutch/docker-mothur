#!/usr/bin/python
"""Wrapper script to run classify.seqs, including wrappers for S3 access."""

import os
import uuid
import shutil
import logging
import argparse
from exec_helpers import run_cmds
from exec_helpers import fastq_to_fasta
from exec_helpers import return_results
from s3_helpers import get_file
from s3_helpers import s3_path_exists
from s3_helpers import get_reads_from_url


def classify_seqs(input_str,
                  ref_fasta_fp,
                  ref_fasta_url,
                  ref_taxonomy_fp,
                  ref_taxonomy_url,
                  output_folder,
                  threads=16,
                  temp_folder='/scratch',
                  ksize=8,
                  iters=100):
    """Classify a set of reads with mothur.classify.seqs."""

    # Use the read prefix to name the output and temporary files
    read_prefix = input_str.split('/')[-1]

    # Check to see if the output already exists, if so, skip this sample
    output_fp = output_folder.rstrip('/') + '/' + read_prefix + '.json.gz'
    if output_fp.startswith('s3://'):
        # Check S3
        if s3_path_exists(output_fp):
            msg = "Output already exists, skipping ({})."
            logging.info(msg.format(output_fp))
            return
    else:
        # Check local filesystem
        if os.path.exists(output_fp):
            msg = "Output already exists, skipping ({})."
            logging.info(msg.format(output_fp))
            return

    # Make a temp folder inside the `temp_folder` that can be deleted at end
    temp_folder = os.path.join(
        temp_folder,
        str(uuid.uuid4()).replace("-", "")
    )
    os.mkdir(temp_folder)

    # Get the reads
    read_fp = get_reads_from_url(input_str, temp_folder)

    # If the read name has any forbidden characters, make a clean symlink
    forbidden = [" ", "-"]
    new_filename = read_fp.split('/')[-1]
    for c in forbidden:
        if c in new_filename:
            new_filename = new_filename.replace(c, "_")
    if new_filename != read_fp.split('/')[-1]:
        new_fp = os.path.join(temp_folder, new_filename)
        os.symlink(read_fp, new_fp)
        read_fp = new_fp

    # If the reads are gzipped, unzip them
    if read_fp.endswith(".gz"):
        run_cmds(["gunzip", "-f", read_fp])
        read_fp = read_fp.replace(".gz", "")

    # If the reads are in FASTQ format, convert to FASTA
    for ending in [".fq", ".fastq"]:
        if read_fp.endswith(ending):
            new_fp = read_fp.replace(ending, ".fasta")
            fastq_to_fasta(read_fp, new_fp)
            read_fp = new_fp

    # If the reads have non-standard FASTA suffixes, correct them
    for ending in [".fa", ".fna"]:
        if read_fp.endswith(ending):
            new_fp = read_fp.replace(ending, ".fasta")
            os.rename(read_fp, new_fp)
            read_fp = new_fp

    # Make sure that it ends with ".fasta"
    assert read_fp.endswith(".fasta")

    # Write out a batchfile for mothur to use
    batchfile_fp = os.path.join(temp_folder, "batchfile")
    with open(batchfile_fp, "wt") as fo:
        mothur_cmd =  "classify.seqs(fasta={}, template={}, taxonomy={}, method=wang, ksize={}, iters={}, processors={})" # noqa
        mothur_cmd = mothur_cmd.format(read_fp, ref_fasta_fp, ref_taxonomy_fp,
                                       ksize, iters, threads)
        fo.write(mothur_cmd)

    # Use mothur to run the classify.seqs command
    logging.info("Running mothur.classify.seqs")
    run_cmds(["mothur", batchfile_fp])

    # There is only one file in the output folder with this file ending
    output_files = os.listdir(temp_folder)
    output_per_read = [x for x in output_files if x.endswith(".wang.taxonomy")]
    assert len(output_per_read) == 1, "\n".join(output_files)
    output_per_read = os.path.join(temp_folder, output_per_read[0])

    output_summary = output_per_read.replace(".taxonomy", ".tax.summary")

    output = parse_classify_seqs_output(output_per_read, output_summary)

    # Read in the logs
    logging.info("Reading in the logs")
    logs = open(log_fp, 'rt').readlines()

    # Add more metadata to the results object
    output["metadata"] = {
        "input_path": input_str,
        "input": read_prefix,
        "output_folder": output_folder,
        "logs": logs,
        "ref_fasta_url": ref_fasta_url,
        "ref_tax_url": ref_taxonomy_url
    }

    # Write out the final results as JSON and copy to the output folder
    return_results(output, read_prefix, output_folder, temp_folder)

    # Delete everything in the temporary folder
    logging.info("Deleting temporary folder {}".format(temp_folder))
    shutil.rmtree(temp_folder)


def parse_classify_seqs_output(output_per_read, output_summary):
    """Parse a set of results from the mothur classify.seqs command."""
    output = {
        "read_level": [],
        "summary": []
    }

    # Read the taxonomic assignments per read
    msg = "{} does not exist".format(output_per_read)
    assert os.path.exists(output_per_read), msg
    with open(output_per_read, "rt") as f:
        for line in f:
            # Split up the tab-delimited line
            header, tax_string = line.rstrip("\n").split("\t")
            output["read_level"].append(
                {
                    "header": header,
                    "taxonomy": tax_string
                }
            )

    # Read the taxonomic assignment summary
    msg = "{} does not exist".format(output_summary)
    assert os.path.exists(output_summary), msg
    header = None
    with open(output_summary, "rt") as f:
        for line in f:
            line = line.rstrip("\n").split("\t")
            # Get the header
            if header is None:
                header = line
            else:
                # Store the summary as a list of dicts
                output["summary"].append(
                    dict(zip(header, line))
                )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Run the classify.seqs command within mothur.
    """)

    parser.add_argument("--input",
                        type=str,
                        required=True,
                        help="""Location for input file(s). Comma-separated.
                                (Supported: sra://, s3://, or ftp://).""")
    parser.add_argument("--ref-fasta",
                        type=str,
                        required=True,
                        help="""Reference FASTA file.
                                (Supported: s3://, ftp://, or local path).""")
    parser.add_argument("--ref-taxonomy",
                        type=str,
                        required=True,
                        help="""Reference taxonomy file.
                                (Supported: s3://, ftp://, or local path).""")
    parser.add_argument("--output-folder",
                        type=str,
                        required=True,
                        help="""Folder to place results.
                                (Supported: s3://, or local path).""")
    parser.add_argument("--threads",
                        type=int,
                        default=16,
                        help="Number of threads to use.")
    parser.add_argument("--temp-folder",
                        type=str,
                        default='/scratch',
                        help="Folder used for temporary files.")

    args = parser.parse_args()

    # Set up logging
    log_fp = '{}.log.txt'.format(uuid.uuid4())
    fmt = '%(asctime)s %(levelname)-8s [mothur.classify.seqs] %(message)s'
    logFormatter = logging.Formatter(fmt)
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)

    # Write to file
    fileHandler = logging.FileHandler(log_fp)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    # Also write to STDOUT
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    # Make sure that the reference files have controlled endings
    assert args.ref_fasta.endswith(".fasta")
    assert args.ref_taxonomy.endswith(".tax")

    # Get the reference database files
    ref_fasta_fp = get_file(args.ref_fasta, args.temp_folder)
    ref_taxonomy_fp = get_file(args.ref_taxonomy, args.temp_folder)

    # Align each of the inputs and calculate the overall abundance
    for input_str in args.input.split(','):
        logging.info("Processing input argument: " + input_str)
        classify_seqs(input_str,              # ID for single sample to process
                      ref_fasta_fp,           # Local path to DB for FASTA
                      args.ref_fasta,         # URL for reference FASTA
                      ref_taxonomy_fp,        # Local path to DB for taxonomy
                      args.ref_taxonomy,      # URL for reference taxonomy
                      args.output_folder,     # Place to put results
                      threads=args.threads,
                      temp_folder=args.temp_folder)

    # Stop logging
    logging.info("Done")
    logging.shutdown()
