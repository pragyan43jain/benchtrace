package storage

import (
	"archive/zip"
	"bytes"
	"testing"
)

func TestValidation(t *testing.T) {
	for _, n := range []string{"../main.c", "bad.exe", "a\\b.txt"} {
		if Validate(n, []byte("hello")) == nil {
			t.Fatal(n)
		}
	}
	if Validate("main.c", []byte("void setup(){}")) != nil {
		t.Fatal("valid C rejected")
	}
	if Validate("a.pdf", []byte("not pdf")) == nil {
		t.Fatal("bad pdf accepted")
	}
}
func TestUnsafeZip(t *testing.T) {
	var b bytes.Buffer
	w := zip.NewWriter(&b)
	f, _ := w.Create("../escape.txt")
	f.Write([]byte("data"))
	w.Close()
	if _, e := Unpack("test.zip", b.Bytes()); e == nil {
		t.Fatal("traversal accepted")
	}
}
func TestZip(t *testing.T) {
	var b bytes.Buffer
	w := zip.NewWriter(&b)
	f, _ := w.Create("source/main.c")
	f.Write([]byte("void setup(){}"))
	w.Close()
	files, e := Unpack("test.zip", b.Bytes())
	if e != nil || len(files) != 1 || files[0].Name != "main.c" {
		t.Fatal(e)
	}
}

func TestZipDuplicateFlattenedNames(t *testing.T) {
	var b bytes.Buffer
	w := zip.NewWriter(&b)
	for _, name := range []string{"a/main.c", "b/main.c"} {
		f, _ := w.Create(name)
		f.Write([]byte("void f(){}"))
	}
	w.Close()
	if _, e := Unpack("a.zip", b.Bytes()); e == nil {
		t.Fatal("duplicate flattened names accepted")
	}
}
func TestOversizeAndBinary(t *testing.T) {
	if Validate("a.txt", make([]byte, MaxFile+1)) == nil {
		t.Fatal("size limit")
	}
	if Validate("a.txt", []byte{255, 254, 0}) == nil {
		t.Fatal("binary text accepted")
	}
}
