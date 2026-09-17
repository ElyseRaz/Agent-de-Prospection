package main

import (
	"context"
	"log"

	"leadpilot/internal/config"
	"leadpilot/internal/db"
	"leadpilot/internal/httpserver"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("configuration invalide: %v", err)
	}

	ctx := context.Background()
	pool, err := db.NewPool(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("connexion base de donnees: %v", err)
	}
	defer pool.Close()

	e := httpserver.New(cfg, pool)

	log.Printf("demarrage LeadPilot API sur le port %s (env=%s)", cfg.Port, cfg.AppEnv)
	if err := e.Start(":" + cfg.Port); err != nil {
		log.Fatalf("erreur serveur HTTP: %v", err)
	}
}
