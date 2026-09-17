package db

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
)

// NewPool ouvre un pool de connexions pgx et verifie immediatement la
// connectivite (echoue vite au demarrage plutot qu'au premier appel HTTP).
func NewPool(ctx context.Context, databaseURL string) (*pgxpool.Pool, error) {
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return nil, fmt.Errorf("creation du pool pgx: %w", err)
	}

	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping de la base au demarrage: %w", err)
	}

	return pool, nil
}
