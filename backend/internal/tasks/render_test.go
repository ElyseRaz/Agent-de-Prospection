package tasks

import (
	"strings"
	"testing"
)

func TestRenderText_SubstitutesAllVariables(t *testing.T) {
	result := RenderText(
		"Bonjour {{contact}}, chez {{entreprise}} nous avons remarque {{besoin_detecte}}.",
		TemplateVars{CompanyName: "Acme", ContactName: "Jane", Needs: "un site date"},
	)
	expected := "Bonjour Jane, chez Acme nous avons remarque un site date."
	if result != expected {
		t.Errorf("attendu %q, obtenu %q", expected, result)
	}
}

func TestRenderText_LeavesUnknownPlaceholdersUntouched(t *testing.T) {
	result := RenderText("Bonjour {{inconnu}}", TemplateVars{})
	if result != "Bonjour {{inconnu}}" {
		t.Errorf("un placeholder hors de la liste fermee ne doit pas etre modifie, obtenu %q", result)
	}
}

func TestNeedsLabel_JoinsMultipleNeeds(t *testing.T) {
	label := NeedsLabel([]byte(`["refonte de site web","assistant virtuel"]`))
	expected := "refonte de site web, assistant virtuel"
	if label != expected {
		t.Errorf("attendu %q, obtenu %q", expected, label)
	}
}

func TestNeedsLabel_FallsBackWhenEmpty(t *testing.T) {
	if label := NeedsLabel([]byte(`[]`)); label != "vos besoins numeriques" {
		t.Errorf("repli attendu pour une liste vide, obtenu %q", label)
	}
	if label := NeedsLabel(nil); label != "vos besoins numeriques" {
		t.Errorf("repli attendu pour des donnees absentes, obtenu %q", label)
	}
}

func TestContactLabel_PrefersFullNameOverEmail(t *testing.T) {
	name := "Jane Doe"
	if label := ContactLabel(&name, "jane@acme.com"); label != "Jane Doe" {
		t.Errorf("attendu 'Jane Doe', obtenu %q", label)
	}
}

func TestContactLabel_FallsBackToEmailLocalPart(t *testing.T) {
	if label := ContactLabel(nil, "jane@acme.com"); label != "jane" {
		t.Errorf("attendu 'jane', obtenu %q", label)
	}
	emptyName := "   "
	if label := ContactLabel(&emptyName, "jane@acme.com"); label != "jane" {
		t.Errorf("un nom vide/blanc doit retomber sur l'email, obtenu %q", label)
	}
}

func TestUnsubscribeFooter_ContainsURL(t *testing.T) {
	footer := UnsubscribeFooter("https://example.com/unsubscribe?token=abc")
	if footer == "" {
		t.Fatal("le footer de desinscription ne doit jamais etre vide")
	}
	if !strings.Contains(footer, "https://example.com/unsubscribe?token=abc") {
		t.Errorf("le footer devrait contenir l'URL de desinscription, obtenu %q", footer)
	}
}
