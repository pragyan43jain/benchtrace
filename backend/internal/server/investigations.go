package server

import (
	"benchtrace/internal/auth"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

func (s *Server) createInvestigation(w http.ResponseWriter, r *http.Request) {
	if !s.owns(w, r) {
		return
	}
	var p struct {
		Problem string `json:"problem"`
	}
	if !decode(w, r, &p) {
		return
	}
	if len(strings.TrimSpace(p.Problem)) < 5 || len(p.Problem) > 10000 {
		fail(w, 400, "Problem requires 5–10000 characters")
		return
	}
	id := auth.ID()
	_, e := s.DB.Exec(r.Context(), "INSERT INTO investigations(id,project_id,problem) VALUES($1,$2,$3)", id, r.PathValue("project"), p.Problem)
	if !dbError(w, e) {
		respond(w, 201, map[string]string{"id": id})
	}
}
func (s *Server) investigationData(r *http.Request) (map[string]any, error) {
	id := r.PathValue("investigation")
	v, e := s.query(r, "SELECT row_to_json(i) FROM investigations i WHERE id=$1", id)
	if e != nil {
		return nil, e
	}
	h, e := s.query(r, "SELECT row_to_json(h) FROM diagnostic_hypotheses h WHERE investigation_id=$1 ORDER BY rank", id)
	if e != nil {
		return nil, e
	}
	tests, e := s.query(r, "SELECT row_to_json(t) FROM diagnostic_tests t JOIN diagnostic_hypotheses h ON h.id=t.hypothesis_id WHERE h.investigation_id=$1 ORDER BY t.created_at", id)
	if e != nil {
		return nil, e
	}
	events, e := s.query(r, "SELECT row_to_json(t) FROM investigation_events t WHERE investigation_id=$1 ORDER BY created_at", id)
	if e != nil {
		return nil, e
	}
	evidence, e := s.query(r, "SELECT json_build_object('id',f.id,'name',f.name,'sha256',f.sha256,'category',f.category,'status',f.status) FROM investigation_evidence e JOIN project_files f ON f.id=e.file_id WHERE e.investigation_id=$1 ORDER BY f.name", id)
	if e != nil {
		return nil, e
	}
	return map[string]any{"investigation": v[0], "hypotheses": h, "tests": tests, "events": events, "evidence": evidence}, nil
}
func (s *Server) investigation(w http.ResponseWriter, r *http.Request) {
	if !s.ownsInvestigation(w, r) {
		return
	}
	v, e := s.investigationData(r)
	if !dbError(w, e) {
		respond(w, 200, v)
	}
}
func (s *Server) updateInvestigation(w http.ResponseWriter, r *http.Request) {
	if !s.ownsInvestigation(w, r) {
		return
	}
	var p struct {
		Status     string `json:"status"`
		Resolution string `json:"resolution"`
	}
	if !decode(w, r, &p) {
		return
	}
	valid := map[string]bool{"open": true, "investigating": true, "waiting_for_measurement": true, "resolved": true, "closed": true}
	if !valid[p.Status] || len(p.Resolution) > 20000 {
		fail(w, 400, "Invalid investigation status or resolution")
		return
	}
	if (p.Status == "resolved" || p.Status == "closed") && len(strings.TrimSpace(p.Resolution)) < 5 {
		fail(w, 400, "Record a resolution before resolving or closing")
		return
	}
	tx, e := s.DB.Begin(r.Context())
	if dbError(w, e) {
		return
	}
	defer tx.Rollback(r.Context())
	_, e = tx.Exec(r.Context(), "UPDATE investigations SET status=$1,resolution=$2,updated_at=now() WHERE id=$3", p.Status, p.Resolution, r.PathValue("investigation"))
	if dbError(w, e) {
		return
	}
	raw, _ := json.Marshal(p)
	_, e = tx.Exec(r.Context(), "INSERT INTO investigation_events(id,investigation_id,kind,detail) VALUES($1,$2,'status_changed',$3)", auth.ID(), r.PathValue("investigation"), raw)
	if dbError(w, e) {
		return
	}
	if !dbError(w, tx.Commit(r.Context())) {
		respond(w, 200, map[string]bool{"ok": true})
	}
}
func (s *Server) diagnose(w http.ResponseWriter, r *http.Request) {
	if !s.ownsInvestigation(w, r) {
		return
	}
	var selection struct {
		FileIDs *[]string `json:"file_ids"`
	}
	if !decode(w, r, &selection) {
		return
	}
	var problem string
	if e := s.DB.QueryRow(r.Context(), "SELECT problem FROM investigations WHERE id::text=$1", r.PathValue("investigation")).Scan(&problem); dbError(w, e) {
		return
	}
	files, e := s.query(r, "SELECT json_build_object('id',id,'name',name,'category',category,'sha256',sha256,'analysis',analysis) FROM project_files WHERE project_id::text=$1 AND status='ready' ORDER BY created_at LIMIT 200", r.PathValue("project"))
	if dbError(w, e) {
		return
	}
	if selection.FileIDs != nil {
		wanted := map[string]bool{}
		for _, id := range *selection.FileIDs {
			wanted[id] = true
		}
		selected := []map[string]any{}
		for _, file := range files {
			if wanted[file["id"].(string)] {
				selected = append(selected, file)
			}
		}
		if len(selected) != len(wanted) {
			fail(w, 409, "Every selected file must belong to this project and finish processing")
			return
		}
		files = selected
	}
	// Store only evidence relevant to diagnostic rules; waveform samples remain in measurement records.
	for _, file := range files {
		a := file["analysis"].(map[string]any)
		delete(a, "channels")
		delete(a, "time")
		delete(a, "moving_average")
	}
	if len(files) == 0 {
		fail(w, 409, "Upload and process evidence before diagnosis")
		return
	}
	var result struct {
		Hypotheses []map[string]any `json:"hypotheses"`
		Summary    string           `json:"summary"`
		Applicable *bool            `json:"applicable"`
	}
	tests, err := s.query(r, "SELECT json_build_object('id',t.id,'rule_key',h.rule_key,'observation',t.observation,'outcome',t.outcome) FROM diagnostic_tests t JOIN diagnostic_hypotheses h ON h.id=t.hypothesis_id WHERE h.investigation_id::text=$1 ORDER BY t.created_at DESC LIMIT 1000", r.PathValue("investigation"))
	if dbError(w, err) {
		return
	}
	if e = s.engine(r.Context(), "/diagnose", map[string]any{"files": files, "tests": tests, "problem": problem}, &result); e != nil {
		fail(w, 502, "Diagnostic engine unavailable")
		return
	}
	if result.Applicable != nil && !*result.Applicable {
		fail(w, 422, result.Summary)
		return
	}
	tx, e := s.DB.Begin(r.Context())
	if dbError(w, e) {
		return
	}
	defer tx.Rollback(r.Context())
	inv := r.PathValue("investigation")
	if _, e = tx.Exec(r.Context(), "DELETE FROM investigation_evidence WHERE investigation_id=$1", inv); dbError(w, e) {
		return
	}
	for _, f := range files {
		_, e = tx.Exec(r.Context(), "INSERT INTO investigation_evidence(investigation_id,file_id) VALUES($1,$2) ON CONFLICT DO NOTHING", inv, f["id"])
		if dbError(w, e) {
			return
		}
	}
	for _, h := range result.Hypotheses {
		raw, _ := json.Marshal(h)
		_, e = tx.Exec(r.Context(), `INSERT INTO diagnostic_hypotheses(id,investigation_id,rule_key,title,rank,assessment) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(investigation_id,rule_key) DO UPDATE SET title=excluded.title,rank=excluded.rank,assessment=excluded.assessment`, auth.ID(), inv, h["key"], h["title"], h["rank"], raw)
		if dbError(w, e) {
			return
		}
	}
	raw, _ := json.Marshal(map[string]any{"summary": result.Summary, "hypotheses": result.Hypotheses, "files": files, "problem": problem})
	_, e = tx.Exec(r.Context(), "INSERT INTO investigation_events(id,investigation_id,kind,detail) VALUES($1,$2,'diagnosis',$3)", auth.ID(), inv, raw)
	if dbError(w, e) {
		return
	}
	_, e = tx.Exec(r.Context(), "UPDATE investigations SET status='waiting_for_measurement',updated_at=now() WHERE id=$1", inv)
	if dbError(w, e) {
		return
	}
	if dbError(w, tx.Commit(r.Context())) {
		return
	}
	s.investigation(w, r)
}
func (s *Server) recordTest(w http.ResponseWriter, r *http.Request) {
	if !s.ownsInvestigation(w, r) {
		return
	}
	var p struct {
		HypothesisID string `json:"hypothesis_id"`
		Observation  string `json:"observation"`
		Outcome      string `json:"outcome"`
	}
	if !decode(w, r, &p) {
		return
	}
	statuses := map[string]string{"supports": "supported", "confirms": "confirmed", "rejects": "rejected", "inconclusive": "unverified"}
	status, ok := statuses[p.Outcome]
	if !ok || len(strings.TrimSpace(p.Observation)) < 5 || len(p.Observation) > 20000 {
		fail(w, 400, "Provide an outcome and observation (5–20000 characters)")
		return
	}
	tx, e := s.DB.Begin(r.Context())
	if dbError(w, e) {
		return
	}
	defer tx.Rollback(r.Context())
	tag, e := tx.Exec(r.Context(), "UPDATE diagnostic_hypotheses SET status=$1 WHERE id::text=$2 AND investigation_id::text=$3", status, p.HypothesisID, r.PathValue("investigation"))
	if dbError(w, e) {
		return
	}
	if tag.RowsAffected() != 1 {
		fail(w, 404, "Hypothesis not found")
		return
	}
	_, e = tx.Exec(r.Context(), "INSERT INTO diagnostic_tests(id,hypothesis_id,observation,outcome,recorded_by) VALUES($1,$2,$3,$4,$5)", auth.ID(), p.HypothesisID, p.Observation, p.Outcome, user(r))
	if dbError(w, e) {
		return
	}
	raw, _ := json.Marshal(p)
	_, e = tx.Exec(r.Context(), "INSERT INTO investigation_events(id,investigation_id,kind,detail) VALUES($1,$2,'test_recorded',$3)", auth.ID(), r.PathValue("investigation"), raw)
	if dbError(w, e) {
		return
	}
	if !dbError(w, tx.Commit(r.Context())) {
		respond(w, 201, map[string]bool{"ok": true})
	}
}
func reportText(v map[string]any) string {
	i := v["investigation"].(map[string]any)
	var b strings.Builder
	fmt.Fprintf(&b, "# BenchTrace diagnostic report\n\nProblem: %s\n\nStatus: %s\n\nAll conclusions are evidence-based hypotheses unless explicitly marked as user-confirmed. User-recorded tests are not independently verified by BenchTrace.\n\n", i["problem"], i["status"])
	for _, h := range v["hypotheses"].([]map[string]any) {
		a := h["assessment"].(map[string]any)
		status := h["status"]
		if status == "confirmed" {
			status = "user-confirmed"
		}
		fmt.Fprintf(&b, "## %v. %s\n\nStatus: %s\n\nRanking: %v\n\n", h["rank"], h["title"], status, a["ranking_method"])
		for _, k := range []string{"supporting_evidence", "contradictory_evidence"} {
			fmt.Fprintf(&b, "### %s\n\n", strings.ReplaceAll(k, "_", " "))
			for _, x := range a[k].([]any) {
				c := x.(map[string]any)
				location := fmt.Sprint(c["source"])
				for _, key := range []string{"page", "line", "time", "test_id"} {
					if value, ok := c[key]; ok {
						location += fmt.Sprintf(", %s %v", key, value)
					}
				}
				fmt.Fprintf(&b, "- %s [evidence %s]: %s\n", location, c["file_id"], c["excerpt"])
			}
			b.WriteString("\n")
		}
		fmt.Fprintf(&b, "Next test: %s\n\nConfirms if: %s\n\nRejects if: %s\n\nUnknowns: %v\n\n", a["recommended_test"], a["confirms_if"], a["rejects_if"], a["unknowns"])
	}
	b.WriteString("## Source manifest\n\n")
	for _, f := range v["evidence"].([]map[string]any) {
		fmt.Fprintf(&b, "- %s (%s), ID %s, SHA-256 %s\n", f["name"], f["category"], f["id"], f["sha256"])
	}
	b.WriteString("## Recorded tests\n\n")
	for _, t := range v["tests"].([]map[string]any) {
		fmt.Fprintf(&b, "- %s — %s: %s (hypothesis %s)\n", t["created_at"], t["outcome"], t["observation"], t["hypothesis_id"])
	}
	fmt.Fprintf(&b, "\n## Resolution\n\n%s\n\nInvestigation ID: %s\nProject ID: %s\nLast updated: %s\n", i["resolution"], i["id"], i["project_id"], i["updated_at"])
	return b.String()
}
func (s *Server) report(w http.ResponseWriter, r *http.Request) {
	if !s.ownsInvestigation(w, r) {
		return
	}
	v, e := s.investigationData(r)
	if dbError(w, e) {
		return
	}
	w.Header().Set("Content-Type", "text/markdown; charset=utf-8")
	w.Header().Set("Content-Disposition", `attachment; filename="benchtrace-report.md"`)
	fmt.Fprint(w, reportText(v))
}
func (s *Server) saveKnowledge(w http.ResponseWriter, r *http.Request) {
	if !s.ownsInvestigation(w, r) {
		return
	}
	v, e := s.investigationData(r)
	if dbError(w, e) {
		return
	}
	i := v["investigation"].(map[string]any)
	body := reportText(v)
	verification := "unverified"
	for _, h := range v["hypotheses"].([]map[string]any) {
		if h["status"] == "confirmed" {
			verification = "user_confirmed"
		}
	}
	var emb struct {
		Embedding []float64 `json:"embedding"`
		Version   string    `json:"version"`
	}
	if e = s.engine(r.Context(), "/embed", map[string]string{"text": body[:min(len(body), 20000)]}, &emb); e != nil {
		fail(w, 502, "Retrieval engine unavailable")
		return
	}
	b, _ := json.Marshal(emb.Embedding)
	_, e = s.DB.Exec(r.Context(), "INSERT INTO knowledge_entries(id,project_id,investigation_id,title,content,embedding,verification,embedding_version) VALUES($1,$2,$3,$4,$5,$6::vector,$7,$8)", auth.ID(), r.PathValue("project"), r.PathValue("investigation"), i["problem"], body, string(b), verification, emb.Version)
	if !dbError(w, e) {
		respond(w, 201, map[string]bool{"ok": true})
	}
}
func (s *Server) knowledge(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query().Get("q")
	verified := r.URL.Query().Get("verified") == "true"
	project := r.URL.Query().Get("project")
	if len(q) > 2000 {
		fail(w, 400, "Query too long")
		return
	}
	var v []map[string]any
	var e error
	if q == "" {
		v, e = s.query(r, "SELECT row_to_json(k) FROM knowledge_entries k JOIN projects p ON p.id=k.project_id WHERE p.owner_id=$1 AND (NOT $2 OR k.verification='user_confirmed') AND ($3='' OR k.project_id::text=$3) ORDER BY k.created_at DESC LIMIT 100", user(r), verified, project)
	} else {
		values, version, err := s.embedding(r.Context(), q)
		if err != nil {
			fail(w, 502, "Retrieval engine unavailable")
			return
		}
		raw, _ := json.Marshal(values)
		v, e = s.query(r, "SELECT row_to_json(k) FROM knowledge_entries k JOIN projects p ON p.id=k.project_id WHERE p.owner_id=$1 AND (NOT $3 OR k.verification='user_confirmed') AND ($4='' OR k.project_id::text=$4) AND k.embedding_version=$5 ORDER BY k.embedding <=> $2::vector LIMIT 20", user(r), string(raw), verified, project, version)
	}
	if !dbError(w, e) {
		respond(w, 200, v)
	}
}
