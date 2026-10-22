#sub: dist = actions_wording(distributed_of(doc))|||dist = actions_wording(doc)
# MUTANT (review kit, k254): the distributed export is re-worded from the INTERNAL record, not from distributed_of(doc): the Internal-only line and row are
# not filtered, so they reach the distributed HTML and Word files. The probe k254-b-actions must show LEAK.
