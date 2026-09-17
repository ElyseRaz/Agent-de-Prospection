-- name: CreateTemplate :one
INSERT INTO email_templates (user_id, name, subject, body)
VALUES ($1, $2, $3, $4)
RETURNING *;

-- name: ListTemplatesByUser :many
SELECT * FROM email_templates WHERE user_id = $1 ORDER BY created_at DESC;

-- name: GetTemplateByID :one
SELECT * FROM email_templates WHERE id = $1;

-- name: UpdateTemplate :one
UPDATE email_templates
SET
    name = coalesce(sqlc.narg(name), name),
    subject = coalesce(sqlc.narg(subject), subject),
    body = coalesce(sqlc.narg(body), body),
    updated_at = now()
WHERE id = sqlc.arg(id)
RETURNING *;

-- name: DeleteTemplate :exec
DELETE FROM email_templates WHERE id = $1;
