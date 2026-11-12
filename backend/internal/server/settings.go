package server

import (
	"benchtrace/internal/auth"
	"net/http"
	"strings"
)

func (s *Server) configuration(w http.ResponseWriter, r *http.Request) {
	var out map[string]any
	if e := s.engine(r.Context(), "/config", map[string]any{}, &out); e != nil {
		fail(w, 502, "Engine configuration unavailable")
		return
	}
	respond(w, 200, out)
}
func (s *Server) profile(w http.ResponseWriter, r *http.Request) {
	var p struct {
		Name            string `json:"name"`
		CurrentPassword string `json:"current_password"`
		NewPassword     string `json:"new_password"`
	}
	if !decode(w, r, &p) {
		return
	}
	p.Name = strings.TrimSpace(p.Name)
	if len(p.Name) < 1 || len(p.Name) > 100 {
		fail(w, 400, "Name requires 1–100 characters")
		return
	}
	if p.NewPassword != "" {
		if len(p.NewPassword) < 12 || len(p.NewPassword) > 72 {
			fail(w, 400, "Password requires 12–72 bytes")
			return
		}
		var old string
		if e := s.DB.QueryRow(r.Context(), "SELECT password_hash FROM users WHERE id=$1", user(r)).Scan(&old); dbError(w, e) {
			return
		}
		if !auth.Check(old, p.CurrentPassword) {
			fail(w, 403, "Current password is incorrect")
			return
		}
		hash, e := auth.Hash(p.NewPassword)
		if dbError(w, e) {
			return
		}
		tx, e := s.DB.Begin(r.Context())
		if dbError(w, e) {
			return
		}
		defer tx.Rollback(r.Context())
		if _, e = tx.Exec(r.Context(), "UPDATE users SET name=$1,password_hash=$2 WHERE id=$3", p.Name, hash, user(r)); dbError(w, e) {
			return
		}
		if _, e = tx.Exec(r.Context(), "DELETE FROM sessions WHERE user_id=$1", user(r)); dbError(w, e) {
			return
		}
		if dbError(w, tx.Commit(r.Context())) {
			return
		}
		s.session(w, r, user(r))
		return
	}
	_, e := s.DB.Exec(r.Context(), "UPDATE users SET name=$1 WHERE id=$2", p.Name, user(r))
	if !dbError(w, e) {
		respond(w, 200, map[string]bool{"ok": true})
	}
}
