CREATE TABLE provider_settings (
    user_id uuid PRIMARY KEY REFERENCES users ON DELETE CASCADE,
    model text NOT NULL DEFAULT '',
    api_key_ciphertext bytea,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (length(model) <= 200),
    CHECK (api_key_ciphertext IS NULL OR octet_length(api_key_ciphertext) BETWEEN 29 AND 4096)
);
CREATE TRIGGER provider_settings_updated BEFORE UPDATE ON provider_settings FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
