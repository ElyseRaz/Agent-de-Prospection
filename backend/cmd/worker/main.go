package main

import (
	"context"
	"log"
	"net/http"
	"time"

	"github.com/hibiken/asynq"

	"leadpilot/internal/ai"
	"leadpilot/internal/config"
	"leadpilot/internal/db"
	"leadpilot/internal/db/sqlc"
	"leadpilot/internal/email"
	"leadpilot/internal/reputation"
	"leadpilot/internal/tasks"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("configuration invalide: %v", err)
	}

	if err := db.RunMigrations(cfg.DatabaseURL); err != nil {
		log.Fatalf("migrations: %v", err)
	}

	ctx := context.Background()
	pool, err := db.NewPool(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("connexion base de donnees: %v", err)
	}
	defer pool.Close()

	redisConnOpt, err := asynq.ParseRedisURI(cfg.RedisURL)
	if err != nil {
		log.Fatalf("URL Redis invalide: %v", err)
	}

	srv := asynq.NewServer(redisConnOpt, asynq.Config{
		Concurrency: 5,
	})

	httpClient := &http.Client{Timeout: 15 * time.Second}
	queries := sqlc.New(pool)

	// Chaque fournisseur (enrichissement et envoi) est optionnel : construit
	// seulement si sa configuration est presente (voir internal/tasks/*.go,
	// qui tolere un fournisseur nil et saute simplement cette partie).
	var trustpilotProvider *reputation.Provider
	if cfg.TrustpilotAPIKey != "" {
		trustpilotProvider = reputation.NewProvider(cfg.TrustpilotAPIKey, httpClient)
	}
	var groqAnalyzer *ai.Analyzer
	if cfg.GroqAPIKey != "" {
		groqAnalyzer = ai.NewAnalyzer(cfg.GroqAPIKey, cfg.GroqBaseURL, cfg.GroqModel, httpClient)
	}
	var emailSender *email.Sender
	if cfg.SMTPHost != "" {
		emailSender = email.NewSender(cfg.SMTPHost, cfg.SMTPPort, cfg.SMTPUser, cfg.SMTPPassword, cfg.SMTPFrom)
	}

	enrichProcessor := &tasks.EnrichProcessor{
		Queries:    queries,
		Trustpilot: trustpilotProvider,
		AI:         groqAnalyzer,
	}
	sendCampaignProcessor := &tasks.SendCampaignProcessor{
		Queries:        queries,
		EmailSender:    emailSender,
		PublicAppURL:   cfg.PublicAppURL,
		DailySendLimit: cfg.DailySendLimit,
	}

	mux := asynq.NewServeMux()
	mux.HandleFunc(tasks.TypeEnrichProspect, enrichProcessor.ProcessTask)
	mux.HandleFunc(tasks.TypeSendCampaign, sendCampaignProcessor.ProcessTask)

	log.Printf(
		"demarrage LeadPilot worker (env=%s, trustpilot=%v, groq=%v, smtp=%v)",
		cfg.AppEnv, trustpilotProvider != nil, groqAnalyzer != nil, emailSender != nil,
	)
	if err := srv.Run(mux); err != nil {
		log.Fatalf("erreur worker asynq: %v", err)
	}
}
