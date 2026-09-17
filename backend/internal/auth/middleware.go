package auth

import (
	"net/http"
	"strings"

	"github.com/google/uuid"
	"github.com/labstack/echo/v4"
)

type contextKey string

const userIDContextKey contextKey = "user_id"

// RequireAuth verifie le header `Authorization: Bearer <access token>` et
// place l'id utilisateur dans le contexte de la requete Echo, disponible
// ensuite via UserIDFromContext dans n'importe quel handler en aval.
func RequireAuth(secretKey string) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			header := c.Request().Header.Get("Authorization")
			if !strings.HasPrefix(header, "Bearer ") {
				return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
			}
			rawToken := strings.TrimPrefix(header, "Bearer ")

			userID, err := ParseToken(rawToken, TokenTypeAccess, secretKey)
			if err != nil {
				return echo.NewHTTPError(http.StatusUnauthorized, "Token invalide ou expire")
			}

			c.Set(string(userIDContextKey), userID)
			return next(c)
		}
	}
}

func UserIDFromContext(c echo.Context) (uuid.UUID, bool) {
	value := c.Get(string(userIDContextKey))
	userID, ok := value.(uuid.UUID)
	return userID, ok
}
