FROM golang:1.22 AS builder

WORKDIR /app

COPY go.mod go.sum ./

RUN go mod download

COPY . .

RUN CGO_ENABLED=0 go build -o devboard-backend .

RUN chmod +x ./devboard-backend
#-------------Stage 1-completed--------------#
FROM alpine:3.20 AS runner

WORKDIR /app

RUN adduser -D appuser

USER appuser

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

COPY --from=builder /app/devboard-backend .

EXPOSE 8080

ENTRYPOINT ["./devboard-backend"]
