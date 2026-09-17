-- name: CreateCampaignRecipient :one
INSERT INTO campaign_recipients (campaign_id, contact_id, company_id)
VALUES ($1, $2, $3)
ON CONFLICT (campaign_id, contact_id) DO NOTHING
RETURNING *;

-- name: ListCampaignRecipients :many
SELECT
    cr.id, cr.campaign_id, cr.contact_id, cr.company_id, cr.status,
    cr.error_message, cr.sent_at, cr.created_at,
    ct.email AS contact_email, ct.full_name AS contact_full_name,
    co.name AS company_name, co.ai_needs AS company_ai_needs
FROM campaign_recipients cr
JOIN contacts ct ON ct.id = cr.contact_id
JOIN companies co ON co.id = cr.company_id
WHERE cr.campaign_id = $1
ORDER BY cr.created_at ASC;

-- name: ListPendingRecipients :many
SELECT
    cr.id, cr.campaign_id, cr.contact_id, cr.company_id, cr.status,
    cr.error_message, cr.sent_at, cr.created_at,
    ct.email AS contact_email, ct.full_name AS contact_full_name,
    co.name AS company_name, co.ai_needs AS company_ai_needs
FROM campaign_recipients cr
JOIN contacts ct ON ct.id = cr.contact_id
JOIN companies co ON co.id = cr.company_id
WHERE cr.campaign_id = $1 AND cr.status = 'pending'
ORDER BY cr.created_at ASC;

-- name: GetCampaignRecipientByID :one
SELECT * FROM campaign_recipients WHERE id = $1;

-- name: MarkRecipientSent :exec
UPDATE campaign_recipients SET status = 'sent', sent_at = now() WHERE id = $1;

-- name: MarkRecipientFailed :exec
UPDATE campaign_recipients SET status = 'failed', error_message = $2 WHERE id = $1;

-- name: MarkRecipientUnsubscribed :exec
UPDATE campaign_recipients SET status = 'unsubscribed' WHERE id = $1;

-- name: CountRecipientsByStatus :many
SELECT status, count(*) AS total
FROM campaign_recipients
WHERE campaign_id = $1
GROUP BY status;

-- name: CountPendingRecipients :one
SELECT count(*) FROM campaign_recipients WHERE campaign_id = $1 AND status = 'pending';
