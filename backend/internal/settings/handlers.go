package settings

import (
	"net/http"

	"github.com/labstack/echo/v4"

	"leadpilot/internal/config"
)

type statusResponse struct {
	TrustpilotConfigured bool `json:"trustpilot_configured"`
	GroqConfigured       bool `json:"groq_configured"`
	SMTPConfigured       bool `json:"smtp_configured"`
	DailySendLimit       int  `json:"daily_send_limit"`
}

// Status expose uniquement des booleens (et la limite d'envoi, publique par
// nature) - jamais les cles elles-memes, qui restent exclusivement dans les
// variables d'environnement.
func Status(cfg config.Config) echo.HandlerFunc {
	return func(c echo.Context) error {
		return c.JSON(http.StatusOK, statusResponse{
			TrustpilotConfigured: cfg.TrustpilotAPIKey != "",
			GroqConfigured:       cfg.GroqAPIKey != "",
			SMTPConfigured:       cfg.SMTPHost != "",
			DailySendLimit:       cfg.DailySendLimit,
		})
	}
}
