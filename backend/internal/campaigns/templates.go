package campaigns

import (
	"errors"
	"net/http"
	"strings"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/labstack/echo/v4"

	"leadpilot/internal/auth"
	"leadpilot/internal/db/sqlc"
)

func (h *Handlers) loadOwnedTemplate(c echo.Context, templateID, userID uuid.UUID) (sqlc.EmailTemplate, error) {
	tmpl, err := h.Queries.GetTemplateByID(c.Request().Context(), auth.ToPgUUID(templateID))
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return sqlc.EmailTemplate{}, echo.NewHTTPError(http.StatusNotFound, "Template introuvable")
		}
		return sqlc.EmailTemplate{}, echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	if auth.FromPgUUID(tmpl.UserID) != userID {
		return sqlc.EmailTemplate{}, echo.NewHTTPError(http.StatusForbidden, "Ce template ne vous appartient pas")
	}
	return tmpl, nil
}

func (h *Handlers) CreateTemplate(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	var req createTemplateRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}
	if strings.TrimSpace(req.Name) == "" || strings.TrimSpace(req.Subject) == "" || strings.TrimSpace(req.Body) == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "Nom, sujet et corps sont obligatoires")
	}

	tmpl, err := h.Queries.CreateTemplate(c.Request().Context(), sqlc.CreateTemplateParams{
		UserID:  auth.ToPgUUID(userID),
		Name:    req.Name,
		Subject: req.Subject,
		Body:    req.Body,
	})
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	return c.JSON(http.StatusCreated, toTemplateResponse(tmpl))
}

func (h *Handlers) ListTemplates(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	templates, err := h.Queries.ListTemplatesByUser(c.Request().Context(), auth.ToPgUUID(userID))
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	responses := make([]templateResponse, 0, len(templates))
	for _, tmpl := range templates {
		responses = append(responses, toTemplateResponse(tmpl))
	}
	return c.JSON(http.StatusOK, responses)
}

func (h *Handlers) UpdateTemplate(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}
	templateID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}
	if _, err := h.loadOwnedTemplate(c, templateID, userID); err != nil {
		return err
	}

	var req updateTemplateRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}

	updated, err := h.Queries.UpdateTemplate(c.Request().Context(), sqlc.UpdateTemplateParams{
		ID:      auth.ToPgUUID(templateID),
		Name:    textOrNull(req.Name),
		Subject: textOrNull(req.Subject),
		Body:    textOrNull(req.Body),
	})
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	return c.JSON(http.StatusOK, toTemplateResponse(updated))
}

func (h *Handlers) DeleteTemplate(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}
	templateID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}
	if _, err := h.loadOwnedTemplate(c, templateID, userID); err != nil {
		return err
	}

	if err := h.Queries.DeleteTemplate(c.Request().Context(), auth.ToPgUUID(templateID)); err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	return c.NoContent(http.StatusNoContent)
}
