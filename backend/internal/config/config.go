package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Config centralise toute la configuration, entierement lue depuis les
// variables d'environnement (meme principe que pydantic-settings cote
// Python : rien en dur dans le code, aucun secret par defaut en prod).
type Config struct {
	AppEnv      string
	Port        string
	DatabaseURL string
	RedisURL    string

	SecretKey          string
	AccessTokenExpiry  time.Duration
	RefreshTokenExpiry time.Duration

	CORSOrigins []string
}

func Load() (Config, error) {
	secretKey := os.Getenv("SECRET_KEY")
	if secretKey == "" {
		return Config{}, fmt.Errorf("SECRET_KEY est obligatoire")
	}

	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		return Config{}, fmt.Errorf("DATABASE_URL est obligatoire")
	}

	accessMinutes := getEnvInt("ACCESS_TOKEN_EXPIRE_MINUTES", 15)
	refreshDays := getEnvInt("REFRESH_TOKEN_EXPIRE_DAYS", 14)

	return Config{
		AppEnv:             getEnv("APP_ENV", "development"),
		Port:               getEnv("PORT", "8000"),
		DatabaseURL:        databaseURL,
		RedisURL:           getEnv("REDIS_URL", "redis://redis:6379/0"),
		SecretKey:          secretKey,
		AccessTokenExpiry:  time.Duration(accessMinutes) * time.Minute,
		RefreshTokenExpiry: time.Duration(refreshDays) * 24 * time.Hour,
		CORSOrigins:        splitCSV(getEnv("CORS_ORIGINS", "http://localhost:3000")),
	}, nil
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	raw := os.Getenv(key)
	if raw == "" {
		return fallback
	}
	value, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return value
}

func splitCSV(raw string) []string {
	var result []string
	for _, item := range strings.Split(raw, ",") {
		item = strings.TrimSpace(item)
		if item != "" {
			result = append(result, item)
		}
	}
	return result
}
