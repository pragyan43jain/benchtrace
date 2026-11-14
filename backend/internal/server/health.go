package server

import (
	"context"
	"net/http"
	"time"
)

// Readiness is bounded independently of the longer analysis request timeout.
func (s *Server) readiness(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	checks := map[string]func(context.Context) bool{
		"database": func(c context.Context) bool { return s.DB != nil && s.DB.Ping(c) == nil },
		"redis":    func(c context.Context) bool { return s.Redis != nil && s.Redis.Ping(c).Err() == nil },
		"engine": func(c context.Context) bool {
			req, err := http.NewRequestWithContext(c, http.MethodGet, s.EngineURL+"/health", nil)
			if err != nil {
				return false
			}
			req.Header.Set("Authorization", "Bearer "+s.EngineToken)
			client := s.Client
			if client == nil {
				client = http.DefaultClient
			}
			resp, err := client.Do(req)
			if err != nil {
				return false
			}
			defer resp.Body.Close()
			return resp.StatusCode == http.StatusOK
		},
	}
	type result struct {
		name string
		ok   bool
	}
	results := make(chan result, len(checks))
	for name, check := range checks {
		go func(n string, f func(context.Context) bool) { results <- result{n, f(ctx)} }(name, check)
	}
	dependencies := map[string]bool{}
	code, status := http.StatusOK, "ok"
	for range checks {
		result := <-results
		dependencies[result.name] = result.ok
		if !result.ok {
			code, status = http.StatusServiceUnavailable, "unavailable"
		}
	}
	respond(w, code, map[string]any{"status": status, "dependencies": dependencies})
}
