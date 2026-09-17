package tasks

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	"github.com/hibiken/asynq"
	"github.com/jackc/pgx/v5/pgtype"

	"leadpilot/internal/ai"
	"leadpilot/internal/auth"
	"leadpilot/internal/db/sqlc"
	"leadpilot/internal/reputation"
)

const TypeEnrichProspect = "prospects:enrich"

type EnrichProspectPayload struct {
	CompanyID string `json:"company_id"`
}

func NewEnrichProspectTask(companyID uuid.UUID) (*asynq.Task, error) {
	payload, err := json.Marshal(EnrichProspectPayload{CompanyID: companyID.String()})
	if err != nil {
		return nil, err
	}
	return asynq.NewTask(TypeEnrichProspect, payload), nil
}

// EnrichProcessor traite les jobs d'enrichissement : Trustpilot (par
// domaine) et analyse IA (Groq, sur la page d'accueil publique). Chaque
// fournisseur est optionnel (nil si non configure) et independant - la
// panne ou l'absence de l'un n'empeche jamais l'autre de s'executer, et
// les valeurs deja en base sont preservees quand un fournisseur echoue
// plutot que remises a NULL (voir seed depuis `company` ci-dessous).
type EnrichProcessor struct {
	Queries    *sqlc.Queries
	Trustpilot *reputation.Provider
	AI         *ai.Analyzer
}

func (p *EnrichProcessor) ProcessTask(ctx context.Context, t *asynq.Task) error {
	var payload EnrichProspectPayload
	if err := json.Unmarshal(t.Payload(), &payload); err != nil {
		return fmt.Errorf("payload invalide: %w", err)
	}

	companyID, err := uuid.Parse(payload.CompanyID)
	if err != nil {
		return fmt.Errorf("company_id invalide: %w", err)
	}

	company, err := p.Queries.GetCompanyByID(ctx, auth.ToPgUUID(companyID))
	if err != nil {
		// Le prospect a pu etre supprime entre l'enqueue et le traitement :
		// ce n'est pas une erreur a retenter.
		log.Printf("enrich: prospect %s introuvable, abandon: %v", companyID, err)
		return nil
	}

	update := sqlc.UpdateEnrichmentParams{
		ID:                    company.ID,
		TrustpilotRating:      company.TrustpilotRating,
		TrustpilotReviewCount: company.TrustpilotReviewCount,
		TrustpilotFetchedAt:   company.TrustpilotFetchedAt,
		AiNeeds:               company.AiNeeds,
		AiSummary:             company.AiSummary,
		AiAnalyzedAt:          company.AiAnalyzedAt,
	}

	if p.Trustpilot != nil && company.Domain.Valid && company.Domain.String != "" {
		result, err := p.Trustpilot.FetchByDomain(ctx, company.Domain.String)
		if err != nil {
			log.Printf("enrich: Trustpilot echoue pour %s: %v", companyID, err)
		} else {
			update.TrustpilotFetchedAt = pgtype.Timestamptz{Time: time.Now(), Valid: true}
			if result != nil {
				update.TrustpilotRating = pgtype.Float4{Float32: result.Rating, Valid: true}
				update.TrustpilotReviewCount = pgtype.Int4{Int32: result.ReviewCount, Valid: true}
			}
		}
	}

	if p.AI != nil && company.WebsiteUrl.Valid && company.WebsiteUrl.String != "" {
		analysis, err := p.AI.AnalyzeWebsite(ctx, company.WebsiteUrl.String)
		if err != nil {
			log.Printf("enrich: analyse IA echouee pour %s: %v", companyID, err)
		} else {
			needsJSON, err := json.Marshal(analysis.Needs)
			if err == nil {
				update.AiNeeds = needsJSON
				update.AiSummary = pgtype.Text{String: analysis.Summary, Valid: true}
				update.AiAnalyzedAt = pgtype.Timestamptz{Time: time.Now(), Valid: true}
			}
		}
	}

	if _, err := p.Queries.UpdateEnrichment(ctx, update); err != nil {
		return fmt.Errorf("enregistrement de l'enrichissement echoue: %w", err)
	}

	return nil
}
