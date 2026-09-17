package tasks

import (
	"encoding/json"
	"strings"
)

// TemplateVars regroupe les variables resolues pour un destinataire donne.
// Volontairement une liste fermee (pas de moteur de template generique) :
// coherent avec le reste du projet (pas de fonctionnalite au-dela du
// besoin reel).
type TemplateVars struct {
	CompanyName string
	ContactName string
	Needs       string
}

func RenderText(text string, vars TemplateVars) string {
	replacer := strings.NewReplacer(
		"{{entreprise}}", vars.CompanyName,
		"{{contact}}", vars.ContactName,
		"{{besoin_detecte}}", vars.Needs,
	)
	return replacer.Replace(text)
}

// NeedsLabel transforme les besoins IA bruts (JSONB) en texte lisible pour
// {{besoin_detecte}}, avec un repli neutre si l'entreprise n'a pas encore
// ete enrichie ou si l'IA n'a detecte aucun besoin specifique.
func NeedsLabel(aiNeedsJSON []byte) string {
	var needs []string
	if len(aiNeedsJSON) > 0 {
		_ = json.Unmarshal(aiNeedsJSON, &needs)
	}
	if len(needs) == 0 {
		return "vos besoins numeriques"
	}
	return strings.Join(needs, ", ")
}

// ContactLabel utilise le nom du contact s'il est renseigne, sinon replie
// sur la partie locale de son email (avant le @) pour rester naturel dans
// une formule de politesse ("Bonjour {{contact}}").
func ContactLabel(fullName *string, email string) string {
	if fullName != nil && strings.TrimSpace(*fullName) != "" {
		return *fullName
	}
	if at := strings.Index(email, "@"); at > 0 {
		return email[:at]
	}
	return email
}

// UnsubscribeFooter est toujours ajoute a la fin de chaque email envoye,
// independamment du contenu redige par l'utilisateur - garantit le lien de
// desinscription obligatoire (prospection B2B), jamais contournable via
// l'editeur de template.
func UnsubscribeFooter(unsubscribeURL string) string {
	return "\n\n---\nPour ne plus recevoir d'emails de notre part : " + unsubscribeURL
}
