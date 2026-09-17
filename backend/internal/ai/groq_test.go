package ai

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAnalyzeWebsite_StripsHTMLAndReturnsNeeds(t *testing.T) {
	var capturedUserContent string

	homepage := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html")
		_, _ = w.Write([]byte(`<html><head><style>body{color:red}</style></head>
			<body><script>track()</script><h1>Acme Corp</h1><p>Bienvenue chez Acme.</p></body></html>`))
	}))
	defer homepage.Close()

	groq := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test-groq-key" {
			t.Errorf("en-tete Authorization manquant ou incorrect")
		}
		var req chatCompletionRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Fatalf("corps de requete illisible: %v", err)
		}
		capturedUserContent = req.Messages[1].Content

		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"choices": [{"message": {"role": "assistant", "content": "{\"needs\":[\"refonte de site web\"],\"summary\":\"Site date.\"}"}}]
		}`))
	}))
	defer groq.Close()

	analyzer := NewAnalyzer("test-groq-key", groq.URL, "test-model", groq.Client())
	analysis, err := analyzer.AnalyzeWebsite(context.Background(), homepage.URL)
	if err != nil {
		t.Fatalf("AnalyzeWebsite a echoue: %v", err)
	}

	if strings.Contains(capturedUserContent, "<script>") || strings.Contains(capturedUserContent, "<style>") {
		t.Errorf("le contenu envoye au LLM contient encore des balises script/style: %q", capturedUserContent)
	}
	if !strings.Contains(capturedUserContent, "Acme Corp") {
		t.Errorf("le texte extrait devrait contenir 'Acme Corp', obtenu: %q", capturedUserContent)
	}

	if len(analysis.Needs) != 1 || analysis.Needs[0] != "refonte de site web" {
		t.Errorf("needs attendu ['refonte de site web'], obtenu %v", analysis.Needs)
	}
	if analysis.Summary != "Site date." {
		t.Errorf("summary attendu 'Site date.', obtenu %q", analysis.Summary)
	}
}

func TestAnalyzeWebsite_ReturnsErrorOnSiteUnreachable(t *testing.T) {
	analyzer := NewAnalyzer("test-key", "https://groq.invalid", "model", http.DefaultClient)
	_, err := analyzer.AnalyzeWebsite(context.Background(), "http://127.0.0.1:1")
	if err == nil {
		t.Fatal("une erreur etait attendue pour un site injoignable")
	}
}

func TestAnalyzeWebsite_ReturnsErrorOnMalformedGroqOutput(t *testing.T) {
	homepage := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`<html><body>Contenu</body></html>`))
	}))
	defer homepage.Close()

	groq := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"choices": [{"message": {"role": "assistant", "content": "pas du json"}}]}`))
	}))
	defer groq.Close()

	analyzer := NewAnalyzer("test-key", groq.URL, "model", groq.Client())
	_, err := analyzer.AnalyzeWebsite(context.Background(), homepage.URL)
	if err == nil {
		t.Fatal("une erreur etait attendue pour une sortie Groq non conforme au schema JSON attendu")
	}
}
