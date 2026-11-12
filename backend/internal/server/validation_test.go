package server

import (
	"net/http/httptest"
	"strings"
	"testing"
)

func TestJSONValidation(t *testing.T) {
	for _, body := range []string{`{"name":"x"} trailing`, `{"name":"x"}{"name":"y"}`, `{"unknown":1}`} {
		r := httptest.NewRequest("POST", "/", strings.NewReader(body))
		w := httptest.NewRecorder()
		var p struct {
			Name string `json:"name"`
		}
		if decode(w, r, &p) {
			t.Fatalf("accepted malformed input: %s", body)
		}
	}
}
func TestProjectValidation(t *testing.T) {
	if validProject(projectInput{Name: "  "}) {
		t.Fatal("blank name")
	}
	if !validProject(projectInput{Name: "ESP32"}) {
		t.Fatal("valid name rejected")
	}
}
