package server

import (
	"benchtrace/internal/auth"
	"encoding/json"
	"net/http"
	"strings"
)

type analysisOptions struct {
	Threshold float64 `json:"threshold"`
	Baud      int     `json:"baud"`
	CPOL      int     `json:"cpol"`
	CPHA      int     `json:"cpha"`
}

func (s *Server) reanalyze(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	var p analysisOptions
	if !decode(w, r, &p) {
		return
	}
	if p.Threshold <= 0 || p.Threshold > 100 || p.Baud < 1 || p.Baud > 10000000 || p.CPOL < 0 || p.CPOL > 1 || p.CPHA < 0 || p.CPHA > 1 {
		fail(w, 400, "Invalid threshold, baud rate or SPI mode")
		return
	}
	tx, e := s.DB.Begin(r.Context())
	if dbError(w, e) {
		return
	}
	defer tx.Rollback(r.Context())
	raw, _ := json.Marshal(p)
	tag, e := tx.Exec(r.Context(), "UPDATE project_files SET options=$1,status='queued',error='' WHERE id::text=$2 AND project_id::text=$3 AND status IN ('ready','failed')", raw, r.PathValue("file"), r.PathValue("project"))
	if dbError(w, e) {
		return
	}
	if tag.RowsAffected() != 1 {
		fail(w, 409, "File missing or already processing")
		return
	}
	_, e = tx.Exec(r.Context(), "INSERT INTO background_jobs(id,file_id) VALUES($1,$2)", auth.ID(), r.PathValue("file"))
	if dbError(w, e) {
		return
	}
	if !dbError(w, tx.Commit(r.Context())) {
		respond(w, 202, map[string]bool{"ok": true})
	}
}
func (s *Server) compare(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	var p struct {
		Left    string `json:"left"`
		Right   string `json:"right"`
		Channel string `json:"channel"`
	}
	if !decode(w, r, &p) {
		return
	}
	if len(p.Channel) > 100 {
		fail(w, 400, "Invalid channel")
		return
	}
	keys := []string{}
	for _, id := range []string{p.Left, p.Right} {
		var key string
		e := s.DB.QueryRow(r.Context(), "SELECT storage_key FROM project_files WHERE id::text=$1 AND project_id::text=$2 AND status='ready'", id, r.PathValue("project")).Scan(&key)
		if e != nil || !strings.HasSuffix(key, ".csv") {
			fail(w, 404, "Processed CSV not found")
			return
		}
		keys = append(keys, key)
	}
	var result map[string]any
	if e := s.engine(r.Context(), "/compare", map[string]any{"left": keys[0], "right": keys[1], "channel": p.Channel}, &result); e != nil {
		fail(w, 422, "Captures cannot be compared: check channel and overlapping time range")
		return
	}
	respond(w, 200, result)
}
