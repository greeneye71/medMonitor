# Claude Code Workflow — medMonitor

## Modello AI

**Usa sempre `claude-opus-4-6` per tutte le fasi del progetto.**
```bash
claude config set model claude-opus-4-6
```

## Repository GitHub
```bash
# Installa e autentica gh
sudo apt install -y gh && gh auth login

# Crea repository
gh repo create medMonitor \
  --private \
  --description "medMonitor — monitoraggio temperatura con FastAPI, TinyFlux/TimescaleDB e Plotly Dash"

# Inizializza e primo push
git init
git add .
git commit -m "[init] struttura iniziale progetto"
git push -u origin main

# Proteggi branch main
gh api repos/{owner}/medMonitor/branches/main/protection \
  --method PUT \
  --field required_pull_request_reviews='{"required_approving_review_count":1}'
```

## Flusso per ogni feature
```bash
git checkout -b feature/nome-feature
# ... sviluppo con Claude Code ...
git add .
git commit -m "[feat] descrizione modifica"
git push origin feature/nome-feature
gh pr create --title "Titolo PR" --base main --label "label"
gh issue close N
```

## Tabella fasi

| Fase | Branch | Release |
|---|---|---|
| Setup + Docker | feature/project-setup | — |
| Database Adapter | feature/database-adapter | — |
| Config + Thresholds | feature/config-system | — |
| MQTT + API REST | feature/backend | v0.2.0 |
| Alert Service | feature/alerts | — |
| Dashboard real-time | feature/dashboard | v0.3.0 |
| Demo Mode | feature/demo-mode | v0.4.0 |
| Soglie per sensore | feature/per-sensor-thresholds | v0.5.0 |
| Test suite | feature/test-suite | v1.0.0 |

## Convenzioni commit
```
[feat]     nuova funzionalità
[fix]      correzione bug
[docs]     documentazione
[test]     test
[refactor] refactoring senza nuove feature
```

## Checklist pre-deploy

- [ ] .env configurato (mai committato, in .gitignore)
- [ ] .env.example committato con valori placeholder
- [ ] Password database modificata
- [ ] SMTP testato con POST /api/config/test-email
- [ ] IMAP testato con POST /api/config/test-imap (se configurato)
- [ ] IP gateway ZigBee corretto
- [ ] Test suite: pytest backend/tests/ -v --cov=backend (> 80%)
- [ ] Servizi avviati (Windows nativo o docker compose up -d)
- [ ] Dashboard: http://localhost:8050
- [ ] Demo mode: scenario=full_stress, speed=10x funzionante
- [ ] Soglie per sensore salvate correttamente in data/config.json
- [ ] gh release create v1.0.0