## CRISPRDetect

- Default (-flank) (0m6.596s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -left_flank_length 0 -right_flank_length 0 -f M1023330751.fna -o M1023330751_default.CRISPRDetect3 > M1023330751_default.log`

- Default (-check_direction) (0m6.098s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -f M1023330751.fna -o M1023330751_NOdirection.CRISPRDetect3 > M1023330751_NOdirection.log`

- Default + cpu ALL (-check_direction) (0m7.760s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -T 0 -left_flank_length 0 -right_flank_length 0 -f M1023330751.fna -o M1023330751_cpu_NOdirection.CRISPRDetect3 > M1023330751_cpu_NOdirection.log`

- Default + cpu ALL (0m8.445s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -T 0 -left_flank_length 0 -right_flank_length 0 -f M1023330751.fna -o M1023330751_cpu.CRISPRDetect3 > M1023330751_cpu.log`

- Default + cpu + direction (0m7.369s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 1 -T 64 -left_flank_length 0 -right_flank_length 0 -f M1023330751.fna -o M1023330751_cpu64_direction.CRISPRDetect3 > M1023330751_cpu64_direction.log`

- Default + cpu ALL/3 (-check_direction) (0m7.948s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -T 64 -left_flank_length 0 -right_flank_length 0 -f M1023330751.fna -o M1023330751_cpu64_NOdirection.CRISPRDetect3 > M1023330751_cpu64_NOdirection.log`

- Default + cpu ALL/3 (-check_direction) + cas ()
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -T 64 -left_flank_length 0 -right_flank_length 0 -annotate_cas_genes 1 -f M1023330751.fna -o M1023330751_cpu64_NOdirection_cas.CRISPRDetect3 > M1023330751_cpu64_NOdirection_cas.log`

- Default + cpu ALL/3 + direction + cas ()
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 1 -T 64 -left_flank_length 0 -right_flank_length 0 -annotate_cas_genes 1 -f M1023330751.fna -o M1023330751_cpu64_direction_cas.CRISPRDetect3 > M1023330751_cpu64_direction_cas.log`






- Default + cas (0m27.638s)
`CRISPRDetect3 -array_quality_score_cutoff 3 -check_direction 0 -T 0 -left_flank_length 0 -right_flank_length 0 -annotate_cas_genes 1 -f M1856252453.fna -o M1856252453_cas.CRISPRDetect3`

