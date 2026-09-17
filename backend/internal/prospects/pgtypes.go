package prospects

import (
	"time"

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

func float4Ptr(value pgtype.Float4) *float32 {
	if !value.Valid {
		return nil
	}
	return &value.Float32
}

func int4Ptr(value pgtype.Int4) *int32 {
	if !value.Valid {
		return nil
	}
	return &value.Int32
}

func timestamptzPtr(value pgtype.Timestamptz) *string {
	if !value.Valid {
		return nil
	}
	formatted := value.Time.Format(time.RFC3339)
	return &formatted
}
