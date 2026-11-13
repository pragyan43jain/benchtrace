package server

import (
	"benchtrace/internal/auth"
	"benchtrace/internal/secrets"
	"context"
	"github.com/jackc/pgx/v5"
	"net/http"
	"os"
	"strings"
	"time"
)

func (s *Server) configuration(w http.ResponseWriter, r *http.Request) {
	var out map[string]any
	if e := s.engine(r.Context(), "/config", map[string]any{}, &out); e != nil {
		fail(w, 502, "Engine configuration unavailable")
		return
	}
	state, e := s.providerState(r.Context(), user(r))
	if e != nil {
		fail(w, 500, "Provider settings unavailable")
		return
	}
	for k, v := range state {
		out[k] = v
	}
	respond(w, 200, out)
}

type providerConfig struct {
	BaseURL string `json:"base_url"`
	Model   string `json:"model"`
	APIKey  string `json:"api_key"`
}

func (s *Server) providerForUser(ctx context.Context, owner string) (providerConfig, error) {
	cfg := providerConfig{BaseURL: os.Getenv("LLM_BASE_URL"), Model: os.Getenv("LLM_MODEL"), APIKey: os.Getenv("LLM_API_KEY")}
	var model string
	var ciphertext []byte
	err := s.DB.QueryRow(ctx, "SELECT model,api_key_ciphertext FROM provider_settings WHERE user_id=$1", owner).Scan(&model, &ciphertext)
	if err != nil && err != pgx.ErrNoRows {
		return providerConfig{}, err
	}
	if model != "" {
		cfg.Model = model
	}
	if len(ciphertext) > 0 {
		key, err := secrets.ParseKey(s.ProviderEncryptionKey)
		if err != nil {
			return providerConfig{}, err
		}
		cfg.APIKey, err = secrets.Decrypt(key, owner, ciphertext)
		if err != nil {
			return providerConfig{}, err
		}
	}
	return cfg, nil
}

func (s *Server) providerState(ctx context.Context, owner string) (map[string]any, error) {
	model := os.Getenv("LLM_MODEL")
	var accountModel string
	var accountKeySet bool
	err := s.DB.QueryRow(ctx, "SELECT model,api_key_ciphertext IS NOT NULL FROM provider_settings WHERE user_id=$1", owner).Scan(&accountModel, &accountKeySet)
	if err != nil && err != pgx.ErrNoRows {
		return nil, err
	}
	if accountModel != "" {
		model = accountModel
	}
	_, encryptionErr := secrets.ParseKey(s.ProviderEncryptionKey)
	return map[string]any{
		"provider_available":    strings.TrimSpace(os.Getenv("LLM_BASE_URL")) != "",
		"provider_model":        model,
		"provider_key_set":      accountKeySet,
		"provider_key_editable": encryptionErr == nil,
	}, nil
}

func (s *Server) providerSettings(w http.ResponseWriter, r *http.Request) {
	state, err := s.providerState(r.Context(), user(r))
	if dbError(w, err) {
		return
	}
	respond(w, 200, state)
}

func (s *Server) saveProviderSettings(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Model       string `json:"model"`
		APIKey      string `json:"api_key"`
		ClearAPIKey bool   `json:"clear_api_key"`
	}
	if !decode(w, r, &input) {
		return
	}
	input.Model = strings.TrimSpace(input.Model)
	if len(input.Model) > 200 || len(input.APIKey) > 2048 || (input.ClearAPIKey && input.APIKey != "") {
		fail(w, 400, "Invalid provider settings")
		return
	}
	var ciphertext []byte
	var err error
	if input.APIKey != "" {
		key, keyErr := secrets.ParseKey(s.ProviderEncryptionKey)
		if keyErr != nil {
			fail(w, 503, "Provider key storage is not configured by this deployment")
			return
		}
		ciphertext, err = secrets.Encrypt(key, user(r), input.APIKey)
		if err != nil {
			fail(w, 500, "Provider key could not be stored")
			return
		}
	}
	switch {
	case input.ClearAPIKey:
		_, err = s.DB.Exec(r.Context(), `INSERT INTO provider_settings(user_id,model,api_key_ciphertext) VALUES($1,$2,NULL)
			ON CONFLICT(user_id) DO UPDATE SET model=excluded.model,api_key_ciphertext=NULL`, user(r), input.Model)
	case input.APIKey != "":
		_, err = s.DB.Exec(r.Context(), `INSERT INTO provider_settings(user_id,model,api_key_ciphertext) VALUES($1,$2,$3)
			ON CONFLICT(user_id) DO UPDATE SET model=excluded.model,api_key_ciphertext=excluded.api_key_ciphertext`, user(r), input.Model, ciphertext)
	default:
		_, err = s.DB.Exec(r.Context(), `INSERT INTO provider_settings(user_id,model) VALUES($1,$2)
			ON CONFLICT(user_id) DO UPDATE SET model=excluded.model`, user(r), input.Model)
	}
	if dbError(w, err) {
		return
	}
	state, err := s.providerState(r.Context(), user(r))
	if dbError(w, err) {
		return
	}
	respond(w, 200, state)
}

func (s *Server) providerTest(w http.ResponseWriter, r *http.Request) {
	key := "rate:provider-test:" + user(r) + ":" + time.Now().UTC().Format("200601021504")
	count, err := s.Redis.Eval(r.Context(), "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],120) end; return n", []string{key}).Int64()
	if err != nil {
		fail(w, 503, "Provider connection limiter unavailable")
		return
	}
	if count > 3 {
		w.Header().Set("Retry-After", "60")
		fail(w, 429, "Provider connection check limit reached; retry in one minute")
		return
	}
	provider, e := s.providerForUser(r.Context(), user(r))
	if dbError(w, e) {
		return
	}
	var out map[string]any
	if e := s.engine(r.Context(), "/provider/test", map[string]any{"provider": provider}, &out); e != nil {
		fail(w, 502, "Provider connection check unavailable")
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
