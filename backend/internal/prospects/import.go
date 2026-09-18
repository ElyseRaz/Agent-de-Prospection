package prospects

import (
	"encoding/csv"
	"errors"
	"io"
	"net/http"
	"path/filepath"
	"strings"

	"github.com/labstack/echo/v4"
	"github.com/xuri/excelize/v2"

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

// ImportCompanies lit un fichier CSV ou Excel (.xlsx). Seule la colonne
// 'name' est obligatoire ; 'domain', 'website', 'address', 'phone' et
// 'company_email' renseignent la fiche entreprise. 'email' cree en plus un
// contact trace sur la fiche - 'source_note' devient alors obligatoire.
// Cree un prospect (+ contact eventuel) par ligne valide. Une ligne en
// erreur n'interrompt jamais l'import des suivantes - le rapport liste
// chaque ligne traitee.
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

	records, err := readImportRows(file, fileHeader.Filename)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, err.Error())
	}

	columnIndex := indexColumns(records[0])
	nameIdx, ok := columnIndex["name"]
	if !ok {
		return echo.NewHTTPError(http.StatusBadRequest, "Colonne 'name' obligatoire")
	}
	domainIdx, hasDomain := columnIndex["domain"]
	emailIdx, hasEmail := columnIndex["email"]
	sourceNoteIdx, hasSourceNote := columnIndex["source_note"]
	addressIdx, hasAddress := columnIndex["address"]
	phoneIdx, hasPhone := columnIndex["phone"]
	companyEmailIdx, hasCompanyEmail := columnIndex["company_email"]
	websiteIdx, hasWebsite := columnIndex["website"]

	ctx := c.Request().Context()
	result := importResponse{Rows: []importRowResult{}}

	for i, record := range records[1:] {
		rowNumber := i + 2 // la ligne 1 est l'en-tete

		if record == nil {
			result.Skipped++
			result.Rows = append(result.Rows, importRowResult{Row: rowNumber, Status: "error", Message: "ligne illisible"})
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
		var websitePtr *string
		if hasWebsite {
			if website := cellAt(record, websiteIdx); website != "" {
				websitePtr = &website
			}
		}
		var addressPtr *string
		if hasAddress {
			if address := cellAt(record, addressIdx); address != "" {
				addressPtr = &address
			}
		}
		var phonePtr *string
		if hasPhone {
			if phone := cellAt(record, phoneIdx); phone != "" {
				phonePtr = &phone
			}
		}
		var companyEmailPtr *string
		if hasCompanyEmail {
			if companyEmail := cellAt(record, companyEmailIdx); companyEmail != "" {
				if !isValidEmail(companyEmail) {
					result.Skipped++
					result.Rows = append(result.Rows, importRowResult{Row: rowNumber, Status: "error", Message: "company_email invalide"})
					continue
				}
				companyEmailPtr = &companyEmail
			}
		}

		company, err := h.Queries.CreateCompany(ctx, sqlc.CreateCompanyParams{
			UserID:     auth.ToPgUUID(userID),
			Name:       name,
			Domain:     textOrNull(domainPtr),
			WebsiteUrl: textOrNull(websitePtr),
			Address:    textOrNull(addressPtr),
			Phone:      textOrNull(phonePtr),
			Email:      textOrNull(companyEmailPtr),
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

// readImportRows lit un fichier CSV ou Excel (.xlsx/.xlsm) et retourne
// toutes les lignes (en-tete inclus) sous forme de cellules texte, quelle
// que soit la source.
func readImportRows(file io.Reader, filename string) ([][]string, error) {
	ext := strings.ToLower(filepath.Ext(filename))

	var records [][]string
	var err error
	if ext == ".xlsx" || ext == ".xlsm" {
		records, err = readExcelRows(file)
	} else {
		records, err = readCSVRows(file)
	}
	if err != nil {
		return nil, err
	}
	if len(records) == 0 {
		return nil, errors.New("fichier vide ou illisible")
	}
	return records, nil
}

func readCSVRows(file io.Reader) ([][]string, error) {
	reader := csv.NewReader(io.LimitReader(file, maxImportFileSize))
	reader.TrimLeadingSpace = true
	reader.FieldsPerRecord = -1

	var records [][]string
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			// Une ligne CSV mal formee ne doit pas interrompre l'import :
			// on la garde comme placeholder, elle sera signalee en erreur.
			records = append(records, nil)
			continue
		}
		records = append(records, record)
	}
	return records, nil
}

func readExcelRows(file io.Reader) ([][]string, error) {
	f, err := excelize.OpenReader(file)
	if err != nil {
		return nil, errors.New("fichier Excel illisible")
	}
	defer f.Close()

	sheets := f.GetSheetList()
	if len(sheets) == 0 {
		return nil, errors.New("fichier Excel sans feuille")
	}
	rows, err := f.GetRows(sheets[0])
	if err != nil {
		return nil, errors.New("impossible de lire la feuille Excel")
	}
	return rows, nil
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
