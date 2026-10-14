# Spike: loading Teams meeting transcripts (BL-42 phase 3)

Run 2026-10-08 (about 23:03 to 23:08 local). Read-only on Microsoft 365. Meetings are called A, B and C; no titles, names, chat text or transcript text appear here.

- **A:** online Teams meeting I organised, transcribed.
- **B:** online Teams meeting I attended (organised by someone else), transcribed.
- **C:** in-person meeting (a room, no Teams), no transcript.

## Result in one line

**One route works, for A and B: the calendar event's `meetingTranscriptUrl`, read with `read_resource`.** It returns the full transcript as WebVTT. The meeting chat can also be read. SharePoint and OneDrive search never found a transcript. C has nothing to fetch.

## Route that worked (exact calls)

1. **Find the event.** `outlook_calendar_search` with `{query: "<title>", afterDateTime: "YYYY-MM-DD", beforeDateTime: "YYYY-MM-DD+1", limit: 10}`.
   - Returns: `uri` (`calendar:///events/<id>`), `id`, `subject`, `organizer` (address only), `attendees` (addresses), `start`/`end` as `{dateTime, timeZone}` (UTC here), `location`, `isOrganizer`, `isCancelled`, `recurrence`, `webLink`, `summary` (short body).
   - **Does not return** whether it is an online meeting, the join URL, the online-meeting ID or the transcript URL. A second call is always needed.
2. **Read the event.** `read_resource` with `{uri: "calendar:///events/<id>"}` (use the `uri` as returned; it is URL-encoded).
   - Returns the full body (HTML), attendees with response status, `sensitivity`, `hasAttachments`, `organizer {name,address}`, `onlineMeeting: {joinUrl}` and `meetingTranscriptUrl`.
   - `meetingTranscriptUrl` has the form `meeting-transcript:///events/<base64url of the join URL>` and, for A, `?start=<ISO>&end=<ISO>` for that occurrence. B's had no start/end.
   - There is **no separate online-meeting ID** in the output. The join URL's thread id (`19:meeting_...@thread.v2`) is the identifier and is also the meeting chat's id.
3. **Fetch the transcript.** `read_resource` with `{uri: "<meetingTranscriptUrl exactly as returned>"}`.
   - Returns JSON: `meeting {id, subject, startDateTime, endDateTime, joinWebUrl, ...}` and `transcripts: [{id, createdDateTime, endDateTime, content}]`.
   - `content` is **WEBVTT** (CRLF line ends): cues `hh:mm:ss.mmm --> hh:mm:ss.mmm` followed by `<v Speaker Name>text</v>`.

## Meeting by meeting

| | Found in calendar | Online Teams meeting | I am organiser | Event ID | Join URL / transcript URL | Transcript |
|---|---|---|---|---|---|---|
| A | yes (1 match) | yes | yes (`isOrganizer: true`) | yes | both present | yes, 1 transcript for the day |
| B | yes (1 match) | yes | no | yes | both present | yes, 1 transcript |
| C | yes (1 match) | no (`onlineMeeting: null`) | no | yes | both null | none |

### A (organised, transcribed)
- Transcript read with the event's own `meetingTranscriptUrl` (with `start`/`end`): exactly one transcript for that day.
- Format and size: WEBVTT, 23,622 bytes, 161 cues, every cue has a speaker tag, covers about 18 min 50 s. Saved to `inbox/` as `2026-10-08 <title>.vtt`.
- **Reusing the join URL matters.** The same Teams meeting (same join URL and chat) had four transcripts over four dates. Without `start`/`end` the call returned all four (168 KB). With them it returned only the day's. Also, `meeting.startDateTime` in the reply is the first date of the series, not the occurrence.
- Meeting chat read as described below. Chat saved beside the transcript as `... - chat.txt` (the four messages posted during the meeting window; system events left out).

### B (attended only)
- **Works exactly as for A.** The attendee's own event carries the transcript URL and the read succeeded, so being only an attendee is no obstacle here.
- One transcript, 61,247 characters (JSON file 64 KB), 312 cues, all with speaker tags, about 51 minutes.
- Not saved to `inbox/` (only A was authorised).
- **Status label: Transcript available.**

### C (in person, no transcript)
- Event found, but it has no online meeting, no join URL and no transcript URL, and so no meeting chat. Nothing to fetch by any route.
- The title searched on SharePoint returned only unrelated files.
- **Status label: No transcript** (nothing to look for). Reserve **Not transcribed** for an online meeting that took place but whose transcript is empty or missing, and **No access** for a permission refusal. Neither was seen in this test; see the rules below.

## Route (a): the meeting chat
- **Finding the chat.** `teams_list_chats` with `{limit: 25}` returns chats with `id`, `chatType` ("meeting"), `topic` (the meeting title), members. The A and B chats were on the first page, but there was a further page (`nextCursor`). **Simpler and certain: the chat id equals the thread id inside the join URL** (checked for A and B), so no listing is needed.
- **Reading it.** `read_resource` with `{uri: "teams:///chats/<chatId>/messages"}` (a URI without `/messages` gives `VALIDATION_ERROR` that lists the valid shapes).
  - Returns up to 50 messages, **ordered by last update, not by sent time**, with a `truncated: true` note. No cursor parameter. The remainder needs `chat_message_search` with `{query: "*", afterDateTime, beforeDateTime}` (works; `ChannelMessage.Read.All` is granted), then filtering results by `chatUri`.
  - `bodyPreview` is cut at about 300 characters. **The full body needs one more call per message:** `read_resource` with `{uri: "teams:///chats/<chatId>/messages/<messageId>"}`.
  - `from` is "Unknown" in lists and null on single reads for system and bot messages; people messages carry a name.
- **What the chat holds besides conversation:** system event messages (`messageType: "unknownFutureValue"`) with `eventDetail` of type `callStartedEventMessageDetail`, `callTranscriptEventMessageDetail` (a transcript was started; carries `callId`), `callRecordingEventMessageDetail` (status `initial`, `chunkFinished`, `success`; a recording URL only on `success`), `callEndedEventMessageDetail` (duration, participants), and members joined or left. Also AI recap messages from the Teams facilitator bot (start, midpoint, wrap-up with a link to a Loop notes page).
- **A transcript event in the chat is a reliable signal that transcription was on**; its absence in an online meeting is a candidate for "Not transcribed".
- `chat_message_search` with keywords (`transcript OR recording OR recap OR "meeting ended"`, a day's window) returned **nothing** for A and B: system events are not searchable and the recap messages did not match. `{query: "*"}` with a window works but returns every chat; summaries are cut at about 100 characters.
- Result: the chat can be fetched, in two steps (list, then each message in full). For a long chat it is many calls.

## Route (b): OneDrive and SharePoint search
- `sharepoint_search` `{query: "<A title>", afterDateTime, limit}`: **0 results**, although a Loop notes file named after the meeting exists in my OneDrive `Meetings` folder (found only by the query used for C, which matched on a person's first name in the file). Title search is **unreliable**.
- `sharepoint_search` `{query: "<B title>", afterDateTime}`: 2 results, both unrelated.
- `sharepoint_search` `{query: "Meeting Transcript", afterDateTime}`: 62 results, none for A or B. The hits were other people's documents (some are Word files made from other meetings' transcripts by other tools), not Teams' own.
- `sharepoint_search` `{query: "Meeting Recording", fileType: "mp4", afterDateTime}`: **0 results**; recordings are not searchable here.
- `sharepoint_folder_search` `{name: "Recordings"}`: 1,002 folders across the tenant; no way to tell mine, so no use.
- The chat's recording event does give a `callRecordingUrl` into the organiser's OneDrive (for A, mine), but it is a video, and for B it is the organiser's OneDrive. Not read.
- **Conclusion: no transcript file was reachable by search for A or B.** Teams here does not leave the transcript as a searchable file; the only route is route (c) below.

## Route (c): other tools
Microsoft 365 tools available: `get_me`, `get_granted_scopes`, `search_people`, `outlook_calendar_search`, `outlook_email_search` and the mail tools, `teams_list_teams`, `teams_list_channels`, `teams_list_channel_messages`, `teams_list_chats`, `chat_message_search`, `sharepoint_search`, `sharepoint_folder_search`, `read_resource`, plus write tools (not used).
- Only `read_resource` with the `meeting-transcript:///` scheme reaches transcripts. There is no tool that lists a meeting's transcripts or fetches a recording or AI insight directly.
- `get_granted_scopes` includes `OnlineMeetingTranscript.Read.All`, `OnlineMeetingRecording.Read.All`, `OnlineMeetingArtifact.Read.All`, `OnlineMeetingAiInsight.Read.All`, `OnlineMeetings.Read`, `Calendars.Read`, `Chat.Read`, `ChannelMessage.Read.All`, `Files.Read.All`, `Sites.Read.All`. No scope is missing for what was done.

## Format and quality
- Format: WEBVTT with `<v Full Name>` voice tags on every cue. Names are full display names (including people from other organisations). **There is no header block** (no title, date or attendee list), so `minutes.py` must supply those from the event.
- Timestamps are `hh:mm:ss.mmm` **relative to the transcript's start** (`createdDateTime`), not clock times. The transcript starts about 30 seconds after the scheduled start.
- Cues are **not in strict start-time order**: short back-channel cues ("Yeah.") are listed after longer cues that started earlier and overlap them. Sort by start time before using, or treat the order as spoken-end order.
- Many single-word back-channel cues; a high share of cues are two or three words.
- Text quality is good for ordinary speech. Product names, acronyms and some personal names are sometimes mis-heard. Punctuation is generally right, but sentences are split across cues.
- No speaker-change problems seen in A or B.

## Timings (rough; one batch of calls at a time, wall-clock including my own turns)
- Whole spike, first call to files written: about 4.5 minutes.
- Step 1, calendar search for three meetings plus two event reads, including one retry: about 35 s.
- Step 2a, chat list and the chat messages for A and B: about 35 s (the 50-message read was the slow call, about 20 s).
- Step 2b, five SharePoint searches: about 16 s.
- Step 2c, transcript reads: about 25 s for A and B together. Fetching A's four-transcript series (168 KB) took longer, about 45 s with two other calls in the batch.
- Per-message chat reads: a second or two each. Writing the files: under 5 s.
- For the real feature, expect per meeting: 2 calls to locate it, 1 to fetch the transcript, and 1 + N for the chat.

## What could make it unreliable
1. **Two calls to learn anything:** calendar search results do not say whether a meeting is online or transcribed; every candidate needs a `read_resource` on the event first.
2. **A dropped connection:** one calendar search failed with `ECONNRESET` and worked on retry. The feature needs a retry.
3. **A reused join URL spans many dates.** Always pass the event's own `start`/`end` (as given in `meetingTranscriptUrl`). Without them, results are capped to the latest few and may not include the day wanted. If an attendee's event for a recurring meeting carries no `start`/`end` (as B's did not, though B was a single event), the day would have to be picked by `createdDateTime`.
4. **Aliases.** The organiser address on A's event is a different domain from my mailbox's. Use `isOrganizer`, not address matching.
5. **Large results.** A result over the tool's size limit is not returned inline; it is saved to a local file by the harness (B, and A's series read, were). Smaller ones come back inline, and the model would have to re-type them to save them, which risks changing the text. Plan to always save through a script from a spooled file, or a way to make the connector write the file.
6. **Chat order and paging.** The chat list is ordered by last update with no cursor and a 50-message cap; old meetings' chats are truncated, so `chat_message_search` plus filtering is needed. Bot messages have no sender name.
7. **Search is not a fallback.** Title search missed an existing file, and recordings are not indexed.
8. **Timing of availability.** The transcript was present hours after the meeting. How soon after the end it appears was not tested; a same-day sweep could find a meeting with a transcript event in the chat but no transcript yet.
9. **Content that should not be stored.** The event body contains a join passcode and dial-in PIN (BL-98 says not to store them). Transcripts can include people from other organisations and anonymous guests.
10. **Labels not exercised.** "Not transcribed" and "No access" did not occur. Suggested rules: *Transcript available* = transcript read returns at least one transcript for the occurrence; *Not transcribed* = online meeting in the past, `meetingTranscriptUrl` present, read succeeds with an empty `transcripts` list (and no transcript event in the chat); *No transcript* = no online meeting or no `meetingTranscriptUrl` (in person, phone, cancelled); *No access* = the read returns a permission or not-found error for a meeting that is online and in the past.
