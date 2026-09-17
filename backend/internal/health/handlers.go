package health

import (
	"net/http"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/labstack/echo/v4"
)

type response struct {
	Status string `json:"status"`
	DB     string `json:"db"`
}

// Handler verifie que la base repond reellement (pas juste que le
// processus API est vivant) - meme contrat que /health cote RemoteRadar.
func Handler(pool *pgxpool.Pool) echo.HandlerFunc {
	return func(c echo.Context) error {
		dbStatus := "ok"
		if err := pool.Ping(c.Request().Context()); err != nil {
			dbStatus = "error"
		}
		return c.JSON(http.StatusOK, response{Status: "ok", DB: dbStatus})
	}
}
