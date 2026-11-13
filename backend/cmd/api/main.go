package main

import (
	"benchtrace/internal/secrets"
	"benchtrace/internal/server"
	"benchtrace/migrations"
	"context"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	db, e := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if e != nil {
		panic(e)
	}
	defer db.Close()
	if e = migrations.Apply(ctx, db); e != nil {
		panic(e)
	}
	dir := os.Getenv("UPLOAD_DIR")
	if dir == "" {
		dir = ".data/uploads"
	}
	if e = os.MkdirAll(dir, 0700); e != nil {
		panic(e)
	}
	s := &server.Server{DB: db, Redis: redis.NewClient(&redis.Options{Addr: os.Getenv("REDIS_URL")}), Client: &http.Client{Timeout: 90 * time.Second}, Origin: os.Getenv("APP_ORIGIN"), UploadDir: dir, EngineURL: os.Getenv("ENGINE_URL"), EngineToken: os.Getenv("ENGINE_TOKEN"), Secure: os.Getenv("COOKIE_SECURE") == "true"}
	if s.Origin == "" || s.EngineToken == "" {
		panic("APP_ORIGIN and ENGINE_TOKEN required")
	}
	providerKey := os.Getenv("PROVIDER_ENCRYPTION_KEY")
	if providerKey != "" {
		if _, e = secrets.ParseKey(providerKey); e != nil {
			panic("PROVIDER_ENCRYPTION_KEY must be a 32-byte hexadecimal key")
		}
	}
	s.ProviderEncryptionKey = providerKey
	defer s.Redis.Close()
	go s.Worker(ctx)
	srv := &http.Server{Addr: ":8080", Handler: s.Routes(), ReadHeaderTimeout: 10 * time.Second, ReadTimeout: 60 * time.Second, WriteTimeout: 120 * time.Second, IdleTimeout: 90 * time.Second}
	go func() {
		<-ctx.Done()
		c, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()
		srv.Shutdown(c)
	}()
	slog.Info("API listening", "address", ":8080")
	if e = srv.ListenAndServe(); e != nil && e != http.ErrServerClosed {
		panic(e)
	}
}
