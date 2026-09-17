package auth

import (
	"errors"
	"net/http"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/labstack/echo/v4"

	"leadpilot/internal/db/sqlc"
)

const uniqueViolationCode = "23505"

type Handlers struct {
	Queries            *sqlc.Queries
	SecretKey          string
	AccessTokenExpiry  time.Duration
	RefreshTokenExpiry time.Duration
}

func NewHandlers(queries *sqlc.Queries, secretKey string, accessExpiry, refreshExpiry time.Duration) *Handlers {
	return &Handlers{
		Queries:            queries,
		SecretKey:          secretKey,
		AccessTokenExpiry:  accessExpiry,
		RefreshTokenExpiry: refreshExpiry,
	}
}

type registerRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type userResponse struct {
	ID        string `json:"id"`
	Email     string `json:"email"`
	Role      string `json:"role"`
	IsActive  bool   `json:"is_active"`
	CreatedAt string `json:"created_at"`
}

func toUserResponse(u sqlc.User) userResponse {
	return userResponse{
		ID:        FromPgUUID(u.ID).String(),
		Email:     u.Email,
		Role:      string(u.Role),
		IsActive:  u.IsActive,
		CreatedAt: u.CreatedAt.Time.Format(time.RFC3339),
	}
}

func (h *Handlers) Register(c echo.Context) error {
	var req registerRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}
	if !isValidEmail(req.Email) {
		return echo.NewHTTPError(http.StatusBadRequest, "Email invalide")
	}
	if len(req.Password) < 8 {
		return echo.NewHTTPError(http.StatusBadRequest, "Le mot de passe doit contenir au moins 8 caracteres")
	}

	hash, err := HashPassword(req.Password)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	user, err := h.Queries.CreateUser(c.Request().Context(), sqlc.CreateUserParams{
		Email:        req.Email,
		PasswordHash: hash,
		Role:         sqlc.UserRoleUser,
	})
	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == uniqueViolationCode {
			return echo.NewHTTPError(http.StatusConflict, "Un compte existe deja pour cet email")
		}
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	return c.JSON(http.StatusCreated, toUserResponse(user))
}

type loginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type tokenPairResponse struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	TokenType    string `json:"token_type"`
}

func (h *Handlers) Login(c echo.Context) error {
	var req loginRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}

	user, err := h.Queries.GetUserByEmail(c.Request().Context(), req.Email)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return echo.NewHTTPError(http.StatusUnauthorized, "Email ou mot de passe incorrect")
		}
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	if !VerifyPassword(req.Password, user.PasswordHash) {
		return echo.NewHTTPError(http.StatusUnauthorized, "Email ou mot de passe incorrect")
	}
	if !user.IsActive {
		return echo.NewHTTPError(http.StatusForbidden, "Compte desactive")
	}

	userID := FromPgUUID(user.ID)
	access, err := CreateToken(userID, TokenTypeAccess, h.AccessTokenExpiry, h.SecretKey)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	refresh, err := CreateToken(userID, TokenTypeRefresh, h.RefreshTokenExpiry, h.SecretKey)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	return c.JSON(http.StatusOK, tokenPairResponse{
		AccessToken:  access,
		RefreshToken: refresh,
		TokenType:    "bearer",
	})
}

type refreshRequest struct {
	RefreshToken string `json:"refresh_token"`
}

type accessTokenResponse struct {
	AccessToken string `json:"access_token"`
	TokenType   string `json:"token_type"`
}

func (h *Handlers) Refresh(c echo.Context) error {
	var req refreshRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Corps de requete invalide")
	}

	userID, err := ParseToken(req.RefreshToken, TokenTypeRefresh, h.SecretKey)
	if err != nil {
		return echo.NewHTTPError(http.StatusUnauthorized, "Refresh token invalide ou expire")
	}

	user, err := h.Queries.GetUserByID(c.Request().Context(), ToPgUUID(userID))
	if err != nil || !user.IsActive {
		return echo.NewHTTPError(http.StatusUnauthorized, "Utilisateur introuvable ou inactif")
	}

	access, err := CreateToken(userID, TokenTypeAccess, h.AccessTokenExpiry, h.SecretKey)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	return c.JSON(http.StatusOK, accessTokenResponse{AccessToken: access, TokenType: "bearer"})
}

func (h *Handlers) Me(c echo.Context) error {
	userID, ok := UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	user, err := h.Queries.GetUserByID(c.Request().Context(), ToPgUUID(userID))
	if err != nil {
		return echo.NewHTTPError(http.StatusUnauthorized, "Utilisateur introuvable ou inactif")
	}

	return c.JSON(http.StatusOK, toUserResponse(user))
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
