#!/usr/bin/python
"""Wrapper script to run mothur on a set of FASTQ files."""

import os
import gzip
import uuid
import shutil
import logging
import argparse
import datetime
from Bio.SeqIO.QualityIO import FastqGeneralIterator
from exec_helpers import run_cmds


def gzip_safe_open(fp):
    if fp.endswith(".gz"):
        return gzip.open(fp, "rt")
    else:
        return open(fp, "rt")


def try_splitting_fastq_file(file_path):
    """Try splitting a file into R1 and R2, return None if not possible."""
    assert os.path.exists(file_path)

    # Test to see if the file could be a FASTQ
    # Open a handle for the input
    with gzip_safe_open(file_path) as f:
        if f.read(1) != "@":
            logging.info("{} was not in valid FASTQ format".format(file_path))
            return None

    # Open a handle for the input
    f = gzip_safe_open(file_path)
    
    # Open handles for the output
    r1_fp = file_path + ".R1.fastq"
    r2_fp = file_path + ".R2.fastq"
    r1 = open(r1_fp, "wt")
    r2 = open(r2_fp, "wt")

    ix = 0
    for header, seq, qual in FastqGeneralIterator(f):
        if ix % 2 == 0:
            r1.write("@{}\n{}\n+{}\n{}\n".format(
                header, seq, header, qual
            ))
        else:
            r2.write("@{}\n{}\n+{}\n{}\n".format(
                header, seq, header, qual
            ))
        ix += 1

    # Close all of the handles
    r1.close()
    r2.close()
    f.close()

    logging.info("Split {} into {:,} pairs of reads".format(file_path, ix))

    return r1_fp, r2_fp


def make_manifest(folder_with_fastqs, manifest_fp):
    """Go through a folder, split paired-end reads, and write out a manifest file."""
    manifest = {}
    for f in os.listdir(folder_with_fastqs):
        if f.endswith(("q.gz", "q")):
            split_files = try_splitting_fastq_file(os.path.join(folder_with_fastqs, f))
            if split_files is None:
                continue

            sample_name = f
            for n in [".fastq", ".fq", ".gz"]:
                sample_name = sample_name.replace(n, "")
            assert sample_name not in manifest
            manifest[sample_name] = split_files

    with open(manifest_fp, "wt") as fo:
        for sample_name, split_files in manifest.items():
            f1, f2 = split_files
            fo.write("{}\t{}\t{}\n".format(sample_name, f1, f2))


def run_mothur_command(command_string):
    """Run a command in mothur."""
    logging.info("Running mothur command:\n" + command_string)
    batch_file = "mothur.batch." + str(uuid.uuid4()).replace("-", "")
    assert os.path.exists(batch_file) is False
    with open(batch_file, "wt") as fo:
        fo.write(command_string + "\n")
    # Note: this will not catch errors -- need to check manually
    run_cmds(["mothur", batch_file], catchExcept=True)
    os.remove(batch_file)
    

def run_mothur(
    input_folder, 
    output_folder, 
    output_prefix=datetime.datetime.today().strftime('%Y_%m_%d_%H_%M'),
    threads=16,
    temp_folder="/scratch"
):
    """Run mothur end-to-end on a set of FASTQ files."""

    # Set up logging
    log_fp = '{}.log.txt'.format(output_prefix)
    fmt = '%(asctime)s %(levelname)-8s [mothur.workflow] %(message)s'
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

    # Make a temp folder inside the `temp_folder` that can be deleted at end
    temp_folder = os.path.join(
        temp_folder,
        str(uuid.uuid4()).replace("-", "")
    )
    os.mkdir(temp_folder)

    # Copy the database to the temp folder and decompress it
    temp_db_fasta = os.path.join(temp_folder, "silva.bacteria.fasta.gz")
    run_cmds(["cp", "/usr/local/dbs/silva.bacteria.fasta.gz", temp_db_fasta])
    run_cmds(["gunzip", temp_db_fasta])
    temp_db_fasta = temp_db_fasta[:-3]  # Remove the .gz
    # Also copy the tax file
    temp_db_tax = os.path.join(temp_folder, "silva.bacteria.gg.tax")
    run_cmds(["cp", "/usr/local/dbs/silva.bacteria.gg.tax", temp_db_tax])

    # Make sure that the input folder ends with a trailing slash
    assert isinstance(input_folder, str), "Input folder must be a string"
    assert len(input_folder) > 0, "Input folder has length of zero"
    if input_folder[-1] != "/":
        input_folder += "/"
        logging.info("Adding a trailing slash to input folder: " + input_folder + "/")

    # Get the data from the input folder, place it in temp_folder + '/input/'
    temp_folder_input = os.path.join(temp_folder, "input")
    logging.info("Using temp folder for all input data: " + temp_folder_input)

    # Put the input data into the `temp_folder_input`
    if input_folder.startswith("s3://"):
        # Get data from S3
        logging.info("Fetching data from S3")
        run_cmds(["aws", "s3", "sync", input_folder, temp_folder_input])
    else:
        # Get data from a local path
        logging.info("Copying data from local path")
        shutil.move(input_folder, temp_folder_input)

    assert os.path.exists(temp_folder_input)
    logging.info("Done fetching data")
    logging.info("Number of files found in {}: {:,}".format(
        temp_folder_input, len(os.listdir(temp_folder_input))
    ))

    # Make a manifest file
    manifest_fp = os.path.join(temp_folder, output_prefix + ".files")
    assert os.path.exists(manifest_fp) is False
    make_manifest(temp_folder_input, manifest_fp)
    assert os.path.exists(manifest_fp)

    # Run the whole mothur workflow
    # Note: this will not catch errors -- need to check manually by the existance of output files
    run_mothur_command(
        """# mothur workflow
make.contigs(file={manifest_fp}, processors={threads})
screen.seqs(fasta=current, group=current, maxambig=0, maxlength=275)
unique.seqs()
count.seqs(name=current, group=current)
align.seqs(fasta=current, reference=XXX)
unique.seqs(fasta=current, count=current)
pre.cluster(fasta=current, count=current, diffs=2)
classify.seqs(fasta=current, count=current, reference={temp_db_fasta}, taxonomy={temp_db_tax}, cutoff=80)
cluster.split(fasta=current, count=current, taxonomy=current, splitmethod=classify, taxlevel=4, cutoff=0.15)
classify.otu(list=current, count=current, taxonomy=current, label=0.03)
phylotype(taxonomy=current)
make.shared(list=current, count=current, label=1)""".format(
            temp_db_fasta=temp_db_fasta,
            temp_db_tax=temp_db_tax,
            manifest_fp=manifest_fp,
            threads=threads
        )
    )

    for ending in ["precluster.count_table", "precluster.gg.wang.tx.list", "unique.precluster.dist"]:
        assert any([f.endswith(ending) for f in os.listdir(temp_folder)]), "No outputs ending with " + ending

    # Rename the mothur logfile
    for f in os.listdir(temp_folder):
        if f.startswith("mothur") and f.endswith("logfile"):
            new_fp = output_prefix + f
            logging.info("Renaming {} to {}".format(f, new_fp))
            shutil.move(
                os.path.join(temp_folder, f),
                os.path.join(temp_folder, new_fp)
            )


    # Now return all of the results to the output folder
    for f in os.listdir(temp_folder):
        if f.startswith(output_prefix):
            logging.info("Uploading: " + f)
            fp = os.path.join(temp_folder, f)
            if output_folder.startswith("s3://"):
                run_cmds(["aws", "s3", "cp", fp, output_folder])
            else:
                if not os.path.exists(output_folder):
                    os.mkdir(output_folder)
                run_cmds(["cp", fp, output_folder])
        else:            
            logging.info("Skipping: " + f)


    # Delete everything in the temporary folder
    logging.info("Deleting temporary folder {}".format(temp_folder))
    shutil.rmtree(temp_folder)

    # Stop logging
    logging.info("Done")
    logging.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Run mothur on a set of FASTQ files.
    """)

    parser.add_argument("--input-folder",
                        type=str,
                        required=True,
                        help="""Folder containing input files.""")
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

    run_mothur(**args.__dict__)
