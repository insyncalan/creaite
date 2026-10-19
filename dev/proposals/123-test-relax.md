# #123: relax the client sheet's "no items" test to what it is for

`test_client_item_links.ClientSheetOffersNoItems.test_the_sheet_editor_has_no_item_picker_slash_menu_or_chips` bans the bare name
`attachSlash` in `SheetText.jsx`. But the text section (H5, #218) uses the Notes `/` menu with the `textsection` profile
(`core/editorProfiles.js`: text, h1-h3, lists, task, quote, code block, table, image, link), whose host callbacks are table and image only:
no note, person or work-item row. The test's aim is that a client sheet cannot insert tracker items.

Patch (in the test, `hook` tuple and after the loop):

```python
for hook in ("attach" + "ItemPick", "insert" + "Hash", "item" + "Chip", "item" + "Options"):      # "attachSlash" no longer listed
    self.assertNotIn(hook, code, f"{name} wires {hook}: a client sheet would offer or draw work items")
# the text section's `/` menu (H5) is the Notes menu with the "textsection" profile, which has no note, person or work-item row
prof = (src.parent.parent / "core" / "editorProfiles.js").read_text(encoding="utf-8")
row = re.search(r"^\s*textsection: \[([^\]]*)\]", prof, re.M).group(1)
for bad in ("item", "note", "person", "mention", "hash", "wiki"):
    self.assertNotIn(bad, row, f"the textsection menu rows offer {bad}")
```

(`import re` at the top if missing.) Place the profile assertion once, after the file loop, not inside it.
