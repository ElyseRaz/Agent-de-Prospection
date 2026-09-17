package auth

import (
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
)

// ToPgUUID/FromPgUUID font le pont entre google/uuid (utilise pour le JWT et
// les reponses JSON) et pgtype.UUID (utilise par le code genere sqlc) - les
// deux partagent le meme layout memoire ([16]byte), la conversion est directe.
func ToPgUUID(id uuid.UUID) pgtype.UUID {
	return pgtype.UUID{Bytes: id, Valid: true}
}

func FromPgUUID(id pgtype.UUID) uuid.UUID {
	return uuid.UUID(id.Bytes)
}
