package email

import (
	"fmt"
	"net/smtp"
	"strings"
)

// Sender est optionnel : construit uniquement si `host` est renseigne (voir
// internal/tasks/send_campaign.go, qui refuse proprement l'envoi si nil).
type Sender struct {
	host     string
	port     int
	user     string
	password string
	from     string
}

func NewSender(host string, port int, user, password, from string) *Sender {
	return &Sender{host: host, port: port, user: user, password: password, from: from}
}

// Send construit un message RFC822 minimal (texte brut, UTF-8) et l'envoie
// via SMTP avec authentification PLAIN - suffisant pour les fournisseurs
// SMTP standards (Gmail, SendGrid, Mailgun SMTP relay, etc.).
func (s *Sender) Send(to, subject, body string) error {
	addr := fmt.Sprintf("%s:%d", s.host, s.port)
	auth := smtp.PlainAuth("", s.user, s.password, s.host)

	var msg strings.Builder
	msg.WriteString(fmt.Sprintf("From: %s\r\n", s.from))
	msg.WriteString(fmt.Sprintf("To: %s\r\n", to))
	msg.WriteString(fmt.Sprintf("Subject: %s\r\n", subject))
	msg.WriteString("MIME-Version: 1.0\r\n")
	msg.WriteString("Content-Type: text/plain; charset=UTF-8\r\n")
	msg.WriteString("\r\n")
	msg.WriteString(body)

	if err := smtp.SendMail(addr, auth, s.from, []string{to}, []byte(msg.String())); err != nil {
		return fmt.Errorf("envoi SMTP echoue vers %s: %w", to, err)
	}
	return nil
}
