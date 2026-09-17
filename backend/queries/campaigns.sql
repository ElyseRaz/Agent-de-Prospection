-- name: CreateCampaign :one
INSERT INTO campaigns (user_id, name, subject, body)
VALUES ($1, $2, $3, $4)
RETURNING *;

-- name: ListCampaignsByUser :many
SELECT * FROM campaigns WHERE user_id = $1 ORDER BY created_at DESC;

-- name: GetCampaignByID :one
SELECT * FROM campaigns WHERE id = $1;

-- name: SetCampaignStatus :one
UPDATE campaigns SET status = $2, updated_at = now() WHERE id = $1 RETURNING *;

-- name: MarkCampaignSent :one
UPDATE campaigns SET status = 'sent', sent_at = now(), updated_at = now() WHERE id = $1 RETURNING *;

-- name: DeleteCampaign :exec
DELETE FROM campaigns WHERE id = $1;

-- name: CountSentToday :one
SELECT count(*)
FROM campaign_recipients cr
JOIN campaigns c ON c.id = cr.campaign_id
WHERE c.user_id = $1
  AND cr.status = 'sent'
  AND cr.sent_at >= date_trunc('day', now());
