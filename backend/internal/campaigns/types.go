package campaigns

import (
	"time"

	"leadpilot/internal/auth"
	"leadpilot/internal/db/sqlc"
)

type templateResponse struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Subject   string `json:"subject"`
	Body      string `json:"body"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

func toTemplateResponse(t sqlc.EmailTemplate) templateResponse {
	return templateResponse{
		ID:        auth.FromPgUUID(t.ID).String(),
		Name:      t.Name,
		Subject:   t.Subject,
		Body:      t.Body,
		CreatedAt: t.CreatedAt.Time.Format(time.RFC3339),
		UpdatedAt: t.UpdatedAt.Time.Format(time.RFC3339),
	}
}

type createTemplateRequest struct {
	Name    string `json:"name"`
	Subject string `json:"subject"`
	Body    string `json:"body"`
}

type updateTemplateRequest struct {
	Name    *string `json:"name"`
	Subject *string `json:"subject"`
	Body    *string `json:"body"`
}

type campaignResponse struct {
	ID        string  `json:"id"`
	Name      string  `json:"name"`
	Subject   string  `json:"subject"`
	Body      string  `json:"body"`
	Status    string  `json:"status"`
	CreatedAt string  `json:"created_at"`
	UpdatedAt string  `json:"updated_at"`
	SentAt    *string `json:"sent_at"`
}

func toCampaignResponse(c sqlc.Campaign) campaignResponse {
	return campaignResponse{
		ID:        auth.FromPgUUID(c.ID).String(),
		Name:      c.Name,
		Subject:   c.Subject,
		Body:      c.Body,
		Status:    string(c.Status),
		CreatedAt: c.CreatedAt.Time.Format(time.RFC3339),
		UpdatedAt: c.UpdatedAt.Time.Format(time.RFC3339),
		SentAt:    timestamptzPtr(c.SentAt),
	}
}

type recipientResponse struct {
	ID           string  `json:"id"`
	ContactEmail string  `json:"contact_email"`
	ContactName  *string `json:"contact_name"`
	CompanyName  string  `json:"company_name"`
	Status       string  `json:"status"`
	ErrorMessage *string `json:"error_message"`
	SentAt       *string `json:"sent_at"`
}

func toRecipientResponse(r sqlc.ListCampaignRecipientsRow) recipientResponse {
	return recipientResponse{
		ID:           auth.FromPgUUID(r.ID).String(),
		ContactEmail: r.ContactEmail,
		ContactName:  textPtr(r.ContactFullName),
		CompanyName:  r.CompanyName,
		Status:       string(r.Status),
		ErrorMessage: textPtr(r.ErrorMessage),
		SentAt:       timestamptzPtr(r.SentAt),
	}
}

type campaignDetailResponse struct {
	campaignResponse
	Recipients []recipientResponse `json:"recipients"`
	Summary    map[string]int64    `json:"summary"`
}

type createCampaignRequest struct {
	Name       string   `json:"name"`
	Subject    string   `json:"subject"`
	Body       string   `json:"body"`
	CompanyIDs []string `json:"company_ids"`
}
