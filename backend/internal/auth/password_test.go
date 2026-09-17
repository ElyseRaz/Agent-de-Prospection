package auth

import "testing"

func TestHashPassword_VerifyPassword_RoundTrip(t *testing.T) {
	hash, err := HashPassword("S3curePassw0rd!")
	if err != nil {
		t.Fatalf("HashPassword a echoue: %v", err)
	}

	if !VerifyPassword("S3curePassw0rd!", hash) {
		t.Fatal("le mot de passe correct aurait du etre verifie avec succes")
	}
}

func TestVerifyPassword_RejectsWrongPassword(t *testing.T) {
	hash, err := HashPassword("S3curePassw0rd!")
	if err != nil {
		t.Fatalf("HashPassword a echoue: %v", err)
	}

	if VerifyPassword("mauvais-mot-de-passe", hash) {
		t.Fatal("un mauvais mot de passe n'aurait pas du etre verifie avec succes")
	}
}

func TestHashPassword_ProducesDifferentHashesForSameInput(t *testing.T) {
	hash1, err := HashPassword("S3curePassw0rd!")
	if err != nil {
		t.Fatalf("HashPassword a echoue: %v", err)
	}
	hash2, err := HashPassword("S3curePassw0rd!")
	if err != nil {
		t.Fatalf("HashPassword a echoue: %v", err)
	}

	if hash1 == hash2 {
		t.Fatal("bcrypt doit produire des hashes differents pour le meme mot de passe (salt aleatoire)")
	}
}
