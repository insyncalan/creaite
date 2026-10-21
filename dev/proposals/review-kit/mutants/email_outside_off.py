#sub: def email_outside(req):\n    """Whether a Draft email request goes to anyone outside (#186)|||def email_outside(req):\n    return False\n    """Whether a Draft email request goes to anyone outside (#186)
# MUTANT (review kit, k26): the Draft email never counts as going outside, so an outside recipient gets the full facts and no reply check.
# (a "#sub:" line: edit_ai.py ends in sys.exit(main()), so an appended function would never be reached)
