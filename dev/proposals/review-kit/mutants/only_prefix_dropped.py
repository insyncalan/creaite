#sub: run("tracker.py", "apply", "system/staging/" + name)|||run("tracker.py", "apply", name)
# MUTANT (review kit, k254): {only} on /api/apply hands tracker.py the bare name, not "system/staging/<name>" (#280 round 4's fix removed): tracker.resolve_proposal
# finds a file of the same name in the vault ROOT first, so a planted namesake is applied instead of the staged save. The probe k254-e-onlyname must show LEAK.
