package reputation

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestFetchByDomain_ParsesScoreFromFind(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("apikey") != "test-key" {
			t.Errorf("apikey header manquant ou incorrect")
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"id": "abc123",
			"score": {"trustScore": 4.2},
			"numberOfReviews": {"total": 128}
		}`))
	}))
	defer server.Close()

	provider := NewProvider("test-key", server.Client())
	overrideURLsForTest(t, server.URL)

	result, err := provider.FetchByDomain(context.Background(), "acme.com")
	if err != nil {
		t.Fatalf("FetchByDomain a echoue: %v", err)
	}
	if result == nil {
		t.Fatal("resultat attendu, obtenu nil")
	}
	if result.Rating != 4.2 {
		t.Errorf("rating attendu 4.2, obtenu %v", result.Rating)
	}
	if result.ReviewCount != 128 {
		t.Errorf("review count attendu 128, obtenu %v", result.ReviewCount)
	}
}

func TestFetchByDomain_ReturnsNilOnNotFound(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	provider := NewProvider("test-key", server.Client())
	overrideURLsForTest(t, server.URL)

	result, err := provider.FetchByDomain(context.Background(), "inconnu.com")
	if err != nil {
		t.Fatalf("erreur inattendue: %v", err)
	}
	if result != nil {
		t.Fatalf("resultat attendu nil (non trouve), obtenu %+v", result)
	}
}

func TestFetchByDomain_ReturnsErrorOnServerFailure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	provider := NewProvider("test-key", server.Client())
	overrideURLsForTest(t, server.URL)

	_, err := provider.FetchByDomain(context.Background(), "acme.com")
	if err == nil {
		t.Fatal("une erreur etait attendue pour une panne serveur (500), jamais confondue avec 'non trouve'")
	}
}

// overrideURLsForTest redirige temporairement les constantes findURL/
// detailURLFormat vers un serveur httptest, et les restaure a la fin du test.
func overrideURLsForTest(t *testing.T, baseURL string) {
	t.Helper()
	originalFind := findURL
	originalDetail := detailURLFormat
	findURL = baseURL + "/find"
	detailURLFormat = baseURL + "/detail/%s"
	t.Cleanup(func() {
		findURL = originalFind
		detailURLFormat = originalDetail
	})
}
