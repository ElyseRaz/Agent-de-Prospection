package httpserver

import (
	"github.com/hibiken/asynq"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/labstack/echo/v4"
	echomiddleware "github.com/labstack/echo/v4/middleware"

	"leadpilot/internal/auth"
	"leadpilot/internal/campaigns"
	"leadpilot/internal/config"
	"leadpilot/internal/db/sqlc"
	"leadpilot/internal/health"
	"leadpilot/internal/prospects"
	"leadpilot/internal/settings"
)

const apiV1Prefix = "/api/v1"

// New construit l'application Echo complete : middlewares globaux, routes
// de sante, authentification, prospects, parametres et campagnes.
func New(cfg config.Config, pool *pgxpool.Pool, asynqClient *asynq.Client) *echo.Echo {
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
	prospectHandlers := prospects.NewHandlers(queries, asynqClient)
	campaignHandlers := campaigns.NewHandlers(queries, asynqClient)

	e.GET("/health", health.Handler(pool))
	e.GET(apiV1Prefix+"/unsubscribe", campaignHandlers.Unsubscribe)

	authGroup := e.Group(apiV1Prefix + "/auth")
	authGroup.POST("/register", authHandlers.Register)
	authGroup.POST("/login", authHandlers.Login)
	authGroup.POST("/refresh", authHandlers.Refresh)
	authGroup.GET("/me", authHandlers.Me, auth.RequireAuth(cfg.SecretKey))
	authGroup.PATCH("/me", authHandlers.UpdateMe, auth.RequireAuth(cfg.SecretKey))

	prospectGroup := e.Group(apiV1Prefix+"/prospects", auth.RequireAuth(cfg.SecretKey))
	prospectGroup.POST("", prospectHandlers.CreateCompany)
	prospectGroup.GET("", prospectHandlers.ListCompanies)
	prospectGroup.POST("/import", prospectHandlers.ImportCompanies)
	prospectGroup.GET("/:id", prospectHandlers.GetCompany)
	prospectGroup.PATCH("/:id", prospectHandlers.UpdateCompany)
	prospectGroup.DELETE("/:id", prospectHandlers.DeleteCompany)
	prospectGroup.POST("/:id/contacts", prospectHandlers.CreateContact)
	prospectGroup.DELETE("/:id/contacts/:contactId", prospectHandlers.DeleteContact)
	prospectGroup.POST("/:id/enrich", prospectHandlers.EnrichCompany)

	settingsGroup := e.Group(apiV1Prefix+"/settings", auth.RequireAuth(cfg.SecretKey))
	settingsGroup.GET("/status", settings.Status(cfg))

	templateGroup := e.Group(apiV1Prefix+"/templates", auth.RequireAuth(cfg.SecretKey))
	templateGroup.POST("", campaignHandlers.CreateTemplate)
	templateGroup.GET("", campaignHandlers.ListTemplates)
	templateGroup.PATCH("/:id", campaignHandlers.UpdateTemplate)
	templateGroup.DELETE("/:id", campaignHandlers.DeleteTemplate)

	campaignGroup := e.Group(apiV1Prefix+"/campaigns", auth.RequireAuth(cfg.SecretKey))
	campaignGroup.POST("", campaignHandlers.CreateCampaign)
	campaignGroup.GET("", campaignHandlers.ListCampaigns)
	campaignGroup.GET("/:id", campaignHandlers.GetCampaign)
	campaignGroup.DELETE("/:id", campaignHandlers.DeleteCampaign)
	campaignGroup.POST("/:id/send", campaignHandlers.SendCampaign)

	return e
}
