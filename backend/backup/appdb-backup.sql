--
-- PostgreSQL database dump
--

\restrict IBCY8D7wG7dkBoo0Oa5r7yiAHDYIta3pfAGKnNghtJSt4uyrSe8zHLMiw8u7aZK

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg13+1)
-- Dumped by pg_dump version 15.15 (Debian 15.15-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO "user";

--
-- Name: item_audit; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.item_audit (
    id integer NOT NULL,
    item_id integer,
    action character varying(50) NOT NULL,
    payload jsonb,
    created_at timestamp with time zone DEFAULT now(),
    user_id character varying(128),
    ip character varying(45),
    method character varying(16),
    user_agent text,
    request_path character varying(512)
);


ALTER TABLE public.item_audit OWNER TO "user";

--
-- Name: item_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.item_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.item_audit_id_seq OWNER TO "user";

--
-- Name: item_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.item_audit_id_seq OWNED BY public.item_audit.id;


--
-- Name: items; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.items (
    id integer NOT NULL,
    name character varying(100)
);


ALTER TABLE public.items OWNER TO "user";

--
-- Name: items_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.items_id_seq OWNER TO "user";

--
-- Name: items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.items_id_seq OWNED BY public.items.id;


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL,
    applied_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.schema_migrations OWNER TO "user";

--
-- Name: item_audit id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.item_audit ALTER COLUMN id SET DEFAULT nextval('public.item_audit_id_seq'::regclass);


--
-- Name: items id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.items ALTER COLUMN id SET DEFAULT nextval('public.items_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.alembic_version (version_num) FROM stdin;
0002_add_audit_columns
\.


--
-- Data for Name: item_audit; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.item_audit (id, item_id, action, payload, created_at, user_id, ip, method, user_agent, request_path) FROM stdin;
3	11	create	{"ip": "172.19.0.1", "name": "AuditTestUA", "method": "POST", "user_id": "99", "user_agent": "Mozilla/5.0 (Windows NT; Windows NT 10.0; ja-JP) WindowsPowerShell/5.1.26100.7019", "request_path": "/items"}	2025-12-07 01:23:27.930681+00	99	172.19.0.1	POST	Mozilla/5.0 (Windows NT; Windows NT 10.0; ja-JP) WindowsPowerShell/5.1.26100.7019	/items
4	12	create	{"ip": "172.19.0.1", "name": "AuditTestUA", "method": "POST", "user_id": "99", "user_agent": "Mozilla/5.0 (Windows NT; Windows NT 10.0; ja-JP) WindowsPowerShell/5.1.26100.7019", "request_path": "/items"}	2025-12-07 01:33:03.83419+00	99	172.19.0.1	POST	Mozilla/5.0 (Windows NT; Windows NT 10.0; ja-JP) WindowsPowerShell/5.1.26100.7019	/items
1	9	create	{"name": "縺ｰ縺ｪ縺ｪ"}	2025-12-07 01:09:16.620402+00	\N	\N	\N	\N	\N
2	10	create	{"ip": "172.19.0.1", "name": "Kiwi", "user_id": "42"}	2025-12-07 01:18:26.193146+00	42	172.19.0.1	\N	\N	\N
\.


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.items (id, name) FROM stdin;
1	Apple
2	Banana
3	Cherry
4	Grape
5	Citron
6	笘・7	縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺・8	縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺ゅ≠縺・9	縺ｰ縺ｪ縺ｪ
10	Kiwi
11	AuditTestUA
12	AuditTestUA
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.schema_migrations (version, applied_at) FROM stdin;
0001_create_item_audit.sql	2025-12-07 01:01:28.914109+00
\.


--
-- Name: item_audit_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.item_audit_id_seq', 4, true);


--
-- Name: items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.items_id_seq', 12, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: item_audit item_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.item_audit
    ADD CONSTRAINT item_audit_pkey PRIMARY KEY (id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: ix_item_audit_created_at; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_item_audit_created_at ON public.item_audit USING btree (created_at);


--
-- Name: ix_item_audit_ip; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_item_audit_ip ON public.item_audit USING btree (ip);


--
-- Name: ix_item_audit_method; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_item_audit_method ON public.item_audit USING btree (method);


--
-- Name: ix_item_audit_user_id; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_item_audit_user_id ON public.item_audit USING btree (user_id);


--
-- PostgreSQL database dump complete
--

\unrestrict IBCY8D7wG7dkBoo0Oa5r7yiAHDYIta3pfAGKnNghtJSt4uyrSe8zHLMiw8u7aZK

