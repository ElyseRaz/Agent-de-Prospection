-- Extensions requises par RemoteRadar. Rejouable sans erreur (IF NOT EXISTS).
-- Les migrations Alembic (0001_init) les creent aussi ; ce script securise le cas
-- ou la base est provisionnee hors migration (ex: environnement de demo).
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
