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

@test "run_classify_seqs.py" {
  run_classify_seqs.py --ref-fasta /usr/local/tests/test_db.fasta --ref-taxonomy /usr/local/tests/test_db.tax --output-folder /usr/local/tests/ --input /usr/local/tests/test_query.fasta
  
  python /usr/local/tests/test_run_classify_seqs.py
}
