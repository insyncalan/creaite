# Draft-delivery comment, worded accurately (2.6.3)

`live_server.diff` is comment-only. The #183 block said draft_delivery.py "fails closed" for ask creaite. That holds for plain chats
and held runs (it is not in `reach.SCRIPT_COMMANDS`, so `command_kind` gives "unknown" and `record_problem` and the held rule refuse it),
but a request Alan has confirmed (BL-267) is not held to that, so `created` and `hook` can run there. The comment now says so, and
adds that ask creaite has no Microsoft 365 create-draft tool (actions stay off), so it cannot make a draft itself. No code changes.
