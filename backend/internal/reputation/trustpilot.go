package reputation

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

// API Business Units (publique) de Trustpilot. `/find?name=<domaine>` prend
// un DOMAINE (pas un nom en texte libre - cette API publique n'expose pas
// de recherche floue par nom), et renvoie deja score.trustScore/stars et
// numberOfReviews.total. `/{id}` renvoie la meme forme, utilise en repli si
// `/find` ne les inclut pas (meme comportement que le projet precedent).
// var (pas const) : les tests remplacent temporairement ces URLs par un
// serveur httptest (voir overrideURLsForTest dans trustpilot_test.go).
var (
	findURL         = "https://api.trustpilot.com/v1/business-units/find"
	detailURLFormat = "https://api.trustpilot.com/v1/business-units/%s"
)

type Result struct {
	Rating      float32
	ReviewCount int32
}

type businessUnit struct {
	ID    string `json:"id"`
	Score *struct {
		TrustScore float32 `json:"trustScore"`
	} `json:"score"`
	NumberOfReviews *struct {
		Total int32 `json:"total"`
	} `json:"numberOfReviews"`
}

// Provider est optionnel : si `apiKey` est vide, il n'est simplement pas
// construit (voir internal/tasks/enrich.go) - meme principe que les canaux
// de notification du projet precedent, pas d'erreur au demarrage.
type Provider struct {
	apiKey     string
	httpClient *http.Client
}

func NewProvider(apiKey string, httpClient *http.Client) *Provider {
	return &Provider{apiKey: apiKey, httpClient: httpClient}
}

// FetchByDomain renvoie (nil, nil) si l'entreprise n'est pas trouvee sur
// Trustpilot - distinct d'une erreur reseau/API, qui est renvoyee comme
// telle pour ne jamais etre confondue avec "verifie, absent".
func (p *Provider) FetchByDomain(ctx context.Context, domain string) (*Result, error) {
	unit, err := p.find(ctx, domain)
	if err != nil {
		return nil, err
	}
	if unit == nil {
		return nil, nil
	}

	if unit.Score == nil || unit.NumberOfReviews == nil {
		detail, err := p.detail(ctx, unit.ID)
		if err != nil {
			return nil, err
		}
		if detail == nil {
			return nil, nil
		}
		unit = detail
	}

	result := &Result{}
	if unit.Score != nil {
		result.Rating = unit.Score.TrustScore
	}
	if unit.NumberOfReviews != nil {
		result.ReviewCount = unit.NumberOfReviews.Total
	}
	return result, nil
}

func (p *Provider) find(ctx context.Context, domain string) (*businessUnit, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, findURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("apikey", p.apiKey)
	query := req.URL.Query()
	query.Set("name", domain)
	req.URL.RawQuery = query.Encode()

	return p.doRequest(req)
}

func (p *Provider) detail(ctx context.Context, businessUnitID string) (*businessUnit, error) {
	req, err := http.NewRequestWithContext(
		ctx, http.MethodGet, fmt.Sprintf(detailURLFormat, businessUnitID), nil,
	)
	if err != nil {
		return nil, err
	}
	req.Header.Set("apikey", p.apiKey)

	return p.doRequest(req)
}

func (p *Provider) doRequest(req *http.Request) (*businessUnit, error) {
	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("erreur reseau Trustpilot: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, nil
	}
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("erreur Trustpilot (%d)", resp.StatusCode)
	}

	var unit businessUnit
	if err := json.NewDecoder(resp.Body).Decode(&unit); err != nil {
		return nil, fmt.Errorf("reponse Trustpilot illisible: %w", err)
	}
	if unit.ID == "" {
		return nil, nil
	}
	return &unit, nil
}
