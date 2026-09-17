package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
)

const (
	maxHomepageBytes = 300 << 10 // 300 Ko - une requete ciblee sur une seule page, pas un crawl
	maxPromptChars   = 6000
)

var (
	scriptOrStyleTag = regexp.MustCompile(`(?is)<(script|style)[^>]*>.*?</(script|style)>`)
	htmlTag          = regexp.MustCompile(`(?s)<[^>]+>`)
	whitespace       = regexp.MustCompile(`\s+`)
)

const systemPrompt = `Tu es un expert en audit digital B2B. On te donne le texte extrait de la
page d'accueil publique d'une entreprise. Detecte des besoins potentiels en
services numeriques parmi cette liste fermee : "refonte de site web",
"creation de site web", "assistant virtuel", "base de donnees / CRM",
"application mobile", "referencement SEO", "automatisation". Ne suggere que
des besoins que le contenu justifie reellement (ex: design visiblement
date, absence de mention mobile/responsive, pas de prise de RDV en ligne,
absence de outils visibles). Reponds uniquement avec un objet JSON de la
forme exacte {"needs": ["..."], "summary": "..."} - needs est une liste de
0 a 4 elements pris dans la liste fermee ci-dessus, summary est une phrase
de synthese en francais (1-2 phrases). Aucun texte hors de ce JSON.`

type Analysis struct {
	Needs   []string `json:"needs"`
	Summary string   `json:"summary"`
}

// Analyzer est optionnel : si `apiKey` est vide, il n'est simplement pas
// construit (voir internal/tasks/enrich.go).
type Analyzer struct {
	apiKey     string
	baseURL    string
	model      string
	httpClient *http.Client
}

func NewAnalyzer(apiKey, baseURL, model string, httpClient *http.Client) *Analyzer {
	return &Analyzer{apiKey: apiKey, baseURL: baseURL, model: model, httpClient: httpClient}
}

// AnalyzeWebsite recupere le texte de la page d'accueil publique de
// `websiteURL` (une seule requete GET, jamais un crawl) puis demande a Groq
// de detecter des besoins de services numeriques a partir de ce contenu.
func (a *Analyzer) AnalyzeWebsite(ctx context.Context, websiteURL string) (*Analysis, error) {
	text, err := a.fetchHomepageText(ctx, websiteURL)
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(text) == "" {
		return &Analysis{Needs: []string{}, Summary: "Page vide ou illisible, aucune analyse possible."}, nil
	}
	return a.analyzeText(ctx, text)
}

func (a *Analyzer) fetchHomepageText(ctx context.Context, websiteURL string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, websiteURL, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", "LeadPilotBot/1.0 (+enrichissement prospect)")

	resp, err := a.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("site inaccessible: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("site a repondu %d", resp.StatusCode)
	}

	body, err := io.ReadAll(io.LimitReader(resp.Body, maxHomepageBytes))
	if err != nil {
		return "", fmt.Errorf("lecture du site echouee: %w", err)
	}

	text := scriptOrStyleTag.ReplaceAllString(string(body), " ")
	text = htmlTag.ReplaceAllString(text, " ")
	text = whitespace.ReplaceAllString(text, " ")
	text = strings.TrimSpace(text)
	if len(text) > maxPromptChars {
		text = text[:maxPromptChars]
	}
	return text, nil
}

type chatCompletionRequest struct {
	Model          string            `json:"model"`
	Messages       []chatMessage     `json:"messages"`
	ResponseFormat map[string]string `json:"response_format"`
	Temperature    float32           `json:"temperature"`
}

type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type chatCompletionResponse struct {
	Choices []struct {
		Message chatMessage `json:"message"`
	} `json:"choices"`
}

func (a *Analyzer) analyzeText(ctx context.Context, text string) (*Analysis, error) {
	payload := chatCompletionRequest{
		Model: a.model,
		Messages: []chatMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: text},
		},
		ResponseFormat: map[string]string{"type": "json_object"},
		Temperature:    0.3,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequestWithContext(
		ctx, http.MethodPost, a.baseURL+"/chat/completions", bytes.NewReader(body),
	)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+a.apiKey)

	resp, err := a.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("erreur reseau Groq: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("erreur API Groq (%d): %s", resp.StatusCode, string(respBody))
	}

	var completion chatCompletionResponse
	if err := json.Unmarshal(respBody, &completion); err != nil {
		return nil, fmt.Errorf("reponse Groq illisible: %w", err)
	}
	if len(completion.Choices) == 0 {
		return nil, fmt.Errorf("reponse Groq sans choix")
	}

	var analysis Analysis
	if err := json.Unmarshal([]byte(completion.Choices[0].Message.Content), &analysis); err != nil {
		return nil, fmt.Errorf("sortie Groq non conforme au schema attendu: %w", err)
	}
	if analysis.Needs == nil {
		analysis.Needs = []string{}
	}
	return &analysis, nil
}
