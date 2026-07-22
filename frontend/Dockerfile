FROM node:20-alpine

WORKDIR /app

# Copier les fichiers de dépendances
COPY package.json package-lock.json ./

# Installer les dépendances
RUN npm install

# Copier le code source
COPY . .

# Exposer le port
EXPOSE 5173

# Lancer le serveur de développement
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]