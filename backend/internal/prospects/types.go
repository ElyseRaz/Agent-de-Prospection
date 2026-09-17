package prospects

import (
	"time"

	"leadpilot/internal/auth"
	"leadpilot/internal/db/sqlc"
)

var validStatuses = map[string]bool{
	"new":       true,
	"contacted": true,
	"replied":   true,
	"converted": true,
	"lost":      true,
}

type companyResponse struct {
	ID         string  `json:"id"`
	Name       string  `json:"name"`
	Domain     *string `json:"domain"`
	WebsiteURL *string `json:"website_url"`
	Status     string  `json:"status"`
	Notes      *string `json:"notes"`
	CreatedAt  string  `json:"created_at"`
	UpdatedAt  string  `json:"updated_at"`
}

func toCompanyResponse(c sqlc.Company) companyResponse {
	return companyResponse{
		ID:         auth.FromPgUUID(c.ID).String(),
		Name:       c.Name,
		Domain:     textPtr(c.Domain),
		WebsiteURL: textPtr(c.WebsiteUrl),
		Status:     string(c.Status),
		Notes:      textPtr(c.Notes),
		CreatedAt:  c.CreatedAt.Time.Format(time.RFC3339),
		UpdatedAt:  c.UpdatedAt.Time.Format(time.RFC3339),
	}
}

type contactResponse struct {
	ID         string  `json:"id"`
	Email      string  `json:"email"`
	FullName   *string `json:"full_name"`
	SourceNote string  `json:"source_note"`
	CreatedAt  string  `json:"created_at"`
}

func toContactResponse(c sqlc.Contact) contactResponse {
	return contactResponse{
		ID:         auth.FromPgUUID(c.ID).String(),
		Email:      c.Email,
		FullName:   textPtr(c.FullName),
		SourceNote: c.SourceNote,
		CreatedAt:  c.CreatedAt.Time.Format(time.RFC3339),
	}
}

type companyDetailResponse struct {
	companyResponse
	Contacts []contactResponse `json:"contacts"`
}

type contactInput struct {
	Email      string  `json:"email"`
	FullName   *string `json:"full_name"`
	SourceNote string  `json:"source_note"`
}

type createCompanyRequest struct {
	Name       string        `json:"name"`
	Domain     *string       `json:"domain"`
	WebsiteURL *string       `json:"website_url"`
	Notes      *string       `json:"notes"`
	Contact    *contactInput `json:"contact"`
}

type updateCompanyRequest struct {
	Name       *string `json:"name"`
	Domain     *string `json:"domain"`
	WebsiteURL *string `json:"website_url"`
	Status     *string `json:"status"`
	Notes      *string `json:"notes"`
}

func isValidEmail(email string) bool {
	at := -1
	for i, r := range email {
		if r == '@' {
			at = i
			break
		}
	}
	return at > 0 && at < len(email)-1
}
