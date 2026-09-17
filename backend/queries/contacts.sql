-- name: CreateContact :one
INSERT INTO contacts (company_id, email, full_name, source_note)
VALUES ($1, $2, $3, $4)
RETURNING *;

-- name: ListContactsByCompany :many
SELECT * FROM contacts WHERE company_id = $1 ORDER BY created_at ASC;

-- name: GetContactByID :one
SELECT * FROM contacts WHERE id = $1;

-- name: DeleteContact :exec
DELETE FROM contacts WHERE id = $1;
