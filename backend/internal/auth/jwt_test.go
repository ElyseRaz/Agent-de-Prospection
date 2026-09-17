package auth

import (
	"testing"
	"time"

	"github.com/google/uuid"
)

func TestCreateAndParseToken_RoundTrip(t *testing.T) {
	userID := uuid.New()
	secret := "test-secret"

	token, err := CreateToken(userID, TokenTypeAccess, time.Minute, secret)
	if err != nil {
		t.Fatalf("CreateToken a echoue: %v", err)
	}

	parsedID, err := ParseToken(token, TokenTypeAccess, secret)
	if err != nil {
		t.Fatalf("ParseToken a echoue: %v", err)
	}
	if parsedID != userID {
		t.Fatalf("id attendu %s, obtenu %s", userID, parsedID)
	}
}

func TestParseToken_RejectsWrongType(t *testing.T) {
	userID := uuid.New()
	secret := "test-secret"

	refreshToken, err := CreateToken(userID, TokenTypeRefresh, time.Minute, secret)
	if err != nil {
		t.Fatalf("CreateToken a echoue: %v", err)
	}

	if _, err := ParseToken(refreshToken, TokenTypeAccess, secret); err == nil {
		t.Fatal("un refresh token n'aurait pas du etre accepte comme access token")
	}
}

func TestParseToken_RejectsExpired(t *testing.T) {
	userID := uuid.New()
	secret := "test-secret"

	token, err := CreateToken(userID, TokenTypeAccess, -time.Minute, secret)
	if err != nil {
		t.Fatalf("CreateToken a echoue: %v", err)
	}

	if _, err := ParseToken(token, TokenTypeAccess, secret); err == nil {
		t.Fatal("un token expire n'aurait pas du etre accepte")
	}
}

func TestParseToken_RejectsWrongSecret(t *testing.T) {
	userID := uuid.New()

	token, err := CreateToken(userID, TokenTypeAccess, time.Minute, "secret-a")
	if err != nil {
		t.Fatalf("CreateToken a echoue: %v", err)
	}

	if _, err := ParseToken(token, TokenTypeAccess, "secret-b"); err == nil {
		t.Fatal("un token signe avec un autre secret n'aurait pas du etre accepte")
	}
}
