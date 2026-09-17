package main

import (
	"log"

	"github.com/hibiken/asynq"

	"leadpilot/internal/config"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("configuration invalide: %v", err)
	}

	redisConnOpt, err := asynq.ParseRedisURI(cfg.RedisURL)
	if err != nil {
		log.Fatalf("URL Redis invalide: %v", err)
	}

	srv := asynq.NewServer(redisConnOpt, asynq.Config{
		Concurrency: 5,
	})

	mux := asynq.NewServeMux()
	// Les taches d'enrichissement (Trustpilot, analyse Groq) et d'envoi de
	// campagnes s'enregistreront ici a partir de la phase 3 - le worker
	// demarre des maintenant pour valider le socle (connexion Redis,
	// boucle de traitement), sans tache metier pour l'instant.

	log.Printf("demarrage LeadPilot worker (env=%s)", cfg.AppEnv)
	if err := srv.Run(mux); err != nil {
		log.Fatalf("erreur worker asynq: %v", err)
	}
}
