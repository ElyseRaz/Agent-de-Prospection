package prospects

import (
	"encoding/csv"
	"io"
	"net/http"
	"strings"

	"github.com/labstack/echo/v4"

	"leadpilot/internal/auth"
	"leadpilot/internal/db/sqlc"
)

const maxImportFileSize = 5 << 20 // 5 Mo

type importRowResult struct {
	Row     int    `json:"row"`
	Status  string `json:"status"` // imported | error
	Message string `json:"message,omitempty"`
}

type importResponse struct {
	Imported int               `json:"imported"`
	Skipped  int               `json:"skipped"`
	Rows     []importRowResult `json:"rows"`
}

// ImportCompanies lit un CSV (colonnes attendues : name,domain,email,
// source_note - email/source_note optionnels, mais source_note devient
// obligatoire des qu'un email est fourni sur la ligne) et cree un prospect
// (+ contact eventuel) par ligne valide. Une ligne en erreur n'interrompt
// jamais l'import des suivantes - le rapport liste chaque ligne traitee.
func (h *Handlers) ImportCompanies(c echo.Context) error {
	userID, ok := auth.UserIDFromContext(c)
	if !ok {
		return echo.NewHTTPError(http.StatusUnauthorized, "Authentification requise")
	}

	fileHeader, err := c.FormFile("file")
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Fichier 'file' manquant")
	}
	if fileHeader.Size > maxImportFileSize {
		return echo.NewHTTPError(http.StatusBadRequest, "Fichier trop volumineux (5 Mo max)")
	}

	file, err := fileHeader.Open()
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Impossible de lire le fichier")
	}
	defer file.Close()

	reader := csv.NewReader(io.LimitReader(file, maxImportFileSize))
	reader.TrimLeadingSpace = true
	reader.FieldsPerRecord = -1

	header, err := reader.Read()
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "CSV vide ou illisible")
	}
	columnIndex := indexColumns(header)

	nameIdx, ok := columnIndex["name"]
	if !ok {
		return echo.NewHTTPError(http.StatusBadRequest, "Colonne 'name' obligatoire dans le CSV")
	}
	domainIdx, hasDomain := columnIndex["domain"]
	emailIdx, hasEmail := columnIndex["email"]
	sourceNoteIdx, hasSourceNote := columnIndex["source_note"]

	ctx := c.Request().Context()
	result := importResponse{Rows: []importRowResult{}}
	rowNumber := 1

	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		rowNumber++
		if err != nil {
			result.Skipped++
			result.Rows = append(result.Rows, importRowResult{Row: rowNumber, Status: "error", Message: "ligne CSV illisible"})
			continue
		}

		name := cellAt(record, nameIdx)
		if strings.TrimSpace(name) == "" {
			result.Skipped++
			result.Rows = append(result.Rows, importRowResult{Row: rowNumber, Status: "error", Message: "nom manquant"})
			continue
		}

		email := ""
		if hasEmail {
			email = cellAt(record, emailIdx)
		}
		sourceNote := ""
		if hasSourceNote {
			sourceNote = cellAt(record, sourceNoteIdx)
		}
		if email != "" {
			if !isValidEmail(email) {
				result.Skipped++
				result.Rows = append(result.Rows, importRowResult{Row: rowNumber, Status: "error", Message: "email invalide"})
				continue
			}
			if strings.TrimSpace(sourceNote) == "" {
				result.Skipped++
				result.Rows = append(result.Rows, importRowResult{
					Row: rowNumber, Status: "error",
					Message: "source_note obligatoire quand un email est fourni",
				})
				continue
			}
		}

		var domainPtr *string
		if hasDomain {
			if domain := cellAt(record, domainIdx); domain != "" {
				domainPtr = &domain
			}
		}

		company, err := h.Queries.CreateCompany(ctx, sqlc.CreateCompanyParams{
			UserID:     auth.ToPgUUID(userID),
			Name:       name,
			Domain:     textOrNull(domainPtr),
			WebsiteUrl: textOrNull(nil),
			Notes:      textOrNull(nil),
		})
		if err != nil {
			result.Skipped++
			result.Rows = append(result.Rows, importRowResult{Row: rowNumber, Status: "error", Message: "echec creation du prospect"})
			continue
		}

		if email != "" {
			if _, err := h.Queries.CreateContact(ctx, sqlc.CreateContactParams{
				CompanyID:  company.ID,
				Email:      email,
				SourceNote: sourceNote,
			}); err != nil {
				result.Imported++
				result.Rows = append(result.Rows, importRowResult{
					Row: rowNumber, Status: "imported",
					Message: "prospect cree, echec de l'ajout du contact (doublon ?)",
				})
				continue
			}
		}

		result.Imported++
		result.Rows = append(result.Rows, importRowResult{Row: rowNumber, Status: "imported"})
	}

	return c.JSON(http.StatusOK, result)
}

func indexColumns(header []string) map[string]int {
	index := make(map[string]int, len(header))
	for i, col := range header {
		index[strings.ToLower(strings.TrimSpace(col))] = i
	}
	return index
}

func cellAt(record []string, idx int) string {
	if idx < 0 || idx >= len(record) {
		return ""
	}
	return strings.TrimSpace(record[idx])
}
