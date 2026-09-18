package prospects

import (
	"net/http"

	"github.com/labstack/echo/v4"
	"github.com/xuri/excelize/v2"
)

// DownloadImportTemplate genere et renvoie un classeur Excel vierge, avec les
// colonnes attendues par ImportCompanies, deux lignes d'exemple et un onglet
// d'instructions - a completer puis reimporter via /prospects/import.
func (h *Handlers) DownloadImportTemplate(c echo.Context) error {
	f := excelize.NewFile()
	defer f.Close()

	const sheet = "Prospects"
	f.SetSheetName(f.GetSheetName(0), sheet)

	headerStyle, err := f.NewStyle(&excelize.Style{
		Font: &excelize.Font{Bold: true, Color: "FFFFFF"},
		Fill: excelize.Fill{Type: "pattern", Color: []string{"2563EB"}, Pattern: 1},
	})
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}
	exampleStyle, err := f.NewStyle(&excelize.Style{
		Font: &excelize.Font{Color: "667085", Italic: true},
	})
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur interne")
	}

	headers := []string{"name", "domain", "website", "address", "phone", "company_email", "email", "source_note"}
	lastCol := "H"
	for i, h := range headers {
		cell, _ := excelize.CoordinatesToCellName(i+1, 1)
		f.SetCellValue(sheet, cell, h)
	}
	f.SetCellStyle(sheet, "A1", lastCol+"1", headerStyle)

	examples := [][]string{
		{"Acme SAS", "acme.fr", "https://acme.fr", "12 rue de la Paix, 75002 Paris", "+33 1 23 45 67 89", "contact@acme.fr", "", ""},
		{
			"Widget Corp", "widgetcorp.io", "https://widgetcorp.io", "48 Wall Street, New York, NY",
			"+1 212 555 0100", "hello@widgetcorp.io", "contact@widgetcorp.io", "Salon Web Summit 2026, stand 42",
		},
	}
	for row, values := range examples {
		for col, value := range values {
			cell, _ := excelize.CoordinatesToCellName(col+1, row+2)
			f.SetCellValue(sheet, cell, value)
		}
	}
	f.SetCellStyle(sheet, "A2", lastCol+"3", exampleStyle)

	f.SetColWidth(sheet, "A", "A", 22)
	f.SetColWidth(sheet, "B", "B", 18)
	f.SetColWidth(sheet, "C", "C", 24)
	f.SetColWidth(sheet, "D", "D", 32)
	f.SetColWidth(sheet, "E", "E", 18)
	f.SetColWidth(sheet, "F", "F", 24)
	f.SetColWidth(sheet, "G", "G", 24)
	f.SetColWidth(sheet, "H", "H", 40)

	const instructionsSheet = "Instructions"
	f.NewSheet(instructionsSheet)
	instructions := [][]string{
		{"Colonne", "Obligatoire", "Description"},
		{"name", "Oui", "Nom de l'entreprise."},
		{"domain", "Non", "Domaine (ex: acme.fr), utilise pour l'enrichissement Trustpilot."},
		{"website", "Non", "URL du site web (ex: https://acme.fr)."},
		{"address", "Non", "Adresse postale de l'entreprise."},
		{"phone", "Non", "Telephone general de l'entreprise."},
		{"company_email", "Non", "Email general de l'entreprise (accueil, contact@...)."},
		{"email", "Non", "Email d'un contact precis chez cette entreprise (personne a prospecter)."},
		{"source_note", "Oui si email fourni", "D'ou vient ce contact (page contact publique, salon, reseau...). Obligatoire des qu'un email est renseigne - aucune collecte de masse."},
		{"", "", ""},
		{"Remarque", "", "Seul 'name' est obligatoire. Supprime les deux lignes d'exemple avant d'importer, ou laisse-les : les lignes sans email sont importees telles quelles."},
	}
	instructionsHeaderStyle, _ := f.NewStyle(&excelize.Style{Font: &excelize.Font{Bold: true}})
	for row, values := range instructions {
		for col, value := range values {
			cell, _ := excelize.CoordinatesToCellName(col+1, row+1)
			f.SetCellValue(instructionsSheet, cell, value)
		}
	}
	f.SetCellStyle(instructionsSheet, "A1", "C1", instructionsHeaderStyle)
	f.SetColWidth(instructionsSheet, "A", "A", 18)
	f.SetColWidth(instructionsSheet, "B", "B", 18)
	f.SetColWidth(instructionsSheet, "C", "C", 70)

	f.SetActiveSheet(0)

	buf, err := f.WriteToBuffer()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Erreur lors de la generation du modele")
	}

	c.Response().Header().Set(echo.HeaderContentDisposition, `attachment; filename="modele-import-prospects.xlsx"`)
	return c.Blob(http.StatusOK, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", buf.Bytes())
}
