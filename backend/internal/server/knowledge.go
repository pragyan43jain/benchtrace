package server

import (
	"benchtrace/internal/auth"
	"encoding/json"
	"net/http"
	"strings"
)

func (s *Server) createProcedure(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	var p struct {
		Title   string `json:"title"`
		Content string `json:"content"`
	}
	if !decode(w, r, &p) {
		return
	}
	if len(strings.TrimSpace(p.Title)) < 3 || len(p.Title) > 200 || len(strings.TrimSpace(p.Content)) < 10 || len(p.Content) > 20000 {
		fail(w, 400, "Procedure requires a title (3–200 characters) and steps (10–20000 characters)")
		return
	}
	var emb struct {
		Embedding []float64 `json:"embedding"`
		Version   string    `json:"version"`
	}
	if e := s.engine(r.Context(), "/embed", map[string]string{"text": p.Title + "\n" + p.Content[:min(len(p.Content), 19000)]}, &emb); e != nil {
		fail(w, 502, "Retrieval engine unavailable")
		return
	}
	raw, _ := json.Marshal(emb.Embedding)
	id := auth.ID()
	_, e := s.DB.Exec(r.Context(), "INSERT INTO knowledge_entries(id,project_id,title,content,embedding,kind,embedding_version) VALUES($1,$2,$3,$4,$5::vector,'procedure',$6)", id, r.PathValue("project"), p.Title, p.Content, string(raw), emb.Version)
	if !dbError(w, e) {
		respond(w, 201, map[string]string{"id": id})
	}
}
func (s *Server) components(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	rows, e := s.query(r, "SELECT row_to_json(c) FROM (SELECT c.*,f.name AS source FROM components c JOIN project_files f ON f.id=c.file_id WHERE f.project_id::text=$1 ORDER BY c.reference) c", r.PathValue("project"))
	if !dbError(w, e) {
		respond(w, 200, rows)
	}
}
func (s *Server) projectHistory(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	rows, e := s.query(r, "SELECT row_to_json(e) FROM project_events e WHERE project_id::text=$1 ORDER BY created_at DESC LIMIT 200", r.PathValue("project"))
	if !dbError(w, e) {
		respond(w, 200, rows)
	}
}
func (s *Server) preferences(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	var p analysisOptions
	if !decode(w, r, &p) {
		return
	}
	if !validOptions(p) {
		fail(w, 400, "Invalid analysis defaults")
		return
	}
	raw, _ := json.Marshal(p)
	tx, e := s.DB.Begin(r.Context())
	if dbError(w, e) {
		return
	}
	defer tx.Rollback(r.Context())
	if _, e = tx.Exec(r.Context(), "UPDATE projects SET preferences=$1,updated_at=now() WHERE id::text=$2", raw, r.PathValue("project")); dbError(w, e) {
		return
	}
	if _, e = tx.Exec(r.Context(), "INSERT INTO project_events(id,project_id,actor_id,kind,detail) VALUES($1,$2,$3,'preferences_changed',$4)", auth.ID(), r.PathValue("project"), user(r), raw); dbError(w, e) {
		return
	}
	if !dbError(w, tx.Commit(r.Context())) {
		respond(w, 200, map[string]bool{"ok": true})
	}
}
