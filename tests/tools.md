# Tools Differences

| **ToolRunned** | **minNumRepeats** | **MinRepeatConservation** | **minRepeatLenght** | **maxRepeatLenght** | **minSpacerLength** | **maxSpacerLength** | **searchWL** | **MinLocalAlignmentLength** | **MinLocalAlignIdentity** | **min/max_repeatLenRatio** | **min/max_spacerLenRatio** | **** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **MincedDefault** | 3 |  | 23 | 47 | 26 | 50 | 8 |  |  |  |  |  |
| **MincedPaper** | 3 |  | 16 | 128 | 16 | 128 | 8 |  |  |  |  |  |
| **Pilercr_1(Default)** | 3 | 0.9 | 16 | 64 | 8 | 64 |  | 16 | 0.94 | 0.9 | 0.75 |  |
| **Pilercr_2** | 3 | 0.8 | 16 | 128 | 8 | 128 |  | 16 | 0.85 | 0.9 | 0.75 |  |
| **CRISPRDetect3** | 3 |  | 23 |  |  | 125 (500) | 11 |  |  |  |  |  |
| **CRISPRDetect3(online)** | 3 |  | 11 |  |  | 125 | 11 |  |  |  |  |  |


# Tools time

## Minced
- Default (0m0.707s)
`minced M1856252453.fna > M1856252453_default.minced`

- Paper (0m5.144s)
`minced -minNR 3 -minRL 16 -maxRL 128 -minSL 16 -maxSL 128 M1856252453.fna > M1856252453_paper.minced`


## Piler
- Default info (0m1.288s)
`pilercr -in M1856252453.fna -out M1856252453_info.pilercr`

- Paper_1 (default no info) (0m1.070s)
`pilercr -noinfo -in M1856252453.fna -out M1856252453_1.pilercr`

- Paper_2 (0m4.478s)
`pilercr -noinfo -minarray 3 -mincons 0.8 -minid 0.85 -maxrepeat 128 -maxspacer 128 -in M1856252453.fna -out M1856252453_2.pilercr`
```sh
   0 s       6 Mb (  0%)  Reading sequences from M1856252453.fna
   0 s      44 Mb (  4%)  100.00%  
   0 s      44 Mb (  4%)  352 sequences, total length 4197189 bases (4 Mb)
   0 s      46 Mb (  4%)  100.00%  Allocating index
   1 s      46 Mb (  4%)  100.00%  Filtering
   1 s      45 Mb (  4%)  997198 filter hits
   1 s      45 Mb (  4%)  Read filter hits
   1 s      57 Mb (  5%)  997198 filter hits
   1 s      57 Mb (  5%)  Merge filter hits
   2 s      60 Mb (  6%)  470829 trapezoids, total length 4071867
   2 s      60 Mb (  6%)  Initializing trapezoid alignment
   5 s      71 Mb (  7%)  100.00%  Aligning trapezoids
   5 s      71 Mb (  7%)  Removing redundant hits
   5 s      71 Mb (  7%)  Sorting hits
   5 s      71 Mb (  7%)  1563 DP hits, 1531 accepted
   5 s      71 Mb (  7%)  0 discarded hits
   5 s      71 Mb (  7%)  Converting hits to images
   5 s      71 Mb (  7%)  Sorting images
   5 s      71 Mb (  7%)  Finding piles
   5 s      71 Mb (  7%)  2505 piles found
   5 s      71 Mb (  7%)  Building graph
   5 s      71 Mb (  7%)  Find connected components
   5 s      71 Mb (  7%)  44 connected components
   5 s      71 Mb (  7%)  Find arrays
   5 s      71 Mb (  7%)  5 arrays found
   5 s      71 Mb (  7%)  Creating report
   5 s      33 Mb (  3%)  Done
   5 s      33 Mb (  3%)  Elapsed time 5 secs, peak mem use 71 Mb
```


## CRISPRDetect

- Default (-flank) (default +direction) (0m6.596s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -left_flank_length 0 -right_flank_length 0 -f M1023330751.fna -o M1023330751_default.CRISPRDetect3 > M1023330751_default.log`
```sh
	Checking 121 sequences for CRISPR like sequence repeats.
	Total 18 sequences identified to have CRISPR like sequence repeats.

	Putative CRISPRs prediction done.
	Total putative CRISPRs to process: 3 from 3 sequences
	Processing: NODE_492_length_39267_cov_15.735 	 Remaining: 2
	Processing: NODE_805_length_25269_cov_18.2314 	 Remaining: 1
	Processing: NODE_313_length_55098_cov_16.9228 	 Remaining: 0
	  Array_quality_score= 4.53
	  Array_quality_score= 3.02
NA-0,,1
```

- Default - direction (0m6.098s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -f M1023330751.fna -o M1023330751_NOdirection.CRISPRDetect3 > M1023330751_NOdirection.log`
```sh
	Checking 121 sequences for CRISPR like sequence repeats.
	Total 18 sequences identified to have CRISPR like sequence repeats.

	Putative CRISPRs prediction done.
	Total putative CRISPRs to process: 3 from 3 sequences
	Processing: NODE_492_length_39267_cov_15.735 	 Remaining: 2
	Processing: NODE_805_length_25269_cov_18.2314 	 Remaining: 1
	Processing: NODE_313_length_55098_cov_16.9228 	 Remaining: 0
	  Array_quality_score= 4.53
	  Array_quality_score= 3.02
NA-0,,1
```

- Default + cpu ALL/3 + direction (0m7.369s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 1 -T 64 -left_flank_length 0 -right_flank_length 0 -f M1023330751.fna -o M1023330751_cpu64_direction.CRISPRDetect3 > M1023330751_cpu64_direction.log`
```sh
	Putative CRISPRs prediction done.
	Total putative CRISPRs to process: 11 from 9 sequences
	Processing: NODE_492_length_39267_cov_15.735 	 Remaining: 8
	Processing: NODE_697_length_29393_cov_18.2393 	 Remaining: 7
	Processing: NODE_718_length_28741_cov_16.7331 	 Remaining: 6
	Processing: NODE_777_length_26603_cov_17.39 	 Remaining: 5
	Processing: NODE_805_length_25269_cov_18.2314 	 Remaining: 4
	Processing: NODE_261_length_62767_cov_15.0645 	 Remaining: 3
	Processing: NODE_940_length_20876_cov_18.6656 	 Remaining: 2
	Processing: NODE_955_length_20547_cov_18.0301 	 Remaining: 1
	Processing: NODE_313_length_55098_cov_16.9228 	 Remaining: 0
	  Array_quality_score= 4.53
	  Array_quality_score= 3.02
NA-0,,1
	  Array_quality_score= 0.74
	  Array_quality_score= 2.13
	  Array_quality_score= 1.69
	  Array_quality_score= 0.74
```

- Default + cpu ALL/3 - direction (0m7.948s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -T 64 -left_flank_length 0 -right_flank_length 0 -f M1023330751.fna -o M1023330751_cpu64_NOdirection.CRISPRDetect3 > M1023330751_cpu64_NOdirection.log`
```sh
	Putative CRISPRs prediction done.
	Total putative CRISPRs to process: 11 from 9 sequences
	Processing: NODE_492_length_39267_cov_15.735 	 Remaining: 8
	Processing: NODE_697_length_29393_cov_18.2393 	 Remaining: 7
	Processing: NODE_718_length_28741_cov_16.7331 	 Remaining: 6
	Processing: NODE_777_length_26603_cov_17.39 	 Remaining: 5
	Processing: NODE_805_length_25269_cov_18.2314 	 Remaining: 4
	Processing: NODE_261_length_62767_cov_15.0645 	 Remaining: 3
	Processing: NODE_940_length_20876_cov_18.6656 	 Remaining: 2
	Processing: NODE_955_length_20547_cov_18.0301 	 Remaining: 1
	Processing: NODE_313_length_55098_cov_16.9228 	 Remaining: 0
	  Array_quality_score= 4.53
	  Array_quality_score= 3.02
NA-0,,1
	  Array_quality_score= 2.13
	  Array_quality_score= 0.74
	  Array_quality_score= 1.69
	  Array_quality_score= 0.74
```

- Default + cpu ALL/3 - direction + cas ()
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -T 64 -left_flank_length 0 -right_flank_length 0 -annotate_cas_genes 1 -f M1023330751.fna -o M1023330751_cpu64_NOdirection_cas.CRISPRDetect3 > M1023330751_cpu64_NOdirection_cas.log`

- Default + cpu ALL/3 + direction + cas ()
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 1 -T 64 -left_flank_length 0 -right_flank_length 0 -annotate_cas_genes 1 -f M1023330751.fna -o M1023330751_cpu64_direction_cas.CRISPRDetect3 > M1023330751_cpu64_direction_cas.log`

- Default (real, with \n) + cpu ALL/3 - direction
```sh
	Putative CRISPRs prediction done.
	Total putative CRISPRs to process: 11 from 9 sequences
	Processing: NODE_492_length_39267_cov_15.735 	 Remaining: 8
	Processing: NODE_697_length_29393_cov_18.2393 	 Remaining: 7
	Processing: NODE_718_length_28741_cov_16.7331 	 Remaining: 6
	Processing: NODE_777_length_26603_cov_17.39 	 Remaining: 5
	Processing: NODE_805_length_25269_cov_18.2314 	 Remaining: 4
	Processing: NODE_261_length_62767_cov_15.0645 	 Remaining: 3
	Processing: NODE_940_length_20876_cov_18.6656 	 Remaining: 2
	Processing: NODE_955_length_20547_cov_18.0301 	 Remaining: 1
	Processing: NODE_313_length_55098_cov_16.9228 	 Remaining: 0
	  Array_quality_score= 4.49
	  Array_quality_score= 3.02
NA-0,,1
	  Array_quality_score= 0.74
	  Array_quality_score= 2.13
	  Array_quality_score= 1.69
	  Array_quality_score= 0.74
```





- Default (0m13.719s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -left_flank_length 0 -right_flank_length 0 -check_direction 0 -left_flank_length 0 -right_flank_length 0 -f M1856252453.fna -o M1856252453.CRISPRDetect3`
```sh
        Checking 352 sequences for CRISPR like sequence repeats.
        Total 8 sequences identified to have CRISPR like sequence repeats.

        Putative CRISPRs prediction done.
        Total putative CRISPRs to process: 2 from 2 sequences
        Processing: NODE_6421_length_4372_cov_9.0278     Remaining: 1
        Processing: NODE_1078_length_18534_cov_9.17663   Remaining: 0
          Array_quality_score= 3.96
          Array_quality_score= 4.83
```

- Default + cpu ALL (0m7.766s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -T 0 -left_flank_length 0 -right_flank_length 0 -f M1856252453.fna -o M1856252453_cpu.CRISPRDetect3`
```sh
        Putative CRISPRs prediction done.
        Total putative CRISPRs to process: 9 from 8 sequences
        Processing: NODE_2107_length_11003_cov_7.28051   Remaining: 7
        Processing: NODE_2676_length_8889_cov_6.11014    Remaining: 6
        Processing: NODE_6421_length_4372_cov_9.0278     Remaining: 5
        Processing: NODE_7308_length_3937_cov_9.54946    Remaining: 4
        Processing: NODE_7552_length_3829_cov_11.4221    Remaining: 3
        Processing: NODE_1078_length_18534_cov_9.17663   Remaining: 2
        Processing: NODE_1096_length_18384_cov_9.25321   Remaining: 1
        Processing: NODE_1427_length_14859_cov_9.23636   Remaining: 0
          Array_quality_score= 3.96
          Array_quality_score= 4.76
          Array_quality_score= 4.83
LEFT-8,RIGHT-16,,1
          Array_quality_score= 0.22
```

- Default + check_direction (0m8.414s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 1 -T 0 -left_flank_length 0 -right_flank_length 0 -f M1856252453.fna -o M1856252453_direction.CRISPRDetect3`

- Default + cas (0m27.638s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -T 0 -left_flank_length 0 -right_flank_length 0 -annotate_cas_genes 1 -f M1856252453.fna -o M1856252453_cas.CRISPRDetect3`

