#!/usr/bin/env bats

@test "Python is present" {
  result="$(python -c 'print(2+2)')"
  [ "$result" -eq 4 ]
}

@test "fastq-dump" {
	output="$(fastq-dump --stdout -X 2 SRR390728)"
	correct_output="$(cat /usr/local/tests/fastq-dump-output.fastq)"

	[ "$output" == "$correct_output" ]
}

@test "AWS CLI v1.11.13" {
  v="$(aws --version 2>&1)"
  [[ "$v" =~ "1.11.13" ]]
}


@test "Curl v7.47.0" {
  v="$(curl --version)"
  [[ "$v" =~ "7.47.0" ]]
}

@test "run_classify_seqs.py" {
  run_classify_seqs.py --ref-fasta /usr/local/tests/test_db.fasta --ref-taxonomy /usr/local/tests/test_db.tax --output-folder /usr/local/tests/ --input "/usr/local/tests/test - query.fasta" --sample-name test_query
  
  python /usr/local/tests/test_run_classify_seqs.py /usr/local/tests/test_query.json.gz
}

@test "run_classify_seqs.py - clean filename" {
  run_classify_seqs.py --ref-fasta /usr/local/tests/test_db.fasta --ref-taxonomy /usr/local/tests/test_db.tax --output-folder /usr/local/tests/ --input /usr/local/tests/test_query.fasta --sample-name test_query
  
  python /usr/local/tests/test_run_classify_seqs.py /usr/local/tests/test_query.json.gz
}

@test "run_classify_seqs.py - fastq_to_fasta" {
  run_classify_seqs.py --ref-fasta /usr/local/tests/test_db.fasta --ref-taxonomy /usr/local/tests/test_db.tax --output-folder /usr/local/tests/ --input /usr/local/tests/test_query2.fastq --sample-name test_query2
  
  python /usr/local/tests/test_run_classify_seqs.py /usr/local/tests/test_query2.json.gz
}
