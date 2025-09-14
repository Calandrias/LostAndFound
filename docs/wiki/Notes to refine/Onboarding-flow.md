# Privacy-First Owner-Onboarding – Lost & Found Platform

## Ziel

**Frictionless, privacy-first Onboarding eines Owners**  
- Kein E-Mail, keine Telefonnummer, keine “unnötigen” Felder.
- Server sieht _nur_ minimal-pseudonymisierte Daten; alles Kritische bleibt clientseitig.

---

## Ablauf (Schritt für Schritt)

1. **Registrierung starten**
    - Nutzer klickt “Registrieren”
    - Frontend zeigt Formular (nur Username und Passwort, keine Mail etc.)

2. **Username & Passwortwahl**
    - Client prüft Username-Format/Länge.
    - Client prüft Passwort (Stärke, ggf. gegen bekannte Leaks).

3. **Lokales Hashing (Client)**
    - Client erstellt UsernameHash (aus Username).
    - Client erstellt PasswortHash (aus Passwort, evtl. durch KDF).

4. **Anlage im Backend (Initial Call)**
    - Client sendet UsernameHash & PasswordHash an Backend.
    - Backend erstellt neues Salt.
    - Backend verschlüsselt PasswortHash mit Salt.
    - Backend speichert UsernameHash, Salt und salted PasswordHash.
    - Bei Conflict: Timed Error (kein Enumeration-Leak).

5. **Session & Entropie**
    - Backend erzeugt starke Entropy (für Schlüsselgenerierung).
    - Backend erzeugt einen Onetime-Session Token.
    - Backend gibt Entropy & SessionToken zurück.

6. **Schlüsselpaar-Generierung (Client-Side)**
    - Client erzeugt PrivateKey aus Username, Passwort und Entropy (nur im Client).
    - Erzeugt zugehörigen PublicKey.

7. **Key-Registration (Final Call)**
    - Client sendet PublicKey, UsernameHash und SessionToken an Backend.
    - Backend prüft SessionToken und speichert PublicKey („Owner onboarding abgeschlossen”).

8. **Ab hier: Login-Flow.**

---

## Privacy- & Security-Prinzipien

- **Minimalistische Datenspeicherung:** Kein Klartext Credentials/Private Keys/Identitäten am Server.
- **Kein Tracking:** Keine E-Mails, Telefonnummern, persistenten IDs.
- **Vermeidung von Enumeration:** Keine Info bei User-Conflicts (generische Fehler, timed).
- **Alles Kryptographische (Private Keys etc.) bleibt clientseitig.**
- **Recovery**: Nur optional via Backup/Seed, niemals Email.

---

## Mermaid-Flowchart

```mermaid
    flowchart TD;
        A[User klickt "Registrieren"] --> B[Frontend: Username & Passwort erfassen]
        B --> C[Frontend prüft Format, Stärke, Leaks]
        C --> D[Frontend erstellt UsernameHash & PasswordHash]
        D --> E[Sendet beide an Backend]
        E --> F{UsernameHash schon vorhanden?}
        F -- ja --> G[Timed ErrorResponse]
        F -- nein --> H[Backend: Salt erzeugen, PasswordHash salten & speichern]
        H --> I[Backend erzeugt Entropy & SessionToken]
        I --> J[Sendet Entropy & Token an Frontend]
        J --> K[Frontend erstellt PrivateKey aus Username, Passwort, Entropy]
        K --> L[Frontend erstellt PublicKey aus PrivateKey]
        L --> M[Frontend sendet PublicKey, UsernameHash, SessionToken ans Backend]
        M --> N[Backend prüft Token & User; speichert PublicKey; Owner aktiv]
        N --> O[Weitere Logins jetzt möglich (Login-Flow)]
```