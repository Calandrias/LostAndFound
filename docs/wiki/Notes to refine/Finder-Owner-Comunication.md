# Lost & Found – Anonymer, sicherer Kommunikations-Flow mit Multi-Owner

## Grundprinzipien

- **Keine Registrierung notwendig:** Tag-Owner und Finder bleiben pseudonym.
- **Vollständige Verschlüsselung:** Nachrichten, Schlüssel und Identitäten sind Ende-zu-Ende geschützt.
- **Zero Knowledge Backend:** Das Backend speichert/relayed nur verschlüsselte Inhalte, nie Klartext oder Private Keys.
- **Multi-Owner:** Jeder Tag kann mehreren Besitzern gehören, ohne dass Finder oder Owner voneinander wissen.

---

## Ablauf: Finder-zu-Owner-Kommunikation

### 1. Schlüsselerzeugung und Tag-Claim

- Das Frontend erzeugt beim Claiming für jeden Tag ein eigenes Tag-Schlüsselpaar (asymmetrisch).
- Der **Tag Private Key** wird mit dem **Owner Public Key** verschlüsselt und im Backend gespeichert.
- Der **Owner-Private-Key** verlässt niemals den Browser des Owners.

### 2. Nachricht an Owner (Broadcast Encryption-Prinzip)

- Der Finder erhält beim Scan den Tag Public Key.
- Finder generiert ein frisches (temporäres) eigenes Finder-Schlüsselpaar.
- Die Nachricht wird:
    - a) – Hybride Verschlüsselung: Zuerst symmetrisch (z. B. AES) verschlüsselt.
    - b) – Der zufällige Session-Key wird per Multi-Recipient/Private Broadcast Encryption für alle Owner Public Keys „eingewickelt“ (Keyblock für Empfänger, nicht für Finder erkennbar).
- Der **Finder-Public-Key** wird Teil des Nachrichtenblocks zur späteren Antwort.
- Das Backend speichert/relayed ausschließlich verschlüsselte Nachrichten.

### 3. Antwort vom Owner an Finder (Rückkanal)

- Jeder berechtigte Owner kann mit seinem Private Key die Finder-Nachricht entschlüsseln und erhält den Finder Public Key.
- Die Antwort wird vom Owner mit dem Finder Public Key verschlüsselt.
- Das Backend relayt auch diese Rückantwort – nur der Finder kann sie lesen.
- Der Finder bleibt pseudonym; Owners wissen nicht voneinander, können nicht erkennen, wer/wann/ob geantwortet wurde.

### 4. Multi-Owner- und Datenschutz-Aspekte

- Der Finder erfährt auf technischer Ebene nie, wie viele oder wer die Owner eines Tags sind.
- Jeder Owner operiert isoliert; Antworten und Aktionen einzelner Owners bleiben privat (keine Outbox/Lesestatus/Reply-Logs zugänglich für andere Owners).
- Das Backend kann keinen Bezug zwischen Nachrichten, Owners oder Findern herstellen.

---

## Vorteile

- **Maximale Privatsphäre:** Keine personenbezogenen Daten oder Metadaten für Backend, Finder oder andere Owners sichtbar.
- **Ende-zu-Ende-Sicherheit:** Sämtliche kryptografischen Schlüssel verbleiben immer auf Nutzergeräten; Recovery ist nur für Besitzer mit Backup oder „Share Ownership“-Links möglich.
- **Skalierbare Gruppen-Nutzung:** Auch bei Clubs, Teams, Familien möglich; Sharing per verschlüsseltem Backup-Link über Web Share API.

---

## Kurztechnisches Beispiel (Pseudo-Code)

´´´
Owner claimt Tag
tag_keypair = generate_keypair()
enc_tag_private = encrypt(tag_keypair.private, owner_public_key)
save_to_backend(tag_public_key, enc_tag_private)

Finder scannt Tag und sendet Nachricht
finder_keypair = generate_keypair()
session_key = generate_symmetric_key()
enc_message = encrypt_aes(message, session_key)
enc_session_keys = [encrypt(session_key, owner_pk) for owner_pk in all_owner_pks]
payload = {
"msg": enc_message,
"session_keys": enc_session_keys,
"finder_pubkey": finder_keypair.public
}
save_to_backend(payload)

Owner liest, antwortet
enc_session_key = find_my_session_key(payload.session_keys)
session_key = decrypt(enc_session_key, owner_private_key)
msg = decrypt_aes(payload.msg, session_key)
answer = encrypt(reply, payload.finder_pubkey)
save_to_backend(answer)

´´´

---

**Hinweise:**  
Werden Browser oder Keys gelöscht, ist der Zugriff verloren. Backup-Option oder Sharing ist sinnvoll für realistische Nutzbarkeit!
