package migrations

import "embed"

// FS embeds every migration file into the compiled binary, so `api`/`worker`
// can apply the schema themselves on startup without needing a separate
// migrate step or external DB access (see internal/db/migrate.go) - useful on
// platforms like Railway where the DB is only reachable from inside its
// private network.
//
//go:embed *.sql
var FS embed.FS
