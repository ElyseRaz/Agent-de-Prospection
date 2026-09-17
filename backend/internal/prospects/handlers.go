package prospects

import (
	"errors"
	"net/http"
	"strings"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/labstack/echo/v4"

	"leadpilot/internal/auth"
	"leadpilot/internal/db/sqlc"
)

const uniqueViolationCode = "23505"

type Handlers struct {
	Queries *sqlc.Queries
}

func NewHandlers(queries *sqlc.Queries) *Handlers {
	return &Handlers{Queries: queries}
}

// loadOwnedCompany charge un prospect et verifie qu'il appartient bien a
// l'utilisateur courant - 404 si absent, 403 si appartient a quelqu'un
// d'autre (jamais l'inverse, pour ne pas laisser deviner qu'un id existe).
func (h *Handlers) loadOwnedCompany(c echo.Context, companyID, userID uuid.UUID) (sqlc.Company, error) {
	company, err := h.Queries.GetCompanyByID(c.Request().Context(), auth.ToPgUUID(companyID))
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return sqlc.Company{}, echo.NewHTTPError(http.StatusNotFound, "Prospect introuvable")
		}
		return sqlc.Company{}, echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	if auth.FromPgUUID(company.UserID) != userID {
		return sqlc.Company{}, echo.NewHTTPError(http.StatusForbidden, "Ce prospect ne vous appartient pas")
	}
	return company, nil
}

func (h *Handlers) CreateCompany(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	var req createCompanyRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}
	if strings.TrimSpace(req.Name) == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "Le nom de l'entreprise est requis")
	}
	if req.Contact != nil {
		if !isValidEmail(req.Contact.Email) {
			return echo.NewHTTPError(http.StatusBadRequest, "Email de contact invalide")
		}
		if strings.TrimSpace(req.Contact.SourceNote) == "" {
			return echo.NewHTTPError(
				http.StatusBadRequest,
				"source_note est obligatoire pour tracer l'origine du contact",
			)
		}
	}

	ctx := c.Request().Context()
	company, err := h.Queries.CreateCompany(ctx, sqlc.CreateCompanyParams{
		UserID:     auth.ToPgUUID(userID),
		Name:       req.Name,
		Domain:     textOrNull(req.Domain),
		WebsiteUrl: textOrNull(req.WebsiteURL),
		Notes:      textOrNull(req.Notes),
	})
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	var contacts []contactResponse
	if req.Contact != nil {
		contact, err := h.Queries.CreateContact(ctx, sqlc.CreateContactParams{
			CompanyID:  company.ID,
			Email:      req.Contact.Email,
			FullName:   textOrNull(req.Contact.FullName),
			SourceNote: req.Contact.SourceNote,
		})
		if err != nil {
			return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
		}
		contacts = []contactResponse{toContactResponse(contact)}
	}

	return c.JSON(http.StatusCreated, companyDetailResponse{
		companyResponse: toCompanyResponse(company),
		Contacts:        contacts,
	})
}

func (h *Handlers) ListCompanies(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	statusParam := c.QueryParam("status")
	if statusParam != "" && !validStatuses[statusParam] {
		return echo.NewHTTPError(http.StatusBadRequest, "Statut invalide")
	}
	var statusFilter *string
	if statusParam != "" {
		statusFilter = &statusParam
	}

	var searchFilter *string
	if search := strings.TrimSpace(c.QueryParam("search")); search != "" {
		searchFilter = &search
	}

	companies, err := h.Queries.ListCompaniesByUser(c.Request().Context(), sqlc.ListCompaniesByUserParams{
		UserID: auth.ToPgUUID(userID),
		Status: statusOrNull(statusFilter),
		Search: textOrNull(searchFilter),
	})
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	responses := make([]companyResponse, 0, len(companies))
	for _, company := range companies {
		responses = append(responses, toCompanyResponse(company))
	}
	return c.JSON(http.StatusOK, responses)
}

func (h *Handlers) GetCompany(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	companyID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}

	company, err := h.loadOwnedCompany(c, companyID, userID)
	if err != nil {
		return err
	}

	contacts, err := h.Queries.ListContactsByCompany(c.Request().Context(), company.ID)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	contactResponses := make([]contactResponse, 0, len(contacts))
	for _, contact := range contacts {
		contactResponses = append(contactResponses, toContactResponse(contact))
	}

	return c.JSON(http.StatusOK, companyDetailResponse{
		companyResponse: toCompanyResponse(company),
		Contacts:        contactResponses,
	})
}

func (h *Handlers) UpdateCompany(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	companyID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}

	if _, err := h.loadOwnedCompany(c, companyID, userID); err != nil {
		return err
	}

	var req updateCompanyRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}
	if req.Name != nil && strings.TrimSpace(*req.Name) == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "Le nom de l'entreprise ne peut pas etre vide")
	}
	if req.Status != nil && !validStatuses[*req.Status] {
		return echo.NewHTTPError(http.StatusBadRequest, "Statut invalide")
	}

	updated, err := h.Queries.UpdateCompany(c.Request().Context(), sqlc.UpdateCompanyParams{
		ID:         auth.ToPgUUID(companyID),
		Name:       textOrNull(req.Name),
		Domain:     textOrNull(req.Domain),
		WebsiteUrl: textOrNull(req.WebsiteURL),
		Status:     statusOrNull(req.Status),
		Notes:      textOrNull(req.Notes),
	})
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	return c.JSON(http.StatusOK, toCompanyResponse(updated))
}

func (h *Handlers) DeleteCompany(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	companyID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}

	if _, err := h.loadOwnedCompany(c, companyID, userID); err != nil {
		return err
	}

	if err := h.Queries.DeleteCompany(c.Request().Context(), auth.ToPgUUID(companyID)); err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	return c.NoContent(http.StatusNoContent)
}

func (h *Handlers) CreateContact(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	companyID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}
	if _, err := h.loadOwnedCompany(c, companyID, userID); err != nil {
		return err
	}

	var req contactInput
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}
	if !isValidEmail(req.Email) {
		return echo.NewHTTPError(http.StatusBadRequest, "Email invalide")
	}
	if strings.TrimSpace(req.SourceNote) == "" {
		return echo.NewHTTPError(
			http.StatusBadRequest,
			"source_note est obligatoire pour tracer l'origine du contact",
		)
	}

	contact, err := h.Queries.CreateContact(c.Request().Context(), sqlc.CreateContactParams{
		CompanyID:  auth.ToPgUUID(companyID),
		Email:      req.Email,
		FullName:   textOrNull(req.FullName),
		SourceNote: req.SourceNote,
	})
	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == uniqueViolationCode {
			return echo.NewHTTPError(http.StatusConflict, "Ce contact existe deja pour ce prospect")
		}
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	return c.JSON(http.StatusCreated, toContactResponse(contact))
}

func (h *Handlers) DeleteContact(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	companyID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant invalide")
	}
	if _, err := h.loadOwnedCompany(c, companyID, userID); err != nil {
		return err
	}

	contactID, err := uuid.Parse(c.Param("contactId"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Identifiant de contact invalide")
	}

	contact, err := h.Queries.GetContactByID(c.Request().Context(), auth.ToPgUUID(contactID))
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return echo.NewHTTPError(http.StatusNotFound, "Contact introuvable")
		}
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	if auth.FromPgUUID(contact.CompanyID) != companyID {
		return echo.NewHTTPError(http.StatusNotFound, "Contact introuvable")
	}

	if err := h.Queries.DeleteContact(c.Request().Context(), auth.ToPgUUID(contactID)); err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	return c.NoContent(http.StatusNoContent)
}
