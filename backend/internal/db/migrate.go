package db

import (
	"errors"
	"fmt"
	"strings"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/pgx/v5"
	"github.com/golang-migrate/migrate/v4/source/iofs"

	"leadpilot/migrations"
)

// RunMigrations applies every pending migration embedded in the binary.
// Safe to call on every startup - golang-migrate uses a Postgres advisory
// lock internally, and returns ErrNoChange once the schema is already
// current, so multiple instances (api + worker) starting concurrently on the
// same database don't race or double-apply.
func RunMigrations(databaseURL string) error {
	source, err := iofs.New(migrations.FS, ".")
	if err != nil {
		return fmt.Errorf("chargement des migrations embarquees: %w", err)
	}

	m, err := migrate.NewWithSourceInstance("iofs", source, toPgx5URL(databaseURL))
	if err != nil {
		return fmt.Errorf("initialisation de golang-migrate: %w", err)
	}
	defer m.Close()

	if err := m.Up(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
		return fmt.Errorf("application des migrations: %w", err)
	}
	return nil
}

// toPgx5URL rewrites a standard postgres:// URL to the pgx5:// scheme that
// golang-migrate's pgx/v5 database driver registers itself under.
func toPgx5URL(databaseURL string) string {
	for _, prefix := range []string{"postgresql://", "postgres://"} {
		if strings.HasPrefix(databaseURL, prefix) {
			return "pgx5://" + strings.TrimPrefix(databaseURL, prefix)
		}
	}
	return databaseURL
}
