#sub: raise DocError("Its project must be one project code.")|||pass
# MUTANT (review kit, k254): creaite_doc.check no longer refuses a project that is not a string (#277 removed): a list or an object goes on to the
# tracker query with a code it can't bind, and the report routes answer a fault (HTTP 500) instead of a plain refusal. The probe k254-a-docproject must show LEAK.
