FROM node:18-alpine

RUN npm install -g @apideck/portman

WORKDIR /app

COPY ../eligibility-signposting-api.yaml .

CMD ["portman", "-l", "eligibility-signposting-api.yaml", "-o", "collection.json"]
