-- name: CreateUnsubscribe :exec
INSERT INTO unsubscribes (email) VALUES ($1) ON CONFLICT (email) DO NOTHING;

-- name: IsUnsubscribed :one
SELECT EXISTS(SELECT 1 FROM unsubscribes WHERE email = $1);
