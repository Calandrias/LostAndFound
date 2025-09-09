# Lost & Found - Privacy-first QR Service

Open Source service for privacy-preserving lost-and-found via QR tags with anonymous first contact, optional chat relay, and status-driven notifications.

> ⚠️ This project is in early development (“DRAFT” / “Work in Progress”).  
> Features, APIs, and architecture may change at any time.  
> Feedback welcome – privacy & security are top priorities!


## 🎯 Key Features
- Anonymous first contact with optional location sharing (consent-driven)
- Owner login only for managing tags and replies (minimal data collection)
- "Not lost" inbox buffering - messages delivered only when status changes to "lost"
- Auto-deletion with TTL; optional success-based payment or donations
- Privacy by Design: pseudonymous IDs, minimal scopes, GDPR-compliant

## 📚 Documentation
- **[Project Wiki](docs/wiki/Home.md)** - Complete documentation
- **[Architecture](docs/wiki/Architecture.md)** - System design and data model
- **[Core Flows](docs/wiki/Flows.md)** - QR scan, messaging, status switching
- **[Privacy & Security](docs/wiki/Privacy-Security.md)** - Data minimization and protection
- **[Roadmap](docs/wiki/Roadmap.md)** - Development phases
- **[Operations](docs/wiki/Operations.md)** - CI/CD and deployment

## 🚀 Quick Start
*(Coming in Phase 1)*

## 🏗️ Project Structure
```
├── frontend/           # Astro static app (islands for chat/forms)
├── runtime/           
│   ├── public/        # Finder-facing Lambdas
│   ├── admin/         # Owner-facing Lambdas  
│   └── shared/        # Common utilities
├── infra/             # CDK infrastructure stacks
├── docs/
│   ├── wiki/          # Project documentation
│   └── adr/           # Architecture Decision Records
└── .github/workflows/ # CI/CD pipelines
```

## 🤝 Contributing
This project is in early development. Documentation and ADRs are tracked in `docs/wiki/` and `docs/adr/`.

## 📄 License
*(To be decided - likely MIT or Apache-2.0)*

## 💝 Support
*(GitHub Sponsors integration coming in Phase 4)*