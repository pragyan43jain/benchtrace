FROM golang:1.26.11-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /api ./cmd/api
FROM alpine:3.21.3
RUN adduser -D -u 10001 app && mkdir /uploads && chown app /uploads
WORKDIR /app
COPY --from=build /api /app/api
COPY migrations migrations
USER app
CMD ["/app/api"]
