# G8: Claude by API key (a decision for Alan, not a build)

**The question.** The AI models page offers "Use an API key" for Claude. G1 can keep that key in the keychain, but nothing
uses it. Should creaite's Claude runs (ask creaite, the sweep, Prep, drafts) ever run on an Anthropic API key instead of your
subscription, for example when the subscription's limit is reached (#132 scope (c))? The rule from the done-when stands
whatever you choose: **the key never goes into a run's environment**, because every program a run starts (a creaite script,
anything Claude Code runs) inherits that environment and could read it.

## The options

| | Option | What it means | Risk |
|---|---|---|---|
| A | **Do nothing** | Claude stays on your subscription. The page stops offering "Use an API key" for Claude (a small page change). | None new. At a limit, G6's card says when it resets, and quick edits can go to OpenAI if you allow it. |
| B | **Keys only for providers other than Claude** | As round 1 and 2 build it: the OpenAI key in the keychain, read only by the live server for its own HTTPS call (G2, G4). Claude stays on your subscription; the Claude key option is hidden as in A. | The same as A for Claude. |
| C | **Claude by API key through Claude Code's `apiKeyHelper`** | Each `claude -p` run is told (in the `--settings` creaite already passes) to ask a small creaite helper for the key. Claude Code runs the helper itself, keeps the key in its own memory and sends it to Anthropic. The run's environment never holds it. | The helper is a program that prints the key. It must be refused to every model run by name (as `providers.py` is in G1), in the hook, the wrapper and the permission rules. The hook can't see the helper being run, because Claude Code runs it outside the tool calls. **Not verified:** whether Claude Code passes a helper's key on to the programs its tools start. That needs a real run, and creaite must not rely on it until it has been checked. |
| D | **Claude by API key through a local relay in the live server** | The live server listens on 127.0.0.1 and adds the key to each request on its way to `api.anthropic.com`. A run gets only the relay's address and a token for that run, which stops working when the run ends. The key stays in the live server's memory. | This is the most code. It adds a second outgoing path and a port, and while the run is going, anything in it can use the token to spend your API money. It is a "gateway", which #132 said needs Jarvis's agreement. |

## What each does to the guard

- **A and B** change nothing in the guard.
- **C** adds one script to the never list for runs, as `providers.py` already is. It adds one key, `apiKeyHelper`, to the run's `--settings`. The hook, the tools and approvals don't move.
- **D** adds a network listener. The guard can't see what a run sends to it.

## Recommendation

**B now, plus A's page change.** Keep Claude on your subscription, and hide "Use an API key" for Claude until this is decided.
G6 already covers a limit: the card says when it resets, and quick edits can move to OpenAI when the text allows.

If limits keep getting in the way, **C** is the safer way to use a Claude API key. The key stays out of every environment, and
the change is small and reviewable. Before building it:

1. check, in one real run with a throwaway key, that Claude Code doesn't hand the key to the programs its tools start;
2. set a spend cap on the Anthropic account;
3. get IT's approval of the egress, as for G2.

**D is not recommended.** It is the most code and the most exposure for the same result.
