create table broadcast_jobs (
  id bigserial primary key,
  kind text not null check (kind in ('alert', 'broadcast')),
  audience text not null check (audience in ('all', 'level')),
  level text check (level in ('100', '200', '300', '400')),
  message text not null,
  ref text,
  status text not null default 'queued' check (status in ('queued', 'sending', 'sent', 'cancelled')),
  sent_count int not null default 0,
  failed_count int not null default 0,
  last_student_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table favorites (
  student_id uuid not null references students(id) on delete cascade,
  material_id bigint not null references materials(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (student_id, material_id)
);

create table recent_views (
  student_id uuid not null references students(id) on delete cascade,
  material_id bigint not null references materials(id) on delete cascade,
  viewed_at timestamptz not null default now(),
  primary key (student_id, material_id)
);

create table opportunities (
  id bigserial primary key,
  kind text not null check (kind in ('internship', 'scholarship', 'siwes', 'competition', 'other')),
  title text not null,
  organisation text,
  description text,
  url text,
  deadline date,
  levels text[],
  archived boolean not null default false,
  created_by bigint not null,
  created_at timestamptz not null default now()
);

create table fyp_topics (
  id bigserial primary key,
  title text not null,
  supervisor text,
  year int,
  area text,
  description text,
  status text not null default 'available' check (status in ('available', 'taken', 'completed')),
  created_by bigint not null,
  created_at timestamptz not null default now()
);

create table feedback (
  id bigserial primary key,
  student_id uuid references students(id) on delete set null,
  kind text not null check (kind in ('suggestion', 'bug', 'report', 'other')),
  body text not null,
  material_id bigint references materials(id) on delete set null,
  status text not null default 'new' check (status in ('new', 'read', 'resolved')),
  created_at timestamptz not null default now()
);

create table event_links (
  id bigserial primary key,
  title text not null,
  description text,
  url text not null,
  event_date date,
  active boolean not null default true
);

create index broadcast_jobs_status_idx on broadcast_jobs (status, id);
create index broadcast_jobs_audience_idx on broadcast_jobs (audience, level);
create index broadcast_jobs_created_idx on broadcast_jobs (created_at desc);

create index favorites_material_idx on favorites (material_id);
create index favorites_created_idx on favorites (created_at desc);

create index recent_views_material_idx on recent_views (material_id);
create index recent_views_viewed_idx on recent_views (viewed_at desc);

create index opportunities_kind_idx on opportunities (kind);
create index opportunities_deadline_idx on opportunities (deadline);
create index opportunities_archived_idx on opportunities (archived);
create index opportunities_created_by_idx on opportunities (created_by);
create index opportunities_levels_idx on opportunities using gin (levels);

create index fyp_topics_status_idx on fyp_topics (status);
create index fyp_topics_supervisor_idx on fyp_topics (supervisor);
create index fyp_topics_area_idx on fyp_topics (area);
create index fyp_topics_year_idx on fyp_topics (year);
create index fyp_topics_created_by_idx on fyp_topics (created_by);
create index fyp_topics_title_trgm_idx on fyp_topics using gin (title gin_trgm_ops);

create index feedback_status_idx on feedback (status);
create index feedback_kind_idx on feedback (kind);
create index feedback_student_idx on feedback (student_id);
create index feedback_material_idx on feedback (material_id);
create index feedback_created_idx on feedback (created_at desc);

create index event_links_active_idx on event_links (active);
create index event_links_date_idx on event_links (event_date);

alter table broadcast_jobs enable row level security;
alter table favorites enable row level security;
alter table recent_views enable row level security;
alter table opportunities enable row level security;
alter table fyp_topics enable row level security;
alter table feedback enable row level security;
alter table event_links enable row level security;
