# ---------- Stage 1: Build ----------
FROM node:24-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci --legacy-peer-deps

COPY . .

RUN npm run build

#####--- --------- Stage 2: Run ----------
FROM dhi.io/nginx:1.30-alpine3.23 AS runner

WORKDIR /app

COPY --from=builder /app/dist /usr/share/nginx/html

COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf
#COPY --from=builder /app/nginx.conf.template /etc/nginx/templates/default.conf.template

USER nginx

EXPOSE 8082

CMD ["-g", "daemon off;"]

