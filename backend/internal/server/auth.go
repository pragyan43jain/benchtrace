package server

import (
	"benchtrace/internal/auth"
	"net/http"
	"net/mail"
	"strings"
	"time"
)

type credentials struct {
	Email    string `json:"email"`
	Password string `json:"password"`
	Name     string `json:"name"`
}

func (s *Server) register(w http.ResponseWriter, r *http.Request) {
	var c credentials
	if !decode(w, r, &c) {
		return
	}
	c.Email = strings.ToLower(strings.TrimSpace(c.Email))
	c.Name = strings.TrimSpace(c.Name)
	a, e := mail.ParseAddress(c.Email)
	if e != nil || a.Address != c.Email || len(c.Email) > 254 || len(c.Password) < 12 || len(c.Password) > 72 || len(c.Name) < 1 || len(c.Name) > 100 {
		fail(w, 400, "Valid email, name and a 12–72 byte password required")
		return
	}
	hash, e := auth.Hash(c.Password)
	if dbError(w, e) {
		return
	}
	id := auth.ID()
	_, e = s.DB.Exec(r.Context(), "INSERT INTO users(id,email,password_hash,name) VALUES($1,$2,$3,$4)", id, c.Email, hash, c.Name)
	if e != nil {
		fail(w, 409, "Unable to register this email")
		return
	}
	s.session(w, r, id)
}
func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	var c credentials
	if !decode(w, r, &c) {
		return
	}
	var id, hash string
	e := s.DB.QueryRow(r.Context(), "SELECT id,password_hash FROM users WHERE email=$1", strings.ToLower(strings.TrimSpace(c.Email))).Scan(&id, &hash)
	if e != nil {
		auth.Check("$2a$12$w0cE64HqsVWpHAAxQZs8ZuP.7N8fIeQ39UUTxP/ihxwxhWaWehJBu", c.Password)
		fail(w, 401, "Invalid email or password")
		return
	}
	if !auth.Check(hash, c.Password) {
		fail(w, 401, "Invalid email or password")
		return
	}
	s.session(w, r, id)
}
func (s *Server) session(w http.ResponseWriter, r *http.Request, id string) {
	token := auth.Token()
	_, e := s.DB.Exec(r.Context(), "INSERT INTO sessions(token_hash,user_id,expires_at) VALUES($1,$2,$3)", auth.Digest(token), id, time.Now().Add(7*24*time.Hour))
	if dbError(w, e) {
		return
	}
	http.SetCookie(w, &http.Cookie{Name: "benchtrace_session", Value: token, Path: "/", HttpOnly: true, Secure: s.Secure, SameSite: http.SameSiteStrictMode, MaxAge: 604800})
	respond(w, 200, map[string]string{"id": id})
}
func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	c, _ := r.Cookie("benchtrace_session")
	_, e := s.DB.Exec(r.Context(), "DELETE FROM sessions WHERE token_hash=$1", auth.Digest(c.Value))
	if dbError(w, e) {
		return
	}
	http.SetCookie(w, &http.Cookie{Name: "benchtrace_session", Value: "", Path: "/", MaxAge: -1, HttpOnly: true, Secure: s.Secure, SameSite: http.SameSiteStrictMode})
	respond(w, 200, map[string]bool{"ok": true})
}
func (s *Server) me(w http.ResponseWriter, r *http.Request) {
	v, e := s.query(r, "SELECT json_build_object('id',id,'email',email,'name',name) FROM users WHERE id=$1", user(r))
	if dbError(w, e) {
		return
	}
	respond(w, 200, v[0])
}
