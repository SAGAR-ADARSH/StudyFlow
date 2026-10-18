FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
# Proxy target is read by next.config.ts at build and runtime.
ARG API_PROXY_TARGET=http://api:8000
ENV API_PROXY_TARGET=$API_PROXY_TARGET
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
