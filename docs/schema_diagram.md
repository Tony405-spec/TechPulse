# Superseded: Legacy Schema Diagram

This describes the historical descriptive schema (company, fortune500, stackoverflow, tag_company, tag_type). The current additive canonical contract is migrations/001_canonical_schema.sql; see docs/ARCHITECTURE.md. This file is retained as project history and must not be confused with the current ingestion contract.

```sql
-- Table: public.company

-- DROP TABLE IF EXISTS public.company;

CREATE TABLE IF NOT EXISTS public.company
(
    id integer NOT NULL,
    exchange character varying(10) COLLATE pg_catalog."default",
    ticker character(5) COLLATE pg_catalog."default",
    name character varying COLLATE pg_catalog."default" NOT NULL,
    parent_id integer,
    CONSTRAINT company_pkey PRIMARY KEY (id),
    CONSTRAINT company_ticker_key UNIQUE (ticker),
    CONSTRAINT company_parent_id_fkey FOREIGN KEY (parent_id)
        REFERENCES public.company (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.company
    OWNER to postgres;
-- Table: public.ev311

-- DROP TABLE IF EXISTS public.ev311;

CREATE TABLE IF NOT EXISTS public.ev311
(
    id integer,
    priority text COLLATE pg_catalog."default",
    source text COLLATE pg_catalog."default",
    category text COLLATE pg_catalog."default",
    date_created timestamp without time zone,
    date_completed timestamp without time zone,
    street text COLLATE pg_catalog."default",
    house_num text COLLATE pg_catalog."default",
    zip text COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.ev311
    OWNER to postgres;
-- Table: public.fortune500

-- DROP TABLE IF EXISTS public.fortune500;

CREATE TABLE IF NOT EXISTS public.fortune500
(
    rank integer NOT NULL,
    title character varying COLLATE pg_catalog."default" NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    ticker character(5) COLLATE pg_catalog."default",
    url character varying COLLATE pg_catalog."default",
    hq character varying COLLATE pg_catalog."default",
    sector character varying COLLATE pg_catalog."default",
    industry character varying COLLATE pg_catalog."default",
    employees integer,
    revenues integer,
    revenues_change real,
    profits numeric,
    profits_change real,
    assets numeric,
    equity numeric,
    CONSTRAINT fortune500_pkey PRIMARY KEY (title),
    CONSTRAINT fortune500_name_key UNIQUE (name),
    CONSTRAINT fortune500_employees_check CHECK (employees > 0),
    CONSTRAINT fortune500_assets_check CHECK (assets > 0::numeric)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.fortune500
    OWNER to postgres;
-- Table: public.stackoverflow

-- DROP TABLE IF EXISTS public.stackoverflow;

CREATE TABLE IF NOT EXISTS public.stackoverflow
(
    id integer NOT NULL DEFAULT nextval('stackoverflow_id_seq'::regclass),
    tag character varying(30) COLLATE pg_catalog."default",
    date date,
    question_count integer DEFAULT 0,
    question_pct double precision,
    unanswered_count integer,
    unanswered_pct double precision,
    CONSTRAINT stackoverflow_tag_fkey FOREIGN KEY (tag)
        REFERENCES public.tag_company (tag) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.stackoverflow
    OWNER to postgres;
-- Table: public.tag_company

-- DROP TABLE IF EXISTS public.tag_company;

CREATE TABLE IF NOT EXISTS public.tag_company
(
    tag character varying(30) COLLATE pg_catalog."default" NOT NULL,
    company_id integer,
    CONSTRAINT tag_company_pkey PRIMARY KEY (tag),
    CONSTRAINT tag_company_company_id_fkey FOREIGN KEY (company_id)
        REFERENCES public.company (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.tag_company
    OWNER to postgres;
-- Table: public.tag_type

-- DROP TABLE IF EXISTS public.tag_type;

CREATE TABLE IF NOT EXISTS public.tag_type
(
    id integer NOT NULL DEFAULT nextval('tag_type_id_seq'::regclass),
    tag character varying(30) COLLATE pg_catalog."default",
    type character varying(30) COLLATE pg_catalog."default",
    CONSTRAINT tag_type_tag_fkey FOREIGN KEY (tag)
        REFERENCES public.tag_company (tag) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.tag_type
    OWNER to postgres;
```
