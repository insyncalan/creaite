Plan #85 before/after (dev/tests/test_lost_click.py, CREAITE_LOST_CLICK_SHOTS=<folder>).
The mouse is pressed on ABC-A-001's ID in Work, a full data refresh (reloadData) runs while the button is down, then released.
before/row-held.png  button down, the table already redrawn under the pointer
before/row-after.png after release: nothing opened (the click went to the table, not the row)
after/row-held.png   button down, the table not yet redrawn (the refresh waits for the click)
after/row-after.png  after release: ABC-A-001 opens in the panel; the refresh then redraws
