BEGIN TRANSACTION;
CREATE TABLE actions (
  id           TEXT PRIMARY KEY CHECK (id GLOB '[A-Z]*-A-[0-9][0-9][0-9]' AND length(id) BETWEEN 9 AND 13 AND substr(id, 1, length(id) - 6) NOT GLOB '*[^A-Z0-9]*'),
  project      TEXT NOT NULL REFERENCES projects(code),
  description  TEXT NOT NULL,
  workstream   TEXT,
  owner        TEXT NOT NULL DEFAULT 'TBC',   -- Alan's own actions use his full name (settings identity); no separate 'mine' flag
  priority     TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Urgent','High','Medium','Low')),
  due_date     TEXT CHECK (due_date IS NULL OR due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  status       TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Delayed','Closed','Cancelled')),  -- Delayed counts as open
  raised       TEXT NOT NULL,
  closed       TEXT CHECK (closed IS NULL OR closed >= raised),
  latest_update TEXT,
  client_visible INTEGER NOT NULL DEFAULT 0 CHECK (client_visible IN (0,1)),
  client_message TEXT NOT NULL DEFAULT ('What it is: ' || char(10) || 'What it means for you: ' || char(10) || 'What is being done: '),  -- three headings always present; must be complete when client_visible = 1 (checked by tracker.py)
  milestone    TEXT REFERENCES milestones(id),
  source       TEXT NOT NULL,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO "actions" VALUES('ABC-A-001','ABC','Send revised SOW to client',NULL,'Sara Khan','High','2030-06-14','Open','2026-10-01',NULL,NULL,0,'What it is: 
What it means for you: 
What is being done: ',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','2026-10-12 11:46:39.241');
CREATE TABLE applies (
  apply_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  at          TEXT NOT NULL DEFAULT (datetime('now')),
  proposals   TEXT NOT NULL,            -- JSON list of proposal files
  file_ops    TEXT,                     -- JSON list of file operations performed
  undone_at   TEXT                      -- set when undone
);
INSERT INTO "applies" VALUES(1,'2026-10-12 11:46:34.437','["system/staging/proposed-step1.json"]','[]',NULL);
INSERT INTO "applies" VALUES(2,'2026-10-12 11:46:37.352','["system/staging/proposed-step2.json"]','[]',NULL);
INSERT INTO "applies" VALUES(3,'2026-10-12 11:46:39.241','["system/staging/proposed-step3.json"]','[]',NULL);
CREATE TABLE change_log (
  at         TEXT NOT NULL DEFAULT (datetime('now')),
  apply_id   INTEGER REFERENCES applies(apply_id),
  tbl        TEXT NOT NULL,
  item_id    TEXT NOT NULL,
  field      TEXT NOT NULL,
  old_value  TEXT,
  new_value  TEXT,
  op         TEXT NOT NULL DEFAULT 'update' CHECK (op IN ('insert','update','undo')),
  via        TEXT NOT NULL   -- proposal file name, 'dashboard', 'excel-import', 'cx-edit', 'assistant' or 'undo'
);
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','id',NULL,'ABC-A-001','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','project',NULL,'ABC','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','description',NULL,'Send revised SOW to client','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','owner',NULL,'Alan Carter','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','priority',NULL,'High','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','due_date',NULL,'2030-06-14','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','status',NULL,'Open','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','raised',NULL,'2026-10-01','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','client_visible',NULL,'0','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','client_message',NULL,'What it is: 
What it means for you: 
What is being done: ','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','source',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'actions','ABC-A-001','updated_at',NULL,'2026-10-12 11:46:34.438','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','id',NULL,'ABC-002','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','project',NULL,'ABC','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','type',NULL,'Risk','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','description',NULL,'Vendor may slip','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','owner',NULL,'Sara Khan','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','impact',NULL,'High','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','likelihood',NULL,'Medium','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','priority',NULL,'High','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','status',NULL,'Open','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','raised',NULL,'2026-10-01','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','client_visible',NULL,'0','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','client_message',NULL,'What it is: 
What it means for you: 
What is being done: ','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','source',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-002','updated_at',NULL,'2026-10-12 11:46:34.438','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','id',NULL,'ABC-003','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','project',NULL,'ABC','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','type',NULL,'Issue','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','description',NULL,'Test data is late','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','owner',NULL,'Omar Haddad','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','impact',NULL,'Medium','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','status',NULL,'Open','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','raised',NULL,'2026-10-01','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','client_visible',NULL,'0','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','client_message',NULL,'What it is: 
What it means for you: 
What is being done: ','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','source',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'raid','ABC-003','updated_at',NULL,'2026-10-12 11:46:34.438','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','id',NULL,'ABC-D-004','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','project',NULL,'ABC','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','decision',NULL,'Go with vendor A','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','client_visible',NULL,'0','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','client_message',NULL,'','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','date',NULL,'2026-10-01','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','status',NULL,'Made','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','source',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.438',1,'decisions','ABC-D-004','updated_at',NULL,'2026-10-12 11:46:34.438','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','id',NULL,'ABC-D-005','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','project',NULL,'ABC','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','decision',NULL,'Choose the pilot site','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','client_visible',NULL,'0','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','client_message',NULL,'','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','status',NULL,'Pending','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','needed_by',NULL,'2030-06-14','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','source',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'decisions','ABC-D-005','updated_at',NULL,'2026-10-12 11:46:34.438','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','id',NULL,'ABC-P-006','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','project',NULL,'ABC','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','promised_by',NULL,'Alan Carter','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','promised_to',NULL,'Sara Khan','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','description',NULL,'Share the plan','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','due_date',NULL,'2030-06-14','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','status',NULL,'Open','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','raised',NULL,'2026-10-01','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','source',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'promises','ABC-P-006','updated_at',NULL,'2026-10-12 11:46:34.439','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','id',NULL,'ABC-M-001','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','project',NULL,'ABC','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','name',NULL,'Go-live','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','baseline_date',NULL,'2030-06-14','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','forecast_date',NULL,'2030-06-14','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','status',NULL,'Planned','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','sort_order',NULL,'0','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','state_set',NULL,'0','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','client_visible',NULL,'0','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','source',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'milestones','ABC-M-001','updated_at',NULL,'2026-10-12 11:46:34.439','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'workstreams','ABC-W-001','id',NULL,'ABC-W-001','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'workstreams','ABC-W-001','project',NULL,'ABC','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'workstreams','ABC-W-001','name',NULL,'Data','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'workstreams','ABC-W-001','status',NULL,'Active','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'workstreams','ABC-W-001','created',NULL,'2026-10-01','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'workstreams','ABC-W-001','source',NULL,'Alan (cx-edit)','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:34.439',1,'workstreams','ABC-W-001','updated_at',NULL,'2026-10-12 11:46:34.439','insert','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'actions','ABC-A-001','owner','Alan Carter','Sara Khan','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'actions','ABC-A-001','status','Open','Closed','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'actions','ABC-A-001','closed',NULL,'2026-10-12','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'actions','ABC-A-001','updated_at','2026-10-12 11:46:34.438','2026-10-12 11:46:37.354','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'raid','ABC-002','likelihood','Medium','High','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'raid','ABC-002','priority','High','Urgent','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'raid','ABC-002','updated_at','2026-10-12 11:46:34.438','2026-10-12 11:46:37.354','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'decisions','ABC-D-005','date',NULL,'2026-10-02','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'decisions','ABC-D-005','status','Pending','Made','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'decisions','ABC-D-005','updated_at','2026-10-12 11:46:34.438','2026-10-12 11:46:37.354','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'promises','ABC-P-006','status','Open','Done','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'promises','ABC-P-006','closed',NULL,'2026-10-12','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'promises','ABC-P-006','updated_at','2026-10-12 11:46:34.439','2026-10-12 11:46:37.354','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'milestones','ABC-M-001','forecast_date','2030-06-14','2030-06-21','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'milestones','ABC-M-001','percent_complete',NULL,'40','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'milestones','ABC-M-001','updated_at','2026-10-12 11:46:34.439','2026-10-12 11:46:37.354','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'projects','ABC','health',NULL,'At risk','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'projects','ABC','health_reason',NULL,'Vendor slip','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:37.354',2,'projects','ABC','updated_at','2026-10-12 11:46:34.291','2026-10-12 11:46:37.354','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:39.242',3,'actions','ABC-A-001','status','Closed','Open','update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:39.242',3,'actions','ABC-A-001','closed','2026-10-12',NULL,'update','cx-edit');
INSERT INTO "change_log" VALUES('2026-10-12 11:46:39.242',3,'actions','ABC-A-001','updated_at','2026-10-12 11:46:37.354','2026-10-12 11:46:39.241','update','cx-edit');
CREATE TABLE decisions (
  id           TEXT PRIMARY KEY CHECK (id GLOB '[A-Z]*-D-[0-9][0-9][0-9]' AND length(id) BETWEEN 9 AND 13 AND substr(id, 1, length(id) - 6) NOT GLOB '*[^A-Z0-9]*'),
  project      TEXT NOT NULL REFERENCES projects(code),
  decision     TEXT NOT NULL,
  made_by      TEXT,
  client_visible INTEGER NOT NULL DEFAULT 0 CHECK (client_visible IN (0,1)),
  client_message TEXT NOT NULL DEFAULT '',   -- plain wording (no headings); required when client_visible = 1 (checked by tracker.py)
  date         TEXT CHECK (date IS NULL OR date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  status       TEXT NOT NULL DEFAULT 'Made' CHECK (status IN ('Pending','Made','Withdrawn')),
  needed_by    TEXT CHECK (needed_by IS NULL OR needed_by GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  reasoning    TEXT,
  options      TEXT,
  revisit      TEXT,                         -- a date (YYYY-MM-DD) or a trigger in words ("revisit if adoption falls below 60%")
  replaces     TEXT REFERENCES decisions(id),
  source       TEXT NOT NULL,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (status <> 'Made' OR date IS NOT NULL),
  CHECK (replaces IS NULL OR replaces <> id)
);
INSERT INTO "decisions" VALUES('ABC-D-004','ABC','Go with vendor A',NULL,0,'','2026-10-01','Made',NULL,NULL,NULL,NULL,NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','2026-10-12 11:46:34.438');
INSERT INTO "decisions" VALUES('ABC-D-005','ABC','Choose the pilot site',NULL,0,'','2026-10-02','Made','2030-06-14',NULL,NULL,NULL,NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','2026-10-12 11:46:37.354');
CREATE TABLE item_labels (
  item_id    TEXT NOT NULL,                  -- an action, RAID item or decision
  label      TEXT NOT NULL REFERENCES labels(name) ON UPDATE CASCADE,
  added_by   TEXT,
  added_at   TEXT NOT NULL DEFAULT (datetime('now')),
  reason     TEXT,
  suggested  INTEGER NOT NULL DEFAULT 0 CHECK (suggested IN (0,1)),   -- 1 = Claude proposed it
  PRIMARY KEY (item_id, label)
);
CREATE TABLE labels (
  name           TEXT PRIMARY KEY COLLATE NOCASE CHECK (length(trim(name)) > 0 AND instr(name, ',') = 0),
  colour         TEXT NOT NULL DEFAULT 'grey',
  note           TEXT,
  behaviour      TEXT NOT NULL DEFAULT 'warn' CHECK (behaviour IN ('warn','exclude')),
  default_choice TEXT NOT NULL DEFAULT 'include' CHECK (default_choice IN ('include','exclude')),
  builtin        INTEGER NOT NULL DEFAULT 0 CHECK (builtin IN (0,1))
);
INSERT INTO "labels" VALUES('Sensitive','red','Commercially or client sensitive','warn','exclude',1);
CREATE TABLE links (
  from_item   TEXT NOT NULL,                 -- the blocker (e.g. a Dependency)
  to_item     TEXT NOT NULL,                 -- what it blocks
  kind        TEXT NOT NULL DEFAULT 'blocks' CHECK (kind IN ('blocks')),
  source      TEXT NOT NULL,
  created     TEXT NOT NULL DEFAULT (date('now')),
  PRIMARY KEY (from_item, to_item, kind),
  CHECK (from_item <> to_item)
);
CREATE TABLE milestones (
  id            TEXT PRIMARY KEY CHECK (id GLOB '[A-Z]*-M-[0-9][0-9][0-9]' AND length(id) BETWEEN 9 AND 13 AND substr(id, 1, length(id) - 6) NOT GLOB '*[^A-Z0-9]*'),
  project       TEXT NOT NULL REFERENCES projects(code),
  name          TEXT NOT NULL,
  description   TEXT,
  baseline_date TEXT CHECK (baseline_date IS NULL OR baseline_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  forecast_date TEXT CHECK (forecast_date IS NULL OR forecast_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  status        TEXT NOT NULL DEFAULT 'Planned' CHECK (status IN ('Planned','Done','Cancelled')),
  sort_order    INTEGER NOT NULL DEFAULT 0,
  percent_complete INTEGER CHECK (percent_complete IS NULL OR percent_complete BETWEEN 0 AND 100),
  state         TEXT CHECK (state IS NULL OR state IN ('Achieved','On track','At risk','Slipped','Overdue')),
  state_set     INTEGER NOT NULL DEFAULT 0 CHECK (state_set IN (0,1)),
  state_reason  TEXT,
  owner         TEXT,             -- a full name from the people register (BL-55)
  actual_date   TEXT CHECK (actual_date IS NULL OR actual_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),   -- the Achieved date
  client_visible INTEGER NOT NULL DEFAULT 0 CHECK (client_visible IN (0,1)),
  client_message TEXT,            -- plain wording; required when client_visible = 1 (checked by tracker.py)
  internal_note TEXT,             -- Alan's own words on Movement; internal only, never in any client output (Alan, 11-10-2026)
  source        TEXT NOT NULL,
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO "milestones" VALUES('ABC-M-001','ABC','Go-live',NULL,'2030-06-14','2030-06-21','Planned',0,40,NULL,0,NULL,NULL,NULL,0,NULL,NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','2026-10-12 11:46:37.354');
CREATE TABLE projects (
  code            TEXT PRIMARY KEY CHECK (length(code) BETWEEN 3 AND 7 AND code GLOB '[A-Z]*' AND code NOT GLOB '*[^A-Z0-9]*'),
  name            TEXT NOT NULL,
  sponsor         TEXT,
  phase           TEXT,
  health          TEXT CHECK (health IN ('On track','At risk','Off track')),
  health_reason   TEXT,
  next_milestone  TEXT,
  milestone_date  TEXT CHECK (milestone_date IS NULL OR milestone_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  active          INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO "projects" VALUES('ABC','Example Programme',NULL,NULL,'At risk','Vendor slip',NULL,NULL,1,'2026-10-12 11:46:37.354');
CREATE TABLE promises (
  id          TEXT PRIMARY KEY CHECK (id GLOB '[A-Z]*-P-[0-9][0-9][0-9]' AND length(id) BETWEEN 9 AND 13 AND substr(id, 1, length(id) - 6) NOT GLOB '*[^A-Z0-9]*'),
  project     TEXT NOT NULL REFERENCES projects(code),
  promised_by TEXT NOT NULL,                 -- full names from the people register (BL-55)
  promised_to TEXT NOT NULL,
  description TEXT NOT NULL,
  due_date    TEXT CHECK (due_date IS NULL OR due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  status      TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Done','Dropped')),
  raised      TEXT NOT NULL,
  closed      TEXT CHECK (closed IS NULL OR closed >= raised),
  source      TEXT NOT NULL,
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO "promises" VALUES('ABC-P-006','ABC','Alan Carter','Sara Khan','Share the plan','2030-06-14','Done','2026-10-01','2026-10-12','projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','2026-10-12 11:46:37.354');
CREATE TABLE raid (
  id           TEXT PRIMARY KEY CHECK (id GLOB '[A-Z]*-[0-9][0-9][0-9]' AND length(id) BETWEEN 7 AND 11 AND substr(id, 1, length(id) - 4) NOT GLOB '*[^A-Z0-9]*'),
  project      TEXT NOT NULL REFERENCES projects(code),
  type         TEXT NOT NULL CHECK (type IN ('Risk','Assumption','Issue','Dependency')),
  workstream   TEXT,
  description  TEXT NOT NULL,
  owner        TEXT NOT NULL DEFAULT 'TBC',
  response_action TEXT,   -- mitigation (risk), resolution (issue), validation (assumption), management (dependency)
  due_date     TEXT CHECK (due_date IS NULL OR due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),  -- target for the response action
  impact       TEXT CHECK (impact IN ('High','Medium','Low')),
  likelihood   TEXT CHECK (likelihood IN ('High','Medium','Low')),
  priority     TEXT CHECK (priority IN ('Urgent','High','Medium','Low')),   -- calculated from impact and likelihood
  status       TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Closed','Cancelled')),
  raised       TEXT NOT NULL,
  closed       TEXT CHECK (closed IS NULL OR closed >= raised),
  client_visible INTEGER NOT NULL DEFAULT 0 CHECK (client_visible IN (0,1)),
  client_message TEXT NOT NULL DEFAULT ('What it is: ' || char(10) || 'What it means for you: ' || char(10) || 'What is being done: '),
  milestone    TEXT REFERENCES milestones(id),
  source       TEXT NOT NULL,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO "raid" VALUES('ABC-002','ABC','Risk',NULL,'Vendor may slip','Sara Khan',NULL,NULL,'High','High','Urgent','Open','2026-10-01',NULL,0,'What it is: 
What it means for you: 
What is being done: ',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','2026-10-12 11:46:37.354');
INSERT INTO "raid" VALUES('ABC-003','ABC','Issue',NULL,'Test data is late','Omar Haddad',NULL,NULL,'Medium',NULL,NULL,'Open','2026-10-01',NULL,0,'What it is: 
What it means for you: 
What is being done: ',NULL,'projects/ABC Example Programme/minutes/2026-10-01 Steering.docx — Actions','2026-10-12 11:46:34.438');
CREATE TABLE rejected (
  fingerprint  TEXT PRIMARY KEY,  -- hash of project + type + normalised description
  rejected_at  TEXT NOT NULL DEFAULT (datetime('now')),
  via          TEXT,
  reason       TEXT,              -- why: Duplicate, Not mine to track, Not an action, or Alan's own words
  duplicate_of TEXT               -- the item this one repeats (an action, RAID item or decision ID), when the reason is Duplicate
);
CREATE TABLE updates (
  week_ending  TEXT NOT NULL,
  project      TEXT NOT NULL REFERENCES projects(code),
  health       TEXT NOT NULL CHECK (health IN ('On track','At risk','Off track')),
  summary      TEXT NOT NULL,
  key_changes  TEXT,
  PRIMARY KEY (week_ending, project)
);
PRAGMA writable_schema=ON;
INSERT INTO sqlite_master(type,name,tbl_name,rootpage,sql)VALUES('table','vault_search','vault_search',0,'CREATE VIRTUAL TABLE vault_search USING fts5(path, project, kind, date, content, tokenize = ''porter unicode61'')');
CREATE TABLE 'vault_search_config'(k PRIMARY KEY, v) WITHOUT ROWID;
INSERT INTO "vault_search_config" VALUES('version',4);
CREATE TABLE 'vault_search_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3, c4);
CREATE TABLE 'vault_search_data'(id INTEGER PRIMARY KEY, block BLOB);
INSERT INTO "vault_search_data" VALUES(1,X'');
INSERT INTO "vault_search_data" VALUES(10,X'00000000000000');
CREATE TABLE 'vault_search_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE 'vault_search_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE workstreams (
  id         TEXT PRIMARY KEY CHECK (id GLOB '[A-Z]*-W-[0-9][0-9][0-9]' AND length(id) BETWEEN 9 AND 13
                                     AND substr(id, 1, length(id) - 6) NOT GLOB '*[^A-Z0-9]*'),
  project    TEXT NOT NULL REFERENCES projects(code),
  name       TEXT NOT NULL CHECK (length(trim(name)) > 0),
  lead       TEXT,                -- a full name from the people register (BL-55)
  keywords   TEXT,                -- comma-separated
  aliases    TEXT,                -- comma-separated, e.g. "UAT" for Testing
  channel    TEXT,                -- Teams channel, optional
  status     TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Closed')),
  created    TEXT NOT NULL CHECK (created GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  source     TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (project, name COLLATE NOCASE)
);
INSERT INTO "workstreams" VALUES('ABC-W-001','ABC','Data',NULL,NULL,NULL,NULL,'Active','2026-10-01','Alan (cx-edit)','2026-10-12 11:46:34.439');
CREATE TRIGGER labels_keep_builtin_delete BEFORE DELETE ON labels WHEN OLD.builtin = 1
  BEGIN SELECT RAISE(ABORT, 'a built-in label cannot be deleted'); END;
CREATE TRIGGER labels_keep_builtin_rename BEFORE UPDATE OF name, builtin ON labels
  WHEN OLD.builtin = 1 AND (NEW.name <> OLD.name OR NEW.builtin = 0)
  BEGIN SELECT RAISE(ABORT, 'a built-in label cannot be renamed'); END;
PRAGMA writable_schema=OFF;
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('applies',3);
COMMIT;
