package httpserver

import (
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/labstack/echo/v4"
	echomiddleware "github.com/labstack/echo/v4/middleware"

	"leadpilot/internal/auth"
	"leadpilot/internal/config"
	"leadpilot/internal/db/sqlc"
	"leadpilot/internal/health"
)

const apiV1Prefix = "/api/v1"

// New construit l'application Echo complete : middlewares globaux, routes
// de sante et d'authentification. Les routes metier (prospects, campagnes)
// s'ajouteront ici au fil des phases suivantes, sans toucher au reste.
func New(cfg config.Config, pool *pgxpool.Pool) *echo.Echo {
	e := echo.New()
	e.HideBanner = true

	e.Use(echomiddleware.Recover())
	e.Use(echomiddleware.RequestID())
	e.Use(echomiddleware.Logger())
	e.Use(echomiddleware.CORSWithConfig(echomiddleware.CORSConfig{
		AllowOrigins:     cfg.CORSOrigins,
		AllowCredentials: true,
		AllowMethods:     []string{"GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"},
	}))
	e.Use(echomiddleware.SecureWithConfig(echomiddleware.SecureConfig{
		XSSProtection:      "0",
		ContentTypeNosniff: "nosniff",
		XFrameOptions:      "DENY",
		ReferrerPolicy:     "strict-origin-when-cross-origin",
	}))

	queries := sqlc.New(pool)
	authHandlers := auth.NewHandlers(queries, cfg.SecretKey, cfg.AccessTokenExpiry, cfg.RefreshTokenExpiry)

	e.GET("/health", health.Handler(pool))

	authGroup := e.Group(apiV1Prefix + "/auth")
	authGroup.POST("/register", authHandlers.Register)
	authGroup.POST("/login", authHandlers.Login)
	authGroup.POST("/refresh", authHandlers.Refresh)
	authGroup.GET("/me", authHandlers.Me, auth.RequireAuth(cfg.SecretKey))

	return e
}
