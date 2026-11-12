package server

import (
	"benchtrace/internal/auth"
	"context"
	"encoding/json"
	"time"
)

// Embedding caches contain vectors, never the query text. Model identity is part of the key.
func (s *Server) embedding(ctx context.Context, text string) ([]float64, error) {
	key := "embedding:bge-small-en-v1.5:" + auth.Digest(text)
	if cached, e := s.Redis.Get(ctx, key).Bytes(); e == nil {
		var values []float64
		if json.Unmarshal(cached, &values) == nil && len(values) == 384 {
			return values, nil
		}
	}
	var result struct {
		Embedding []float64 `json:"embedding"`
	}
	if e := s.engine(ctx, "/embed", map[string]string{"text": text}, &result); e != nil {
		return nil, e
	}
	raw, e := json.Marshal(result.Embedding)
	if e == nil {
		s.Redis.Set(ctx, key, raw, 15*time.Minute)
	}
	return result.Embedding, nil
}
