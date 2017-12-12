#!/usr/bin/python
"""Test the run_classify_seqs.py command."""

import os
import gzip
import json

fp = '/usr/local/tests/test_query.fasta.json.gz'
assert os.path.exists(fp)
result = json.load(gzip.open(fp))

assert "metadata" in result
assert "read_level" in result
assert "summary" in result

assert result["read_level"][0]["header"] == "CP023429_2152770_2154320"
assert result["read_level"][0]["taxonomy"] == "root(100);cellular organisms(100);Bacteria(100);Proteobacteria(100);Betaproteobacteria(100);Neisseriales(100);Neisseriaceae(100);Neisseria(100);Neisseria sp. 10022(100);Neisseria sp. 10022_unclassified(100);"  # noqa
