# Multi-Owner Share Tag Prozess (Privacy-First, PIN-basiert)

## Übersicht

Der folgende Ablauf ermöglicht das **datensparsame, vertrauenslose Freigeben von Tags an neue(n) Owner** mittels temporärem Share-Link und PIN („Bluetooth-Pairing“-Prinzip). Keine personenbezogenen Daten werden preisgegeben.

---

## Ablaufbeschreibung

1. **O1 (bestehender Owner) wählt Tag(s) im Frontend aus und startet den Freigabeprozess ("Share Tag(s)").**
2. Das Backend generiert für diesen Prozess:
    - eine **kurze, lesbare Prozess-ID** (z.B. „AB42C1“)
    - einen **temporären, einmal nutzbaren Share-Link** (z.B. `https://lostfound.app/share-tag?request=AB42C1`)
    - (optional) eine Ablaufzeit/TTL
3. **O1 überträgt den Share-Link an O2 (neuer Owner)** – persönlich, per Messenger, QR, etc.
4. **O2**, während im System angemeldet, öffnet den Share-Link und erhält die Aufforderung, 
    - einen automatisch generierten **PIN-Code** (z.B. „824137“) zu übernehmen/zu merken **ODER** selbst einen temporären Namen zu wählen,
    - den PIN-Code an O1 weiterzugeben (offline, Chat, verbal).
5. **Das Backend speichert**: Prozess-ID, gewünschten Tag/Tags, neuen Owner (O2), PIN-Code (nur für temporäre Abgleich-Zwecke).
6. **O1 erhält im Frontend einen Hinweis auf eingegangene Freigabeanfrage** (mit Prozess-ID), und sieht einen Dialog:  
   „Bitte geben Sie den vom neuen Co-Owner genannten PIN-Code für Freigabe AB42C1 ein.“
7. **O1 gibt den Code ein.** Nur bei Korrektheit wird im Frontend:
    - der Tag Private Key (je Tag) entschlüsselt,
    - mit dem Public Key von O2 verschlüsselt,
    - und ans Backend zur Speicherung als „Keyblob“ für O2 übergeben.
8. **O2 erhält Zugriff und kann den Tag ab jetzt mitentschlüsseln.**
    - Prozessdaten und PIN werden nach Freigabe gelöscht.
    - O1 und O2 bleiben pseudonym.
    - Prozess kann ggf. für mehrere Tags oder durch Wiederholung für mehrere Nutzer genutzt werden.

---

## Flow-Chart mit Mermaid (Vereinfachte Version)

´´´ mermaid
    sequenceDiagram
        participant O1 as Owner 1 (Bestehender Owner)
        participant BE as Backend
        participant O2 as Owner 2 (Neuer Owner)
    
    O1->>BE: Startet Freigabe für Tag(s)
    BE->>O1: Sendet Share-Link + Prozess-ID (AB42C1)
    O1-->>O2: Überträgt Share-Link (offline/Chat/Messenger)
    O2->>BE: Öffnet Share-Link und authentifiziert sich
    BE->>O2: Zeigt PIN-Code (824137)
    O2-->>O1: Überträgt PIN-Code (offline/chat/verbal)
    O1->>BE: Bestätigt Freigabeprozess, gibt Prozess-ID und PIN-Code ein
    BE->>O1: Gibt Public Key von O2 heraus (für lokale Verschlüsselung)
    O1->>O1: Verschlüsselt Tag-Private-Key mit O2's Public Key
    O1->>BE: Überträgt verschlüsselten Keyblob für O2
    BE->>O2: Benachrichtigt, dass Freigabe erfolgt ist
´´´

---

## Vorteile

- Kein Klartext-Tag Private Key oder personenbezogene Daten auf Server
- Zwang zur echten „Handshaking“-Bestätigung (Offline-Code)
- Pro Prozess-ID/PIN beliebige Tags, je Prozess nur ein Owner (empfohlen für Privacy)
- UX-bekanntes, menschlich prüfbares Sicherheitsprinzip


