package secrets

import (
	"bytes"
	"strings"
	"testing"
)

func TestProviderSecretEncryptionIsAuthenticatedAndOwnerBound(t *testing.T) {
	key := bytes.Repeat([]byte{0x71}, 32)
	sealed, err := Encrypt(key, "user-a", "sk-test-secret")
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Contains(sealed, []byte("sk-test-secret")) {
		t.Fatal("ciphertext contains plaintext secret")
	}
	opened, err := Decrypt(key, "user-a", sealed)
	if err != nil || opened != "sk-test-secret" {
		t.Fatalf("decrypt = %q, %v", opened, err)
	}
	if _, err = Decrypt(key, "user-b", sealed); err == nil {
		t.Fatal("ciphertext decrypted for another owner")
	}
	sealed[len(sealed)-1] ^= 0xff
	if _, err = Decrypt(key, "user-a", sealed); err == nil {
		t.Fatal("tampered ciphertext accepted")
	}
}

func TestParseProviderKeyRequires32Bytes(t *testing.T) {
	if key, err := ParseKey(strings.Repeat("ab", 32)); err != nil || len(key) != 32 {
		t.Fatalf("valid key rejected: %v", err)
	}
	for _, invalid := range []string{"", "00", strings.Repeat("zz", 32), strings.Repeat("ab", 31)} {
		if _, err := ParseKey(invalid); err == nil {
			t.Fatalf("invalid key accepted: %q", invalid)
		}
	}
}
