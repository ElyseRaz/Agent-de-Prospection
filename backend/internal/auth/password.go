package auth

import "golang.org/x/crypto/bcrypt"

// HashPassword et VerifyPassword encapsulent bcrypt (cout par defaut 10,
// suffisant pour un hash de mot de passe utilisateur, pas de derivation de
// cle lourde necessaire ici contrairement a argon2).
func HashPassword(raw string) (string, error) {
	hash, err := bcrypt.GenerateFromPassword([]byte(raw), bcrypt.DefaultCost)
	if err != nil {
		return "", err
	}
	return string(hash), nil
}

func VerifyPassword(raw, hash string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(raw)) == nil
}
