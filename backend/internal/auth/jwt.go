package auth

import (
	"errors"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type TokenType string

const (
	TokenTypeAccess  TokenType = "access"
	TokenTypeRefresh TokenType = "refresh"
)

var ErrInvalidToken = errors.New("token invalide ou expire")

type Claims struct {
	Type TokenType `json:"type"`
	jwt.RegisteredClaims
}

// CreateToken signe un JWT HS256 avec un `sub` = user id et un type
// (access/refresh) verifie a la relecture, pour qu'un refresh token ne
// puisse jamais etre utilise a la place d'un access token ou inversement.
func CreateToken(userID uuid.UUID, tokenType TokenType, expiry time.Duration, secretKey string) (string, error) {
	now := time.Now()
	claims := Claims{
		Type: tokenType,
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   userID.String(),
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(expiry)),
			ID:        uuid.NewString(),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(secretKey))
}

// ParseToken verifie la signature, l'expiration et le type attendu, puis
// renvoie l'id utilisateur extrait du `sub`.
func ParseToken(rawToken string, expectedType TokenType, secretKey string) (uuid.UUID, error) {
	claims := &Claims{}
	token, err := jwt.ParseWithClaims(rawToken, claims, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, ErrInvalidToken
		}
		return []byte(secretKey), nil
	})
	if err != nil || !token.Valid {
		return uuid.UUID{}, ErrInvalidToken
	}
	if claims.Type != expectedType {
		return uuid.UUID{}, ErrInvalidToken
	}

	userID, err := uuid.Parse(claims.Subject)
	if err != nil {
		return uuid.UUID{}, ErrInvalidToken
	}
	return userID, nil
}
