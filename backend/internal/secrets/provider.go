// Package secrets provides authenticated encryption for user-configured provider credentials.
package secrets

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"io"
)

func ParseKey(encoded string) ([]byte, error) {
	key, err := hex.DecodeString(encoded)
	if err != nil || len(key) != 32 {
		return nil, errors.New("provider encryption key must be 64 hexadecimal characters")
	}
	return key, nil
}

func Encrypt(key []byte, owner, plaintext string) ([]byte, error) {
	if len(key) != 32 || owner == "" || plaintext == "" {
		return nil, errors.New("invalid provider secret encryption input")
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	aead, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	nonce := make([]byte, aead.NonceSize())
	if _, err = io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, err
	}
	sealed := aead.Seal(nil, nonce, []byte(plaintext), []byte(owner))
	return append(nonce, sealed...), nil
}

func Decrypt(key []byte, owner string, ciphertext []byte) (string, error) {
	if len(key) != 32 || owner == "" {
		return "", errors.New("invalid provider secret decryption input")
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}
	aead, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	if len(ciphertext) < aead.NonceSize()+aead.Overhead() {
		return "", errors.New("invalid encrypted provider secret")
	}
	nonce, sealed := ciphertext[:aead.NonceSize()], ciphertext[aead.NonceSize():]
	plaintext, err := aead.Open(nil, nonce, sealed, []byte(owner))
	if err != nil {
		return "", errors.New("provider secret authentication failed")
	}
	return string(plaintext), nil
}
