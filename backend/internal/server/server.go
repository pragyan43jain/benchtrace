package server

import (
	"benchtrace/internal/auth"
	"context"
	"encoding/json"
	"errors"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"
)

type Server struct {
	DB                                        *pgxpool.Pool
	Redis                                     *redis.Client
	Client                                    *http.Client
	Origin, UploadDir, EngineURL, EngineToken string
	Secure                                    bool
}
type uidKey struct{}

func (s *Server) Routes() http.Handler {
	m := http.NewServeMux()
	m.HandleFunc("GET /api/health", func(w http.ResponseWriter, r *http.Request) {
		if s.DB.Ping(r.Context()) != nil {
			fail(w, 503, "Database unavailable")
			return
		}
		respond(w, 200, map[string]string{"status": "ok"})
	})
	m.HandleFunc("POST /api/auth/register", s.register)
	m.HandleFunc("POST /api/auth/login", s.login)
	m.Handle("POST /api/auth/logout", s.require(s.logout))
	m.Handle("GET /api/auth/me", s.require(s.me))
	m.Handle("GET /api/projects", s.require(s.projects))
	m.Handle("POST /api/projects", s.require(s.createProject))
	m.Handle("GET /api/projects/{project}", s.require(s.project))
	m.Handle("PATCH /api/projects/{project}", s.require(s.updateProject))
	m.Handle("POST /api/projects/{project}/files", s.require(s.upload))
	m.Handle("GET /api/projects/{project}/files/{file}", s.require(s.file))
	m.Handle("POST /api/projects/{project}/search", s.require(s.search))
	m.Handle("POST /api/projects/{project}/investigations", s.require(s.createInvestigation))
	m.Handle("GET /api/projects/{project}/investigations/{investigation}", s.require(s.investigation))
	m.Handle("PATCH /api/projects/{project}/investigations/{investigation}", s.require(s.updateInvestigation))
	m.Handle("POST /api/projects/{project}/investigations/{investigation}/diagnose", s.require(s.diagnose))
	m.Handle("POST /api/projects/{project}/investigations/{investigation}/tests", s.require(s.recordTest))
	m.Handle("GET /api/projects/{project}/investigations/{investigation}/report", s.require(s.report))
	m.Handle("POST /api/projects/{project}/investigations/{investigation}/save", s.require(s.saveKnowledge))
	m.Handle("GET /api/knowledge", s.require(s.knowledge))
	m.Handle("GET /api/events", s.require(s.events))
	return s.middleware(m)
}
func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
func fail(w http.ResponseWriter, status int, msg string) {
	respond(w, status, map[string]string{"error": msg})
}
func decode(w http.ResponseWriter, r *http.Request, v any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	d := json.NewDecoder(r.Body)
	d.DisallowUnknownFields()
	if e := d.Decode(v); e != nil {
		fail(w, 400, "Invalid request body")
		return false
	}
	var extra any
	if d.Decode(&extra) == nil {
		fail(w, 400, "Multiple JSON values")
		return false
	}
	return true
}
func user(r *http.Request) string { return r.Context().Value(uidKey{}).(string) }
func (s *Server) require(next http.HandlerFunc) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		c, e := r.Cookie("benchtrace_session")
		if e != nil {
			fail(w, 401, "Sign in required")
			return
		}
		var id string
		e = s.DB.QueryRow(r.Context(), "SELECT user_id FROM sessions WHERE token_hash=$1 AND expires_at>now()", auth.Digest(c.Value)).Scan(&id)
		if e != nil {
			fail(w, 401, "Session expired")
			return
		}
		next(w, r.WithContext(context.WithValue(r.Context(), uidKey{}, id)))
	})
}
func (s *Server) middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("Referrer-Policy", "same-origin")
		defer func() {
			if e := recover(); e != nil {
				slog.Error("request panic", "error", e)
				fail(w, 500, "Internal server error")
			}
		}()
		if r.Method != "GET" && r.Method != "HEAD" && r.Header.Get("Origin") != s.Origin {
			fail(w, 403, "Origin not allowed")
			return
		}
		if strings.HasPrefix(r.URL.Path, "/api/auth/") && r.Method == "POST" {
			key := "rate:" + strings.Split(r.RemoteAddr, ":")[0] + ":" + time.Now().UTC().Format("200601021504")
			n, e := s.Redis.Incr(r.Context(), key).Result()
			if e != nil {
				fail(w, 503, "Rate limiter unavailable")
				return
			}
			if n == 1 {
				s.Redis.Expire(r.Context(), key, 2*time.Minute)
			}
			if n > 20 {
				fail(w, 429, "Too many attempts; retry in one minute")
				return
			}
		}
		next.ServeHTTP(w, r)
	})
}
func (s *Server) owns(w http.ResponseWriter, r *http.Request) bool {
	var ok bool
	e := s.DB.QueryRow(r.Context(), "SELECT EXISTS(SELECT 1 FROM projects WHERE id::text=$1 AND owner_id=$2)", r.PathValue("project"), user(r)).Scan(&ok)
	if e != nil {
		fail(w, 500, "Database error")
		return false
	}
	if !ok {
		fail(w, 404, "Project not found")
		return false
	}
	return true
}
func (s *Server) ownsInvestigation(w http.ResponseWriter, r *http.Request) bool {
	if !s.owns(w, r) {
		return false
	}
	var ok bool
	s.DB.QueryRow(r.Context(), "SELECT EXISTS(SELECT 1 FROM investigations WHERE id::text=$1 AND project_id::text=$2)", r.PathValue("investigation"), r.PathValue("project")).Scan(&ok)
	if !ok {
		fail(w, 404, "Investigation not found")
	}
	return ok
}
func (s *Server) query(r *http.Request, q string, args ...any) ([]map[string]any, error) {
	rows, e := s.DB.Query(r.Context(), q, args...)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	result := []map[string]any{}
	for rows.Next() {
		var raw []byte
		if e = rows.Scan(&raw); e != nil {
			return nil, e
		}
		var v map[string]any
		if e = json.Unmarshal(raw, &v); e != nil {
			return nil, e
		}
		result = append(result, v)
	}
	return result, rows.Err()
}
func dbError(w http.ResponseWriter, e error) bool {
	if e != nil {
		slog.Error("database operation failed", "error", e)
		fail(w, 500, "Database operation failed")
		return true
	}
	return false
}

var _ = errors.Is
var _ = pgx.ErrNoRows
var _ = os.Getenv
