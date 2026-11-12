package storage

import (
	"archive/zip"
	"bytes"
	"errors"
	"io"
	"path"
	"strings"
	"unicode/utf8"
)

const MaxFile = 10 << 20
const MaxTotal = 30 << 20

var extensions = map[string]bool{".pdf": true, ".txt": true, ".csv": true, ".json": true, ".c": true, ".cpp": true, ".h": true, ".hpp": true, ".ino": true, ".kicad_sch": true, ".net": true}

type File struct {
	Name string
	Data []byte
}

func Validate(name string, data []byte) error {
	if path.Base(name) != name || strings.ContainsAny(name, "\\\x00") || len(name) > 200 || !extensions[strings.ToLower(path.Ext(name))] {
		return errors.New("unsupported or unsafe filename")
	}
	if len(data) == 0 || len(data) > MaxFile {
		return errors.New("file must be 1 byte to 10 MiB")
	}
	if strings.HasSuffix(strings.ToLower(name), ".pdf") {
		if !bytes.HasPrefix(data, []byte("%PDF-")) {
			return errors.New("invalid PDF signature")
		}
	} else if !utf8.Valid(data) || bytes.ContainsRune(data, 0) {
		return errors.New("expected UTF-8 text")
	}
	return nil
}
func Unpack(name string, data []byte) ([]File, error) {
	if strings.ToLower(path.Ext(name)) != ".zip" {
		e := Validate(name, data)
		return []File{{name, data}}, e
	}
	z, e := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if e != nil {
		return nil, errors.New("invalid ZIP")
	}
	if len(z.File) > 100 {
		return nil, errors.New("ZIP limited to 100 entries")
	}
	result := []File{}
	total := 0
	seen := map[string]bool{}
	for _, f := range z.File {
		if strings.Contains(f.Name, "\\") || strings.HasPrefix(f.Name, "/") || path.Clean(f.Name) != strings.TrimSuffix(f.Name, "/") || strings.HasPrefix(f.Name, "../") || !f.Mode().IsRegular() && !f.FileInfo().IsDir() {
			return nil, errors.New("unsafe ZIP entry")
		}
		if f.FileInfo().IsDir() {
			continue
		}
		if f.UncompressedSize64 > MaxFile {
			return nil, errors.New("ZIP entry too large")
		}
		r, e := f.Open()
		if e != nil {
			return nil, e
		}
		b, e := io.ReadAll(io.LimitReader(r, MaxFile+1))
		r.Close()
		if e != nil {
			return nil, e
		}
		total += len(b)
		if total > MaxTotal {
			return nil, errors.New("ZIP exceeds 30 MiB extracted limit")
		}
		n := path.Base(f.Name)
		if seen[n] {
			return nil, errors.New("duplicate ZIP filename")
		}
		seen[n] = true
		if e := Validate(n, b); e != nil {
			return nil, e
		}
		result = append(result, File{n, b})
	}
	if len(result) == 0 {
		return nil, errors.New("empty archive")
	}
	return result, nil
}
func Category(name string) string {
	switch strings.ToLower(path.Ext(name)) {
	case ".c", ".cpp", ".h", ".hpp", ".ino":
		return "firmware"
	case ".kicad_sch", ".net":
		return "schematic"
	case ".csv":
		return "measurement"
	case ".pdf":
		return "datasheet"
	}
	return "document"
}
