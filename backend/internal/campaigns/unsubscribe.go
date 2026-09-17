package campaigns

import (
	"errors"
	"net/http"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/labstack/echo/v4"

	"leadpilot/internal/auth"
)

const unsubscribeConfirmationPage = `<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>Desinscription</title></head>
<body style="font-family: sans-serif; max-width: 480px; margin: 4rem auto; text-align: center;">
<h1>Vous avez ete desinscrit</h1>
<p>Vous ne recevrez plus d'emails de notre part.</p>
</body></html>`

// Unsubscribe est un endpoint public (pas d'authentification) : le token
// est l'id du campaign_recipient qui a recu l'email contenant ce lien. On
// desinscrit l'email de maniere globale (table unsubscribes, verifiee par
// tout envoi futur, toutes campagnes confondues), pas seulement pour cette
// campagne precise.
func (h *Handlers) Unsubscribe(c echo.Context) error {
	token := c.QueryParam("token")
	recipientID, err := uuid.Parse(token)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Lien de desinscription invalide")
	}

	ctx := c.Request().Context()
	recipient, err := h.Queries.GetCampaignRecipientByID(ctx, auth.ToPgUUID(recipientID))
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return echo.NewHTTPError(http.StatusNotFound, "Lien de desinscription invalide")
		}
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	contact, err := h.Queries.GetContactByID(ctx, recipient.ContactID)
	if err == nil {
		_ = h.Queries.CreateUnsubscribe(ctx, contact.Email)
	}
	_ = h.Queries.MarkRecipientUnsubscribed(ctx, recipient.ID)

	return c.HTML(http.StatusOK, unsubscribeConfirmationPage)
}
