FROM node:24-alpine

ENV NODE_ENV=production
ENV WATCH_PARTY_PORT=8789

WORKDIR /app

COPY tools/watch_party_player_server.js /app/tools/watch_party_player_server.js
COPY web /app/web
COPY assets /app/assets

USER node

EXPOSE 8789

CMD ["node", "tools/watch_party_player_server.js"]
