package server

import (
	"benchtrace/internal/auth"
	"net/http"
	"strings"
)

type projectInput struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Platform    string `json:"platform"`
}

func (s *Server) projects(w http.ResponseWriter, r *http.Request) {
	v, e := s.query(r, "SELECT row_to_json(p) FROM (SELECT p.*, (SELECT count(*) FROM project_files f WHERE f.project_id=p.id) AS file_count,(SELECT count(*) FROM investigations i WHERE i.project_id=p.id) AS investigation_count FROM projects p WHERE owner_id=$1 ORDER BY updated_at DESC) p", user(r))
	if !dbError(w, e) {
		respond(w, 200, v)
	}
}
func validProject(p projectInput) bool {
	return len(strings.TrimSpace(p.Name)) > 0 && len(p.Name) <= 200 && len(p.Description) <= 5000 && len(p.Platform) <= 100
}
func (s *Server) createProject(w http.ResponseWriter, r *http.Request) {
	var p projectInput
	if !decode(w, r, &p) {
		return
	}
	if !validProject(p) {
		fail(w, 400, "Invalid project fields")
		return
	}
	if p.Platform == "" {
		p.Platform = "ESP32"
	}
	id := auth.ID()
	_, e := s.DB.Exec(r.Context(), "INSERT INTO projects(id,owner_id,name,description,platform) VALUES($1,$2,$3,$4,$5)", id, user(r), strings.TrimSpace(p.Name), p.Description, p.Platform)
	if !dbError(w, e) {
		respond(w, 201, map[string]string{"id": id})
	}
}
func (s *Server) updateProject(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	var p projectInput
	if !decode(w, r, &p) {
		return
	}
	if !validProject(p) {
		fail(w, 400, "Invalid project fields")
		return
	}
	_, e := s.DB.Exec(r.Context(), "UPDATE projects SET name=$1,description=$2,platform=$3,updated_at=now() WHERE id=$4", p.Name, p.Description, p.Platform, r.PathValue("project"))
	if !dbError(w, e) {
		respond(w, 200, map[string]bool{"ok": true})
	}
}
func (s *Server) project(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	id := r.PathValue("project")
	p, e := s.query(r, "SELECT row_to_json(p) FROM projects p WHERE id=$1", id)
	if dbError(w, e) {
		return
	}
	files, e := s.query(r, "SELECT row_to_json(f) FROM (SELECT id,name,category,size,status,error,sha256,created_at FROM project_files WHERE project_id=$1 ORDER BY created_at DESC) f", id)
	if dbError(w, e) {
		return
	}
	inv, e := s.query(r, "SELECT row_to_json(i) FROM investigations i WHERE project_id=$1 ORDER BY created_at DESC", id)
	if dbError(w, e) {
		return
	}
	respond(w, 200, map[string]any{"project": p[0], "files": files, "investigations": inv})
}

func (s *Server) activity(w http.ResponseWriter, r *http.Request) {
	rows, e := s.query(r, `SELECT row_to_json(a) FROM (SELECT i.id,i.project_id,p.name AS project,i.problem AS title,i.status,'investigation' AS kind,i.updated_at AS occurred_at FROM investigations i JOIN projects p ON p.id=i.project_id WHERE p.owner_id=$1 UNION ALL SELECT f.id,f.project_id,p.name,f.name,f.status,'file',f.created_at FROM project_files f JOIN projects p ON p.id=f.project_id WHERE p.owner_id=$1 ORDER BY occurred_at DESC LIMIT 20) a`, user(r))
	if !dbError(w, e) {
		respond(w, 200, rows)
	}
}
