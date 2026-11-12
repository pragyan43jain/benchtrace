package server

import (
	"benchtrace/internal/auth"
	"benchtrace/internal/storage"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/coder/websocket"
	"io"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func (s *Server) upload(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, storage.MaxTotal+1<<20)
	if e := r.ParseMultipartForm(storage.MaxTotal); e != nil {
		fail(w, 400, "Invalid upload or size limit exceeded")
		return
	}
	defer r.MultipartForm.RemoveAll()
	f, h, e := r.FormFile("file")
	if e != nil {
		fail(w, 400, "File is required")
		return
	}
	defer f.Close()
	data, e := io.ReadAll(io.LimitReader(f, storage.MaxTotal+1))
	if e != nil || len(data) > storage.MaxTotal {
		fail(w, 400, "Upload exceeds 30 MiB")
		return
	}
	files, e := storage.Unpack(h.Filename, data)
	if e != nil {
		fail(w, 400, e.Error())
		return
	}
	category := r.FormValue("category")
	valid := map[string]bool{"firmware": true, "schematic": true, "datasheet": true, "measurement": true, "log": true, "document": true}
	if category != "" && !valid[category] {
		fail(w, 400, "Invalid category")
		return
	}
	tx, e := s.DB.Begin(r.Context())
	if dbError(w, e) {
		return
	}
	defer tx.Rollback(r.Context())
	written := []string{}
	committed := false
	defer func() {
		if !committed {
			for _, p := range written {
				os.Remove(p)
			}
		}
	}()
	ids := []string{}
	for _, file := range files {
		id := auth.ID()
		key := id + strings.ToLower(filepath.Ext(file.Name))
		p := filepath.Join(s.UploadDir, key)
		if e = os.WriteFile(p, file.Data, 0600); e != nil {
			fail(w, 500, "Storage write failed")
			return
		}
		written = append(written, p)
		cat := category
		if cat == "" {
			cat = storage.Category(file.Name)
		}
		_, e = tx.Exec(r.Context(), "INSERT INTO project_files(id,project_id,name,category,storage_key,sha256,size) VALUES($1,$2,$3,$4,$5,$6,$7)", id, r.PathValue("project"), file.Name, cat, key, auth.Digest(string(file.Data)), len(file.Data))
		if dbError(w, e) {
			return
		}
		_, e = tx.Exec(r.Context(), "INSERT INTO background_jobs(id,file_id) VALUES($1,$2)", auth.ID(), id)
		if dbError(w, e) {
			return
		}
		ids = append(ids, id)
	}
	if dbError(w, tx.Commit(r.Context())) {
		return
	}
	committed = true
	s.Redis.Publish(r.Context(), "jobs", "wake")
	respond(w, 202, map[string]any{"ids": ids})
}
func (s *Server) file(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	v, e := s.query(r, "SELECT row_to_json(f) FROM (SELECT id,name,category,status,error,analysis,sha256 FROM project_files WHERE id::text=$1 AND project_id::text=$2) f", r.PathValue("file"), r.PathValue("project"))
	if dbError(w, e) {
		return
	}
	if len(v) == 0 {
		fail(w, 404, "File not found")
		return
	}
	respond(w, 200, v[0])
}
func (s *Server) engine(ctx context.Context, route string, input any, output any) error {
	b, e := json.Marshal(input)
	if e != nil {
		return e
	}
	req, e := http.NewRequestWithContext(ctx, "POST", s.EngineURL+route, bytes.NewReader(b))
	if e != nil {
		return e
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+s.EngineToken)
	res, e := s.Client.Do(req)
	if e != nil {
		return e
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		body, _ := io.ReadAll(io.LimitReader(res.Body, 1000))
		return fmt.Errorf("analysis rejected (%d): %s", res.StatusCode, body)
	}
	return json.NewDecoder(io.LimitReader(res.Body, 50<<20)).Decode(output)
}
func (s *Server) Worker(ctx context.Context) {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
		// Durable PostgreSQL queue; Redis supplies notifications, never sole durability.
		_, e := s.DB.Exec(ctx, "UPDATE background_jobs SET status='queued' WHERE status='processing' AND updated_at<now()-interval '5 minutes'")
		if e != nil {
			slog.Error("queue recovery", "error", e)
			continue
		}
		_, e = s.DB.Exec(ctx, "UPDATE background_jobs SET status='failed',error='Recovery attempt limit reached' WHERE status='queued' AND attempts>=3")
		if e != nil {
			slog.Error("queue attempt limit", "error", e)
			continue
		}
		_, e = s.DB.Exec(ctx, "UPDATE project_files f SET status='failed',error=j.error FROM background_jobs j WHERE j.file_id=f.id AND j.status='failed' AND f.status='processing'")
		if e != nil {
			slog.Error("queue file recovery", "error", e)
			continue
		}
		var id, file, key string
		e = s.DB.QueryRow(ctx, `WITH job AS (SELECT id FROM background_jobs WHERE status='queued' AND attempts<3 ORDER BY updated_at FOR UPDATE SKIP LOCKED LIMIT 1) UPDATE background_jobs j SET status='processing',attempts=attempts+1,updated_at=now() FROM job WHERE j.id=job.id RETURNING j.id,j.file_id,(SELECT storage_key FROM project_files WHERE id=j.file_id)`).Scan(&id, &file, &key)
		if e != nil {
			continue
		}
		s.DB.Exec(ctx, "UPDATE project_files SET status='processing' WHERE id=$1", file)
		var options map[string]any
		var optionsRaw []byte
		s.DB.QueryRow(ctx, "SELECT options FROM project_files WHERE id=$1", file).Scan(&optionsRaw)
		json.Unmarshal(optionsRaw, &options)
		var result map[string]any
		e = s.engine(ctx, "/process", map[string]any{"storage_key": key, "options": options}, &result)
		if e == nil {
			e = s.storeAnalysis(ctx, file, id, result)
		}
		if e != nil {
			slog.Warn("analysis failed", "file", file, "error", e)
			s.DB.Exec(ctx, "UPDATE background_jobs SET status='failed',error=$1,updated_at=now() WHERE id=$2", e.Error(), id)
			s.DB.Exec(ctx, "UPDATE project_files SET status='failed',error=$1 WHERE id=$2", e.Error(), file)
		}
		s.Redis.Publish(ctx, "events", file)
	}
}
func (s *Server) storeAnalysis(ctx context.Context, file, job string, a map[string]any) error {
	tx, e := s.DB.Begin(ctx)
	if e != nil {
		return e
	}
	defer tx.Rollback(ctx)
	if chunks, ok := a["chunks"].([]any); ok {
		_, e = tx.Exec(ctx, "INSERT INTO documents(id,pages) VALUES($1,$2) ON CONFLICT(id) DO UPDATE SET pages=excluded.pages", file, a["pages"])
		if e != nil {
			return e
		}
		if _, e = tx.Exec(ctx, "DELETE FROM document_chunks WHERE document_id=$1", file); e != nil {
			return e
		}
		for _, c := range chunks {
			x := c.(map[string]any)
			v, _ := json.Marshal(x["embedding"])
			_, e = tx.Exec(ctx, "INSERT INTO document_chunks(id,document_id,page,content,embedding) VALUES($1,$2,$3,$4,$5::vector)", auth.ID(), file, x["page"], x["content"], string(v))
			if e != nil {
				return e
			}
			delete(x, "embedding")
		}
	}
	b, e := json.Marshal(a)
	if e != nil {
		return e
	}
	if a["kind"] == "waveform" {
		_, e = tx.Exec(ctx, "INSERT INTO measurement_files(id,metadata) VALUES($1,$2) ON CONFLICT(id) DO UPDATE SET metadata=excluded.metadata", file, b)
		if e != nil {
			return e
		}
		_, e = tx.Exec(ctx, "INSERT INTO measurement_results(id,file_id,result) VALUES($1,$2,$3)", auth.ID(), file, b)
		if e != nil {
			return e
		}
	}
	if a["kind"] == "circuit" {
		if _, e = tx.Exec(ctx, "DELETE FROM components WHERE file_id=$1", file); e != nil {
			return e
		}
		for _, c := range a["components"].([]any) {
			x := c.(map[string]any)
			raw, _ := json.Marshal(x)
			_, e = tx.Exec(ctx, "INSERT INTO components(id,file_id,reference,properties) VALUES($1,$2,$3,$4)", auth.ID(), file, x["reference"], raw)
			if e != nil {
				return e
			}
		}
	}
	_, e = tx.Exec(ctx, "UPDATE project_files SET analysis=$1,status='ready',error='' WHERE id=$2", b, file)
	if e != nil {
		return e
	}
	_, e = tx.Exec(ctx, "UPDATE background_jobs SET status='complete',error='',updated_at=now() WHERE id=$1", job)
	if e != nil {
		return e
	}
	return tx.Commit(ctx)
}
func (s *Server) search(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	var q struct {
		Query string `json:"query"`
	}
	if !decode(w, r, &q) {
		return
	}
	if len(strings.TrimSpace(q.Query)) == 0 || len(q.Query) > 2000 {
		fail(w, 400, "Query requires 1–2000 characters")
		return
	}
	var v struct {
		Embedding []float64 `json:"embedding"`
	}
	if e := s.engine(r.Context(), "/embed", map[string]string{"text": q.Query}, &v); e != nil {
		fail(w, 502, "Retrieval engine unavailable")
		return
	}
	b, _ := json.Marshal(v.Embedding)
	rows, e := s.query(r, `SELECT row_to_json(x) FROM (SELECT c.id,c.document_id AS file_id,f.name AS source,c.page,c.content,1-(c.embedding <=> $2::vector) AS similarity FROM document_chunks c JOIN project_files f ON f.id=c.document_id WHERE f.project_id::text=$1 ORDER BY c.embedding <=> $2::vector LIMIT 6) x`, r.PathValue("project"), string(b))
	if dbError(w, e) {
		return
	}
	var answer map[string]any
	if e := s.engine(r.Context(), "/answer", map[string]any{"question": q.Query, "evidence": rows}, &answer); e != nil {
		fail(w, 502, "Answer engine unavailable")
		return
	}
	answer["evidence"] = rows
	respond(w, 200, answer)
}
func (s *Server) events(w http.ResponseWriter, r *http.Request) {
	c, e := websocket.Accept(w, r, &websocket.AcceptOptions{OriginPatterns: []string{strings.TrimPrefix(strings.TrimPrefix(s.Origin, "https://"), "http://")}})
	if e != nil {
		return
	}
	defer c.CloseNow()
	ctx, cancel := context.WithCancel(r.Context())
	defer cancel()
	ctx = c.CloseRead(ctx)
	sub := s.Redis.Subscribe(ctx, "events")
	defer sub.Close()
	for {
		select {
		case <-ctx.Done():
			return
		case msg := <-sub.Channel():
			if msg == nil {
				return
			}
			var ok bool
			s.DB.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM project_files f JOIN projects p ON p.id=f.project_id WHERE f.id::text=$1 AND p.owner_id=$2)", msg.Payload, user(r)).Scan(&ok)
			if ok {
				if e = c.Write(ctx, websocket.MessageText, []byte(`{"type":"files_changed"}`)); e != nil {
					return
				}
			}
		}
	}
}
