package server

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestReadinessReportsDependencyFailure(t *testing.T) {
	engine := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(503) }))
	defer engine.Close()
	s := &Server{EngineURL: engine.URL, Client: engine.Client()}
	w := httptest.NewRecorder()
	s.Routes().ServeHTTP(w, httptest.NewRequest("GET", "/api/health", nil))
	if w.Code != 503 {
		t.Fatalf("expected unavailable, got %d", w.Code)
	}
	live := httptest.NewRecorder()
	s.Routes().ServeHTTP(live, httptest.NewRequest("GET", "/api/live", nil))
	if live.Code != 200 {
		t.Fatalf("liveness must survive dependency failures: %d", live.Code)
	}
}
