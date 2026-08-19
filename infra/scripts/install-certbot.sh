#!/usr/bin/env bash
# SCRUM-246 — Installe Certbot sur le VPS OVH, via snap (méthode officiellement
# recommandée par l'EFF — les paquets apt sont souvent obsolètes).
# À exécuter une seule fois, directement sur le serveur OVH (pas dans un conteneur).
#
# Sources : https://certbot.eff.org/instructions

set -euo pipefail

echo "Mise à jour des paquets..."
sudo apt update

echo "Installation de snapd..."
sudo apt install -y snapd
sudo snap install core
sudo snap refresh core

echo "Suppression d'une éventuelle installation Certbot via apt (évite les conflits)..."
sudo apt remove -y certbot || true

echo "Installation de Certbot via snap..."
sudo snap install --classic certbot

echo "Rendre certbot accessible dans le PATH..."
sudo ln -sf /snap/bin/certbot /usr/bin/certbot

echo "Vérification :"
certbot --version
