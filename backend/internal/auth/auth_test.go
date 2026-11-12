package auth

import "testing"

func TestPasswords(t *testing.T) {
	h, e := Hash("long-enough-password")
	if e != nil || !Check(h, "long-enough-password") || Check(h, "wrong") {
		t.Fatal("password verification failed")
	}
	if Digest(Token()) == Digest(Token()) {
		t.Fatal("tokens reused")
	}
	if len(ID()) != 36 {
		t.Fatal("invalid UUID")
	}
}
