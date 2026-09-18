-- name: CreateCompany :one
INSERT INTO companies (user_id, name, domain, website_url, address, phone, email, notes)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING *;

-- name: GetCompanyByID :one
SELECT * FROM companies WHERE id = $1;

-- name: ListCompaniesByUser :many
SELECT * FROM companies
WHERE user_id = $1
  AND (sqlc.narg(status)::company_status IS NULL OR status = sqlc.narg(status))
  AND (
    sqlc.narg(search)::text IS NULL
    OR name ILIKE '%' || sqlc.narg(search)::text || '%'
    OR domain ILIKE '%' || sqlc.narg(search)::text || '%'
  )
ORDER BY created_at DESC;

-- name: UpdateCompany :one
UPDATE companies
SET
    name = coalesce(sqlc.narg(name), name),
    domain = coalesce(sqlc.narg(domain), domain),
    website_url = coalesce(sqlc.narg(website_url), website_url),
    address = coalesce(sqlc.narg(address), address),
    phone = coalesce(sqlc.narg(phone), phone),
    email = coalesce(sqlc.narg(email), email),
    status = coalesce(sqlc.narg(status), status),
    notes = coalesce(sqlc.narg(notes), notes),
    updated_at = now()
WHERE id = sqlc.arg(id)
RETURNING *;

-- name: DeleteCompany :exec
DELETE FROM companies WHERE id = $1;

-- name: CountCompaniesByUser :one
SELECT count(*) FROM companies WHERE user_id = $1;

-- name: UpdateEnrichment :one
UPDATE companies
SET
    trustpilot_rating = sqlc.narg(trustpilot_rating),
    trustpilot_review_count = sqlc.narg(trustpilot_review_count),
    trustpilot_fetched_at = sqlc.narg(trustpilot_fetched_at),
    ai_needs = sqlc.arg(ai_needs),
    ai_summary = sqlc.narg(ai_summary),
    ai_analyzed_at = sqlc.narg(ai_analyzed_at),
    updated_at = now()
WHERE id = sqlc.arg(id)
RETURNING *;
