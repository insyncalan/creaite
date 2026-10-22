# Proposal: /api/vip must not return a row's signatures (#236, Stark's review, LOW)

For Alan's approval. `live_server.py` is guarded, so this is NOT applied; `vip-api.diff` is the change (`git apply -p1`).

## Why

`vip_alerts_route` (`POST /api/vip`, the page's 60-second poll) returned every unseen alert as stored in `vip.json`, including the
server-side fields `sigs` and `seen_sig` (the first 160 normalised characters of each staged item's description, so a repeat can be
told from a reword; Claude's wording of an item, not the message's), and `keys` and `ids`. `build_dashboard.ALERT_HIDDEN` already keeps
all four out of the page built at load; only the poll gave them out. The page never reads them (no `sigs`, `seen_sig`, `.keys` or `.ids`
on an alert anywhere in `system/templates/dashboard/src`).

## The change

The route returns each alert without `keys`, `ids`, `sigs` and `seen_sig`. Nothing else changes; `vip.json` keeps them.
Add to `test_followed_needs.py` once applied: POST `/api/vip` and assert none of the four keys is in any alert.
