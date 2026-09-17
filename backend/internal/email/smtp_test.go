package email

import (
	"strings"
	"testing"
)

func TestSend_ReturnsWrappedErrorWhenServerUnreachable(t *testing.T) {
	sender := NewSender("127.0.0.1", 1, "user", "password", "bot@example.com")

	err := sender.Send("dest@example.com", "Sujet", "Corps")
	if err == nil {
		t.Fatal("une erreur etait attendue pour un serveur SMTP injoignable")
	}
	if !strings.Contains(err.Error(), "dest@example.com") {
		t.Errorf("l'erreur devrait mentionner le destinataire pour faciliter le diagnostic, obtenu: %v", err)
	}
}
