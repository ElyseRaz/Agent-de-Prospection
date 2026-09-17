package prospects

import (
	"github.com/jackc/pgx/v5/pgtype"

	"leadpilot/internal/db/sqlc"
)

func textOrNull(value *string) pgtype.Text {
	if value == nil {
		return pgtype.Text{}
	}
	return pgtype.Text{String: *value, Valid: true}
}

func textPtr(value pgtype.Text) *string {
	if !value.Valid {
		return nil
	}
	return &value.String
}

func statusOrNull(value *string) sqlc.NullCompanyStatus {
	if value == nil {
		return sqlc.NullCompanyStatus{}
	}
	return sqlc.NullCompanyStatus{CompanyStatus: sqlc.CompanyStatus(*value), Valid: true}
}
