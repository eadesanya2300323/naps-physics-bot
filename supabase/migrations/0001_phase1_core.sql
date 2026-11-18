create extension if not exists pgcrypto;
create extension if not exists pg_trgm;

create table students (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint unique,
  auth_user_id uuid unique,
  username text,
  display_name text,
  level text check (level in ('100', '200', '300', '400')),
  active boolean not null default true,
  banned boolean not null default false,
  muted_until timestamptz,
  notify_uploads boolean not null default true,
  created_at timestamptz not null default now(),
  last_seen timestamptz not null default now(),
  check (telegram_id is not null or auth_user_id is not null)
);

create table admins (
  telegram_id bigint primary key,
  role text not null check (role in ('super', 'moderator', 'uploader')),
  added_by bigint,
  added_at timestamptz not null default now()
);

create table courses (
  code text primary key,
  title text not null,
  level text not null check (level in ('100', '200', '300', '400')),
  semester smallint check (semester in (1, 2))
);

create table materials (
  id bigserial primary key,
  course_code text references courses(code) on delete cascade,
  category text not null check (category in ('pq', 'notes', 'test', 'assign', 'template', 'other')),
  title text not null,
  year int,
  semester smallint,
  lecturer text,
  storage_path text not null,
  mime_type text,
  size_bytes bigint,
  sha256 text not null unique,
  telegram_file_id text,
  version int not null default 1,
  is_current boolean not null default true,
  is_key boolean not null default false,
  added_by bigint not null,
  created_at timestamptz not null default now()
);

create table usage_events (
  id bigserial primary key,
  student_id uuid,
  source text not null check (source in ('bot', 'web')),
  kind text not null,
  ref text,
  created_at timestamptz not null default now()
);

create table audit_log (
  id bigserial primary key,
  actor bigint not null,
  action text not null,
  target text,
  created_at timestamptz not null default now()
);

create table settings (
  key text primary key,
  value text
);

create index students_level_idx on students (level);
create index students_active_idx on students (active);
create index students_banned_idx on students (banned);
create index students_notify_idx on students (level, notify_uploads) where telegram_id is not null;

create index admins_role_idx on admins (role);

create index courses_level_idx on courses (level);
create index courses_semester_idx on courses (semester);
create index courses_title_trgm_idx on courses using gin (title gin_trgm_ops);

create index materials_course_idx on materials (course_code);
create index materials_category_idx on materials (category);
create index materials_current_idx on materials (is_current);
create index materials_key_idx on materials (is_key) where is_key;
create index materials_added_by_idx on materials (added_by);
create index materials_year_idx on materials (year);
create index materials_semester_idx on materials (semester);
create index materials_lecturer_idx on materials (lecturer);
create index materials_created_idx on materials (created_at desc);
create index materials_listing_idx on materials (course_code, category, is_current desc, year desc nulls last);
create index materials_identity_idx on materials (course_code, category, lower(title), coalesce(year, 0));
create index materials_title_trgm_idx on materials using gin (title gin_trgm_ops);
create index materials_course_code_trgm_idx on materials using gin (course_code gin_trgm_ops);

create index usage_events_student_idx on usage_events (student_id);
create index usage_events_created_idx on usage_events (created_at desc);
create index usage_events_source_idx on usage_events (source);
create index usage_events_kind_idx on usage_events (kind);

create index audit_log_actor_idx on audit_log (actor);
create index audit_log_created_idx on audit_log (created_at desc);

alter table students enable row level security;
alter table admins enable row level security;
alter table courses enable row level security;
alter table materials enable row level security;
alter table usage_events enable row level security;
alter table audit_log enable row level security;
alter table settings enable row level security;
