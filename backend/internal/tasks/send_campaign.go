package tasks

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/google/uuid"
	"github.com/hibiken/asynq"
	"github.com/jackc/pgx/v5/pgtype"

	"leadpilot/internal/auth"
	"leadpilot/internal/db/sqlc"
	"leadpilot/internal/email"
)

const TypeSendCampaign = "campaigns:send"

type SendCampaignPayload struct {
	CampaignID string `json:"campaign_id"`
}

func NewSendCampaignTask(campaignID uuid.UUID) (*asynq.Task, error) {
	payload, err := json.Marshal(SendCampaignPayload{CampaignID: campaignID.String()})
	if err != nil {
		return nil, err
	}
	return asynq.NewTask(TypeSendCampaign, payload), nil
}

// SendCampaignProcessor envoie une campagne email destinataire par
// destinataire : verifie la desinscription juste avant chaque envoi
// (jamais de contournement possible, meme si desinscrit entre la creation
// de la campagne et son envoi), respecte la limite quotidienne globale par
// utilisateur, et ajoute systematiquement le lien de desinscription -
// jamais laisse au contenu redige par l'utilisateur.
type SendCampaignProcessor struct {
	Queries        *sqlc.Queries
	EmailSender    *email.Sender
	PublicAppURL   string
	DailySendLimit int
}

func (p *SendCampaignProcessor) ProcessTask(ctx context.Context, t *asynq.Task) error {
	var payload SendCampaignPayload
	if err := json.Unmarshal(t.Payload(), &payload); err != nil {
		return fmt.Errorf("payload invalide: %w", err)
	}
	campaignID, err := uuid.Parse(payload.CampaignID)
	if err != nil {
		return fmt.Errorf("campaign_id invalide: %w", err)
	}

	campaign, err := p.Queries.GetCampaignByID(ctx, auth.ToPgUUID(campaignID))
	if err != nil {
		log.Printf("send_campaign: campagne %s introuvable, abandon: %v", campaignID, err)
		return nil
	}

	if p.EmailSender == nil {
		log.Printf("send_campaign: SMTP non configure, campagne %s laissee en brouillon", campaignID)
		return nil
	}

	if _, err := p.Queries.SetCampaignStatus(ctx, sqlc.SetCampaignStatusParams{
		ID: campaign.ID, Status: sqlc.CampaignStatusSending,
	}); err != nil {
		return fmt.Errorf("passage en 'sending' echoue: %w", err)
	}

	recipients, err := p.Queries.ListPendingRecipients(ctx, campaign.ID)
	if err != nil {
		return fmt.Errorf("chargement des destinataires echoue: %w", err)
	}

	sentToday, err := p.Queries.CountSentToday(ctx, campaign.UserID)
	if err != nil {
		return fmt.Errorf("comptage des envois du jour echoue: %w", err)
	}
	remaining := p.DailySendLimit - int(sentToday)

	for _, recipient := range recipients {
		if remaining <= 0 {
			log.Printf("send_campaign: limite quotidienne atteinte, campagne %s reprendra plus tard", campaignID)
			break
		}

		unsubscribed, err := p.Queries.IsUnsubscribed(ctx, recipient.ContactEmail)
		if err == nil && unsubscribed {
			_ = p.Queries.MarkRecipientUnsubscribed(ctx, recipient.ID)
			continue
		}

		var fullName *string
		if recipient.ContactFullName.Valid {
			fullName = &recipient.ContactFullName.String
		}
		vars := TemplateVars{
			CompanyName: recipient.CompanyName,
			ContactName: ContactLabel(fullName, recipient.ContactEmail),
			Needs:       NeedsLabel(recipient.CompanyAiNeeds),
		}

		subject := RenderText(campaign.Subject, vars)
		body := RenderText(campaign.Body, vars)
		unsubscribeURL := fmt.Sprintf(
			"%s/api/v1/unsubscribe?token=%s", p.PublicAppURL, auth.FromPgUUID(recipient.ID).String(),
		)
		body += UnsubscribeFooter(unsubscribeURL)

		if err := p.EmailSender.Send(recipient.ContactEmail, subject, body); err != nil {
			log.Printf("send_campaign: envoi echoue vers %s: %v", recipient.ContactEmail, err)
			_ = p.Queries.MarkRecipientFailed(ctx, sqlc.MarkRecipientFailedParams{
				ID: recipient.ID, ErrorMessage: pgtype.Text{String: err.Error(), Valid: true},
			})
			continue
		}

		_ = p.Queries.MarkRecipientSent(ctx, recipient.ID)
		remaining--
	}

	pendingCount, err := p.Queries.CountPendingRecipients(ctx, campaign.ID)
	if err != nil {
		return fmt.Errorf("comptage des destinataires restants echoue: %w", err)
	}
	if pendingCount == 0 {
		_, err = p.Queries.MarkCampaignSent(ctx, campaign.ID)
	} else {
		// Limite quotidienne atteinte avant la fin : repasse en 'draft'
		// pour que l'utilisateur (ou une future replanification) puisse
		// reprendre l'envoi des destinataires restants un autre jour.
		_, err = p.Queries.SetCampaignStatus(ctx, sqlc.SetCampaignStatusParams{
			ID: campaign.ID, Status: sqlc.CampaignStatusDraft,
		})
	}
	if err != nil {
		return fmt.Errorf("mise a jour du statut final de la campagne echouee: %w", err)
	}

	return nil
}
