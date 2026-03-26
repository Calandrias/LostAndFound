# Security & Privacy Design

> Dieses Dokument fasst die Design-Entscheidungen, Sicherheitskonzepte und rechtlichen
> Überlegungen der Lost & Found QR-Plattform zusammen.
> Es dient als lebendiges Designdokument und Grundlage für zukünftige ADRs.

---

## 1. Grundprinzipien

Die Plattform ist nach dem **Zero-Knowledge**-Prinzip gebaut:

- Der Server kennt **keinen Klarnamen, keine E-Mail, keine Telefonnummer** eines Owners.
- Der Server kann **keine Nachrichten entschlüsseln**.
- Alle kryptographischen Operationen finden **ausschließlich im Client** (Browser) statt.
- Daten werden nur so lange gespeichert wie unbedingt nötig (**TTL + Auto-Delete**).
- Finder sind vollständig anonym – kein Account, keine Registrierung erforderlich.

---

## 2. Akteure

| Akteur | Beschreibung | Account nötig? |
|--------|-------------|---------------|
| **Owner** | Besitzer des Gegenstands, verwaltet Tags | Optional (pseudonym) |
| **Finder** | Scannt QR-Code, kontaktiert Owner anonym | ❌ Nein |
| **Admin** | Plattformbetreiber, Auditing & Abuse-Kontrolle | ✅ Intern |

---

## 3. Owner-Authentifizierung

### 3.1 Identität

Der Owner wird **niemals mit einer realen Identität verknüpft**. Der einzige Identifier ist:

```
owner_hash = "owner_" + base64url( SHA256( "lostfound_v1:" + owner_name ) )
```

- `owner_name` existiert **nur im Client** (Browser-RAM oder Kopf des Users).
- Der Server speichert ausschließlich den `owner_hash` als Primary Key.
- Kollisions-Check erfolgt atomar via DynamoDB `ConditionExpression("attribute_not_exists(owner_hash)")`.

### 3.2 Empfohlenes Authentifizierungsprotokoll: SRP (Secure Remote Password)

Statt eines klassischen Passwort-Hashes wird **SRP (RFC 5054)** empfohlen:

```
Onboarding:
  owner_name + password  ──►  SRP-Verifier + SRP-Salt  ──►  Server speichert

Login (Challenge/Response):
  Client sendet:  owner_hash + SRP client_public (A)
  Server sendet:  SRP server_public (B) + SRP-Salt
  Client sendet:  SRP client_proof (M1)
  Server sendet:  SRP server_proof (M2) + Session-Token
```

**Vorteile gegenüber bcrypt-Hash:**
- Passwort verlässt den Client **niemals**
- Server-DB-Leak gibt **kein crackcbares Datum** preis (Verifier ≠ Passwort)
- Gegenseitige Authentifizierung (Server beweist auch seine Kenntnis)

### 3.3 Client-seitige Key-Ableitung

Für verschlüsselte Daten (Storage, Kommunikation) werden Keys deterministisch abgeleitet:

```
storage_key = PBKDF2-HMAC-SHA256(
    input   = password + owner_name,
    salt    = random_entropy,  // vom Server, pro Owner fix
    rounds  = 200.000,
    length  = 256 bit
)
```

- `random_entropy` wird beim Onboarding vom Server generiert und ist öffentlich (kein Geheimnis).
- Der Owner kann den Key **jederzeit neu ableiten** solange er `owner_name` + `password` kennt.
- **Kein Key-Backup nötig** – Recovery über Passwort + `random_entropy` vom Server.

### 3.4 Sicherheitsstufen (Tiered Security)

| Tier | Zugang | Erlaubte Aktionen |
|------|--------|------------------|
| **Tier 1** (Communication) | `owner_name` + `password` (SRP) | Nachrichten lesen/schreiben, Tag-Status lesen |
| **Tier 2** (Admin) | Tier-1-Session + Paper-Code | Tags erstellen/löschen, Status ändern, Account löschen |

- **Tier-2-Elevation** läuft separat ab (z.B. 15 Minuten TTL).
- Paper-Code wird beim Onboarding einmalig generiert und dem User zur sicheren Aufbewahrung übergeben.
- Tier-2-Key-Ableitung: `PBKDF2(paper_code + owner_name + random_entropy)`.

---

## 4. Session-Management

### 4.1 Owner-Sessions

```
session_token = "sessiontok_" + base64url( random(64 bytes) )
```

- Owner-Sessions: **1 Stunde TTL** (Standard), **30 Minuten** auf fremden Geräten.
- `onetime`-Flag: Session wird nach erstem validen Request invalidiert (für Hotel-PC / fremde Geräte).
- Sessions werden in DynamoDB mit `expires_at` als TTL-Attribut gespeichert → Auto-Delete.
- Ablauf-Check **im Code** bei jeder Anfrage (DynamoDB TTL ist nicht sofort).

### 4.2 Finder-Sessions (Visitor)

- Finder hat **keinen Account** – nur eine ephemere Session.
- Session ist verknüpft mit `tag_code`, **nicht** mit einer Identität.
- Session-TTL: **8 Stunden**.
- Wiederherstellung über **Paper-Code** (siehe Abschnitt 5).

### 4.3 Fremde Geräte (Hotel-PC, Internet-Café)

Empfohlener Ansatz – in Reihenfolge der Sicherheit:

1. **QR Second-Device Login**: Owner scannt auf Smartphone einen QR-Code der am Hotel-PC angezeigt wird. Private Key verlässt das Smartphone nie.
2. **Kurzlebige Session**: `onetime: true` + 30 Minuten TTL, kein "Remember me".
3. **Tier-1 only**: Auf fremden PCs nur Kommunikation erlaubt, keine Admin-Aktionen.

> ⚠️ Kein technisches System kann einen **kompromittierten PC** (Keylogger, Malware) vollständig absichern. Der QR Second-Device Login ist der einzige Ansatz der auch dort schützt.

---

## 5. Finder-Kommunikation & E2EE

### 5.1 Paper-Code für Session-Recovery

```
1. Finder scannt QR  ──►  Browser generiert Paper-Code (6 Wörter, BIP39)
2. UI zeigt Paper-Code prominent an: "Notiere diesen Code!"
3. Server generiert: conversation_entropy (random, 32 bytes)
4. Key-Ableitung im Client:
     finder_private_key = HKDF(
         input = paper_code + conversation_entropy + tag_entropy,
         salt  = tag_code,
         info  = "lostfound_v1_finder_key"
     )
5. Nur finder_public_key geht an Server
6. Paper-Code verlässt den Browser nie
```

**Recovery**: Finder scannt QR erneut, gibt Paper-Code ein → Key wird lokal neu abgeleitet → Konversation wiederhergestellt.

### 5.2 Entropie-Schichtung

| Entropy-Quelle | Liegt bei | Zweck |
|---------------|-----------|-------|
| `tag_entropy` | Tag in DB (pro Tag fix) | Schutz vor Brute-Force auf Paper-Code |
| `conversation_entropy` | Konversation in DB (pro Konversation) | Key-Isolation zwischen verschiedenen Findern |
| `paper_code` | Nur beim Finder | Geheimnis, das Server nie kennt |

→ Alle drei müssen kompromittiert werden um den Key zu rekonstruieren.

### 5.3 End-to-End-Verschlüsselung (Roadmap)

| Phase | Verschlüsselungsmodell |
|-------|----------------------|
| **Phase 1 MVP** | Server verschlüsselt eingehende Finder-Nachricht mit `owner_public_key` bei Eingang – Owner entschlüsselt lokal |
| **Phase 2** | Echter ECDH-Schlüsseltausch: `ECDH(owner_private, finder_public)` → shared AES-GCM Key |
| **Phase 3** | Forward Secrecy: rotierende ephemere Keys pro Nachricht |

### 5.4 Two-Way Kommunikation

Der entscheidende Vorteil gegenüber One-Way-QR-Lösungen (z.B. QR-Mine):

- Owner kann **antworten** – Finder sieht die Antwort in seiner wiederhergestellten Session.
- Kein Austausch von E-Mail oder Telefonnummer nötig.
- Beide Seiten bleiben vollständig anonym.

---

## 6. Verschlüsselter Owner-Storage

```
owner_encrypted_storage = AES-GCM( storage_key, { tag_names, preferences, ... } )
```

- Liegt verschlüsselt in DynamoDB.
- Server hat **keinen Zugang zum Inhalt** – weder technisch noch rechtlich.
- `storage_key` wird vom Client bei jedem Login neu aus `password + owner_name + random_entropy` abgeleitet.
- Möglicher Inhalt: Tag-Bezeichnungen, Notification-E-Mail, persönliche Notizen, Tier-2-Schlüsselmaterial.

---

## 7. E-Mail-Benachrichtigungen

### 7.1 Grundprinzip

- E-Mail ist **optional** und wird nur bei aktivem `lost`-Status gespeichert.
- Beim Zurücksetzen auf `not_lost` wird die E-Mail **sofort und unwiderruflich gelöscht** (Hard-Delete, kein TTL-Warten).
- Maximale Speicherdauer: **90 Tage** (Auto-Reset bei Inaktivität).

### 7.2 Double-Opt-In (Mail-Challenge)

```
1. Owner setzt Tag auf "lost", gibt E-Mail ein
2. Server schickt Challenge-Mail mit OTT (TTL: 1 Stunde)
3. Owner bestätigt  ──►  E-Mail wird aktiviert (AES-GCM + KMS verschlüsselt)
4. Ohne Bestätigung: E-Mail wird nach 1 Stunde automatisch gelöscht
```

### 7.3 Technische Speicherung

- E-Mail wird **symmetrisch verschlüsselt** (AES-GCM, Key via AWS KMS).
- Separates DynamoDB-Table `TagNotification` – isolierter Lifecycle.
- KMS gibt Audit-Trail jeder Entschlüsselung (CloudTrail).
- Kein Klartext-Logging der E-Mail-Adresse.

### 7.4 Empfehlung an User

Die UI gibt beim E-Mail-Eingabefeld einen Hinweis:

> *"Tipp: Du kannst eine temporäre E-Mail-Adresse verwenden, z.B. SimpleLogin, Guerrilla Mail oder temp-mail.org. Wir benötigen deine echte Adresse nicht."*

---

## 8. Abuse-Prävention

Alle Mechanismen funktionieren **ohne Inhaltszugang** (keine Nachrichteninspektion).

| Mechanismus | Auslöser | Beschreibung |
|-------------|---------|-------------|
| **Silent Block** (Session) | Owner | Finder-Session wird blockiert. Finder sieht keinen Fehler – Nachrichten werden serverseitig verworfen (Shadowban-Prinzip). |
| **Tag-Sperre** | Owner | Keine neuen Finder-Sessions für diesen Tag möglich. |
| **Lost-Rate-Limit** | Automatisch | Tag wird nach >3 `lost`-Statuswechseln/Monat automatisch gesperrt und auf Blocklist gesetzt. Verhindert Missbrauch als anonymer Chat-Kanal. |
| **Conversation-TTL** | Automatisch | Konversationen schließen nach 30 Tagen Inaktivität automatisch. |
| **Session-Limit pro Tag** | Automatisch | Max. 5–10 gleichzeitig offene Finder-Sessions pro Tag. |
| **Message-Rate-Limit** | Automatisch | Max. X Nachrichten/Stunde pro Finder-Session. |
| **Proof-of-Work** (Phase 2) | Technisch | Browser löst kleines Rechenrätsel vor Session-Start. Unsichtbar für Menschen, kostspielig für Bots. |
| **Honeypot-Tags** (Phase 2) | Admin | Köder-Tags erkennen automatisierten Missbrauch. |

---

## 9. IP-Adressen & Logging

> ⚠️ IP-Adressen sind personenbezogene Daten (DSGVO). API Gateway und Lambda loggen sie **standardmäßig** – das muss aktiv deaktiviert werden.

### Maßnahmen:

- **API Gateway Access Logs**: IP-Felder aus Log-Format entfernen.
- **Lambda/CloudWatch**: `X-Forwarded-For`-Header **nie** loggen.
- **Strukturiertes Logging**: Nur `owner_hash` und `session_token`-Präfix als Kontext – nie IP oder E-Mail.

```python
# ✅ Korrekt:
logger.append_keys(owner_hash=req.owner_hash)

# ❌ Niemals:
logger.append_keys(ip=event["requestContext"]["identity"]["sourceIp"])
```

- Grobe Geolocation (Land) für Rate-Limiting ist akzeptabel – keine exakte IP speichern.

---

## 10. Infrastruktur & Hosting

- **AWS Region**: Ausschließlich `eu-central-1` (Frankfurt) – kein Drittlandtransfer.
- **DynamoDB TTL**: Auf allen relevanten Tables konfiguriert (`expires_at`-Attribut).
- **KMS**: Für E-Mail-Verschlüsselung und zukünftige sensitive Felder.
- **CloudFront + S3**: Statisches Frontend mit HTTPS-Only, HSTS, CSP-Headers.
- **Content Security Policy (CSP)**: `connect-src` auf eigene API beschränken – verhindert JS-Datenexfiltration.
- **Subresource Integrity (SRI)**: Für alle geladenen Scripts im Frontend-Build.

---

## 11. Rechtliche Einordnung (DSGVO / DSA)

### Was erlaubt ist ✅

- Vollständig anonyme / pseudonyme Kommunikation ist in der EU legal.
- Zero-Knowledge-Speicherung ist DSGVO-konform wenn transparent dokumentiert.
- Burn-Mail-Adressen sind ausdrücklich erlaubt.
- E-Mail mit Double-Opt-In + automatischer Löschung ist DSGVO-konform (Zweckbindung Art. 5).

### Pflichten als Betreiber

| Pflicht | Umsetzung |
|---------|-----------|
| Impressum | Pflicht in DE, auch für Beta/OSS |
| Datenschutzerklärung | Zweck, Dauer, Löschung dokumentieren |
| Verarbeitungsverzeichnis | Auch für Einzelentwickler (Art. 30 DSGVO) |
| Abuse-Mechanismus (DSA) | Silent Block + Tag-Sperre reichen für kleine Plattformen |
| Auskunftspflicht Behörden | Nur `owner_hash` + Timestamps vorhanden – kein Klartext |
| EU-Hosting | `eu-central-1` erzwingen |

### Datenschutzerklärung – Kernaussagen

> *"Wir speichern keine Namen, E-Mail-Adressen oder Telefonnummern von Owners. Der einzige Identifier ist ein kryptographischer Hash, der auf dem Gerät des Nutzers berechnet wird. Alle Nachrichteninhalte werden clientseitig verschlüsselt – wir haben technisch keinen Zugang dazu. Optionale E-Mail-Adressen für Verloren-Benachrichtigungen werden ausschließlich für diesen Zweck verwendet und sofort gelöscht wenn der Tag nicht mehr als verloren markiert ist."*

---

## 12. Offene Punkte & ADRs (TODO)

- [ ] **ADR: SRP vs. bcrypt** – Entscheidung dokumentieren und implementieren
- [ ] **ADR: Key-Ableitungs-Algorithmus** – PBKDF2 Parameter (Runden, Salt-Aufbau) festschreiben (nicht nachträglich änderbar!)
- [ ] **ADR: E2EE-Stufen** – Roadmap Phase 1→2→3 formalisieren
- [ ] **ADR: Tier-2 Admin-Path** – Paper-Code-Mechanismus spezifizieren
- [ ] IP-Logging in CDK-Stacks deaktivieren
- [ ] AWS Region `eu-central-1` in `cdk.json` erzwingen
- [ ] `owner_encrypted_storage` Pattern-Bug fixen (`+` → `*`)
- [ ] `onboarding_logic.py`: `put_owner` → `create_owner` (Collision-Check)

---

## Navigation

- [← Home](Home.md) | [Architecture →](Architecture.md)
- [↑ Back to README](../../README.md)
