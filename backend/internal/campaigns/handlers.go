package campaigns

import (
	"errors"
	"net/http"

	"github.com/google/uuid"
	"github.com/hibiken/asynq"
	"github.com/jackc/pgx/v5"
	"github.com/labstack/echo/v4"

	"leadpilot/internal/auth"
	"leadpilot/internal/db/sqlc"
	"leadpilot/internal/tasks"
)

type Handlers struct {
	Queries     *sqlc.Queries
	AsynqClient *asynq.Client
}

func NewHandlers(queries *sqlc.Queries, asynqClient *asynq.Client) *Handlers {
	return &Handlers{Queries: queries, AsynqClient: asynqClient}
}

func (h *Handlers) loadOwnedCampaign(c echo.Context, campaignID, userID uuid.UUID) (sqlc.Campaign, error) {
	campaign, err := h.Queries.GetCampaignByID(c.Request().Context(), auth.ToPgUUID(campaignID))
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return sqlc.Campaign{}, echo.NewHTTPError(http.StatusNotFound, "Campagne introuvable")
		}
		return sqlc.Campaign{}, echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	if auth.FromPgUUID(campaign.UserID) != userID {
		return sqlc.Campaign{}, echo.NewHTTPError(http.StatusForbidden, "Cette campagne ne vous appartient pas")
	}
	return campaign, nil
}

func (h *Handlers) CreateCampaign(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	var req createCampaignRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}
	if req.Name == "" || req.Subject == "" || req.Body == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "Nom, sujet et corps sont obligatoires")
	}
	if len(req.CompanyIDs) == 0 {
		return echo.NewHTTPError(http.StatusBadRequest, "Au moins un prospect destinataire est requis")
	}

	ctx := c.Request().Context()

	campaign, err := h.Queries.CreateCampaign(ctx, sqlc.CreateCampaignParams{
		UserID:  auth.ToPgUUID(userID),
		Name:    req.Name,
		Subject: req.Subject,
		Body:    req.Body,
	})
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	recipientCount := 0
	for _, rawCompanyID := range req.CompanyIDs {
		companyID, err := uuid.Parse(rawCompanyID)
		if err != nil {
			continue
		}
		company, err := h.Queries.GetCompanyByID(ctx, auth.ToPgUUID(companyID))
		if err != nil || auth.FromPgUUID(company.UserID) != userID {
			// Prospect introuvable ou appartenant a un autre utilisateur :
			// ignore silencieusement plutot que d'echouer toute la
			// campagne pour un id invalide parmi d'autres valides.
			continue
		}

		contacts, err := h.Queries.ListContactsByCompany(ctx, company.ID)
		if err != nil {
			continue
		}
		for _, contact := range contacts {
			if _, err := h.Queries.CreateCampaignRecipient(ctx, sqlc.CreateCampaignRecipientParams{
				CampaignID: campaign.ID,
				ContactID:  contact.ID,
				CompanyID:  company.ID,
			}); err == nil {
				recipientCount++
			}
		}
	}

	if recipientCount == 0 {
		_ = h.Queries.DeleteCampaign(ctx, campaign.ID)
		return echo.NewHTTPError(
			http.StatusBadRequest,
			"Aucun contact trouve parmi les prospects selectionnes (ajoute au moins un contact a ces prospects d'abord)",
		)
	}

	return c.JSON(http.StatusCreated, toCampaignResponse(campaign))
}

func (h *Handlers) ListCampaigns(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	campaignList, err := h.Queries.ListCampaignsByUser(c.Request().Context(), auth.ToPgUUID(userID))
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	responses := make([]campaignResponse, 0, len(campaignList))
	for _, campaign := range campaignList {
		responses = append(responses, toCampaignResponse(campaign))
	}
	return c.JSON(http.StatusOK, responses)
}

func (h *Handlers) GetCampaign(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}
	campaignID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}
	campaign, err := h.loadOwnedCampaign(c, campaignID, userID)
	if err != nil {
		return err
	}

	ctx := c.Request().Context()
	rows, err := h.Queries.ListCampaignRecipients(ctx, campaign.ID)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	recipients := make([]recipientResponse, 0, len(rows))
	for _, row := range rows {
		recipients = append(recipients, toRecipientResponse(row))
	}

	counts, err := h.Queries.CountRecipientsByStatus(ctx, campaign.ID)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	summary := map[string]int64{}
	for _, row := range counts {
		summary[string(row.Status)] = row.Total
	}

	return c.JSON(http.StatusOK, campaignDetailResponse{
		campaignResponse: toCampaignResponse(campaign),
		Recipients:       recipients,
		Summary:          summary,
	})
}

func (h *Handlers) DeleteCampaign(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}
	campaignID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}
	if _, err := h.loadOwnedCampaign(c, campaignID, userID); err != nil {
		return err
	}

	if err := h.Queries.DeleteCampaign(c.Request().Context(), auth.ToPgUUID(campaignID)); err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	return c.NoContent(http.StatusNoContent)
}

// SendCampaign met en file l'envoi (jamais synchrone : un envoi SMTP par
// destinataire prend du temps et ne doit jamais bloquer la requete HTTP).
// Refuse un second envoi tant que la campagne est deja en cours.
func (h *Handlers) SendCampaign(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}
	campaignID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}
	campaign, err := h.loadOwnedCampaign(c, campaignID, userID)
	if err != nil {
		return err
	}
	if campaign.Status == sqlc.CampaignStatusSending {
		return echo.NewHTTPError(http.StatusConflict, "Cette campagne est deja en cours d'envoi")
	}

	task, err := tasks.NewSendCampaignTask(campaignID)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	if _, err := h.AsynqClient.Enqueue(task); err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Impossible de programmer l'envoi")
	}

	return c.JSON(http.StatusAccepted, map[string]string{"status": "queued"})
}
