package server

import (
	"benchtrace/internal/auth"
	"context"
	"encoding/json"
	"fmt"
	"github.com/jackc/pgx/v5"
	"time"
)

// Embedding caches contain vectors, never the query text. Model identity is part of the key.
func (s *Server) embedding(ctx context.Context, text string) ([]float64, string, error) {
	var config struct {
		Version string `json:"embedding_version"`
	}
	if e := s.engine(ctx, "/config", map[string]string{}, &config); e != nil {
		return nil, "", e
	}
	if config.Version == "" {
		return nil, "", fmt.Errorf("missing embedding identity")
	}
	key := "embedding:" + config.Version + ":" + auth.Digest(text)
	if cached, e := s.Redis.Get(ctx, key).Bytes(); e == nil {
		var values []float64
		if json.Unmarshal(cached, &values) == nil && len(values) == 384 {
			return values, config.Version, nil
		}
	}
	var result struct {
		Embedding []float64 `json:"embedding"`
		Version   string    `json:"version"`
	}
	if e := s.engine(ctx, "/embed", map[string]string{"text": text}, &result); e != nil {
		return nil, "", e
	}
	if result.Version != config.Version {
		return nil, "", fmt.Errorf("embedding identity changed during request")
	}
	raw, e := json.Marshal(result.Embedding)
	if e == nil {
		s.Redis.Set(ctx, key, raw, 15*time.Minute)
	}
	return result.Embedding, result.Version, nil
}

// Refresh one legacy vector per idle worker tick. Text and evidence IDs are preserved.
// Queries exclude incompatible versions until this bounded backfill reaches them.
func (s *Server) refreshEmbedding(ctx context.Context) error {
	var config struct {
		Version string `json:"embedding_version"`
	}
	if err := s.engine(ctx, "/config", map[string]string{}, &config); err != nil {
		return err
	}
	if config.Version == "" {
		return fmt.Errorf("missing embedding identity")
	}
	var id, content, kind string
	err := s.DB.QueryRow(ctx, `SELECT id,content,kind FROM (
 SELECT id,content,'document' AS kind FROM document_chunks WHERE embedding_version<>$1
 UNION ALL SELECT id,left(title || E'\n' || content,19000),'knowledge' AS kind FROM knowledge_entries WHERE embedding_version<>$1
 ) pending LIMIT 1`, config.Version).Scan(&id, &content, &kind)
	if err == pgx.ErrNoRows {
		return nil
	}
	if err != nil {
		return err
	}
	values, version, err := s.embedding(ctx, content)
	if err != nil {
		return err
	}
	raw, err := json.Marshal(values)
	if err != nil {
		return err
	}
	statement := "UPDATE document_chunks SET embedding=$1::vector,embedding_version=$2 WHERE id=$3"
	if kind == "knowledge" {
		statement = "UPDATE knowledge_entries SET embedding=$1::vector,embedding_version=$2 WHERE id=$3"
	}
	_, err = s.DB.Exec(ctx, statement, string(raw), version, id)
	return err
}
