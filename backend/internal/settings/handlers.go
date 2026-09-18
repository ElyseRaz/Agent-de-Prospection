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
// La valeur associee est un fragment attendu dans SMTP_HOST quand on envoie
// via le serveur natif du fournisseur (ex: smtp.gmail.com pour gmail.com) -
// dans ce cas SPF/DKIM s'alignent normalement et il n'y a pas de risque.
var freeEmailDomains = map[string]string{
	"gmail.com": "gmail", "googlemail.com": "gmail",
	"outlook.com": "outlook", "hotmail.com": "outlook", "hotmail.fr": "outlook", "live.com": "outlook", "live.fr": "outlook", "msn.com": "outlook",
	"yahoo.com": "yahoo", "yahoo.fr": "yahoo",
	"aol.com":    "aol",
	"icloud.com": "me.com", "me.com": "me.com", "mac.com": "me.com",
	"protonmail.com": "protonmail", "proton.me": "protonmail",
	"gmx.com": "gmx", "gmx.fr": "gmx", "mail.com": "mail.com", "yandex.com": "yandex", "zoho.com": "zoho",
	"orange.fr": "orange", "laposte.net": "laposte", "free.fr": "free.fr", "sfr.fr": "sfr", "wanadoo.fr": "orange", "bbox.fr": "bbox",
}

// isRiskyFromAddress signale une adresse d'expedition sur un domaine grand
// public, sauf si SMTP_HOST est visiblement le serveur natif de ce meme
// fournisseur (ex: SMTP_FROM en @gmail.com envoye via smtp.gmail.com) - dans
// ce cas c'est reellement le fournisseur qui envoie, pas une usurpation.
func isRiskyFromAddress(from, smtpHost string) bool {
	at := strings.LastIndex(from, "@")
	if at < 0 || at == len(from)-1 {
		return false
	}
	domain := strings.ToLower(strings.TrimSpace(from[at+1:]))
	nativeHostHint, isFree := freeEmailDomains[domain]
	if !isFree {
		return false
	}
	return !strings.Contains(strings.ToLower(smtpHost), nativeHostHint)
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
			SMTPFromRisky:        cfg.SMTPHost != "" && isRiskyFromAddress(cfg.SMTPFrom, cfg.SMTPHost),
			DailySendLimit:       cfg.DailySendLimit,
		})
	}
}
