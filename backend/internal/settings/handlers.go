package settings

import (
	"net/http"
	"strings"

	"github.com/labstack/echo/v4"

	"leadpilot/internal/config"
)

type statusResponse struct {
	TrustpilotConfigured bool   `json:"trustpilot_configured"`
	GroqConfigured       bool   `json:"groq_configured"`
	SMTPConfigured       bool   `json:"smtp_configured"`
	SMTPFrom             string `json:"smtp_from"`
	SMTPFromRisky        bool   `json:"smtp_from_risky"`
	DailySendLimit       int    `json:"daily_send_limit"`
}

// freeEmailDomains recense les domaines de messagerie grand public sur
// lesquels on ne controle jamais SPF/DKIM/DMARC. Envoyer "From:" une de ces
// adresses via un relais SMTP tiers (Brevo, SendGrid...) echoue quasi
// systematiquement l'alignement DMARC du fournisseur reel (ex: Gmail) et
// finit en spam ou rejete, silencieusement - voir internal/email/smtp.go.
var freeEmailDomains = map[string]bool{
	"gmail.com": true, "googlemail.com": true,
	"outlook.com": true, "hotmail.com": true, "hotmail.fr": true, "live.com": true, "live.fr": true, "msn.com": true,
	"yahoo.com": true, "yahoo.fr": true,
	"aol.com": true,
	"icloud.com": true, "me.com": true, "mac.com": true,
	"protonmail.com": true, "proton.me": true,
	"gmx.com": true, "gmx.fr": true, "mail.com": true, "yandex.com": true, "zoho.com": true,
	"orange.fr": true, "laposte.net": true, "free.fr": true, "sfr.fr": true, "wanadoo.fr": true, "bbox.fr": true,
}

func isRiskyFromAddress(from string) bool {
	at := strings.LastIndex(from, "@")
	if at < 0 || at == len(from)-1 {
		return false
	}
	domain := strings.ToLower(strings.TrimSpace(from[at+1:]))
	return freeEmailDomains[domain]
}

// Status expose uniquement des booleens (et la limite d'envoi, publique par
// nature) - jamais les cles elles-memes, qui restent exclusivement dans les
// variables d'environnement. SMTPFrom est l'exception : c'est deja
// l'adresse visible sur chaque email envoye, pas un secret.
func Status(cfg config.Config) echo.HandlerFunc {
	return func(c echo.Context) error {
		return c.JSON(http.StatusOK, statusResponse{
			TrustpilotConfigured: cfg.TrustpilotAPIKey != "",
			GroqConfigured:       cfg.GroqAPIKey != "",
			SMTPConfigured:       cfg.SMTPHost != "",
			SMTPFrom:             cfg.SMTPFrom,
			SMTPFromRisky:        cfg.SMTPHost != "" && isRiskyFromAddress(cfg.SMTPFrom),
			DailySendLimit:       cfg.DailySendLimit,
		})
	}
}
