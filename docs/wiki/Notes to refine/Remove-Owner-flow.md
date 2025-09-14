# Owner-Entfernung und Key-Rotation (Privacy-First Flow)

Dieses Dokument beschreibt, wie im Lost & Found System ein Owner sicher entfernt wird und dadurch jeglichen Zugriff auf Tag-bezogene, verschlüsselte Daten verliert. Das Verfahren garantiert Privacy, Zero-Knowledge und verhindert „tote Briefkästen“ durch Ex-Owner.

---

## Ablaufbeschreibung

1. **Entfernungs-Trigger:**  
   Ein verbleibender Owner (O1) stößt per UI die Entfernung eines Owners (O2) für Tag T1 an.

2. **Neues Tag-Schlüsselpaar erzeugen:**  
   Im Frontend wird ein _neuer Tag Private/Public Key_ für T1 generiert.

3. **Migration der Tag-internen verschlüsselten Felder:**  
   Alle relevanten, nur für Owner verschlüsselten Felder (z. B. Notizen, Recovery-Hinweise) werden mit dem alten Tag Key entschlüsselt und **im Frontend mit dem neuen Public Key wieder verschlüsselt**.

4. **Keyblobs aktualisieren:**  
   Für jeden _verbleibenden_ Owner wird der neue Tag Private Key mit dessen Owner Public Key verschlüsselt und im Backend gespeichert.
   - **Der entfernte Owner bekommt keinen neuen Keyblob!**

5. **Backend speichert:**  
   - Neues Tag Public Key
   - Liste aller aktiven Owner & dazugehörige neue Keyblobs
   - Optional: Historie des Zugriffs-/Besitzerwechsels (pseudonym)

6. **Abschluss:**  
   Der entfernte Owner (O2) kann ab jetzt keinerlei verschlüsselte Felder oder Owner-Infos zu Tag T1 mehr lesen oder entschlüsseln.  
   Zugang zu alten Ciphertext-Feldern ist durch Re-Encryption ausgeschlossen.

---

## Flowchart (Mermaid)

´´´mermaid

    sequenceDiagram
        participant O1 as Owner 1 (verbleibend)
        participant O2 as Owner 2 (zu entfernen)
        participant FE as Frontend
        participant BE as Backend

        Note over O1,FE: O1 startet „Entferne O2 als Owner für Tag T1“
        O1->>FE: Entfernen-Trigger
        FE->>FE: Generiere neues Tag Keypair (T1_new)
        FE->>FE: Entschlüssle Owner-Felder mit altem Key, verschlüssele neu mit T1_new Public Key
        loop Für alle verbleibenden Owner
            FE->>FE: Verschlüssele neuen Tag Private Key mit Owner Public Key
            FE->>BE: Update Keyblob speichern
        end
        FE->>BE: Speichere neues Tag Public Key, alte Keyblobs löschen
        O2--xBE: Kein Zugriff mehr auf neue Owner Keyblobs oder Daten
        BE->>O1: Abschlussmeldung „Entfernung erfolgreich“

´´´


---

## Vorteile

- **Ex-Owner verliert Zugriff** auf alle Owner-bezogenen verschlüsselten Daten und künftige Operationen am Tag
- **Privacy: Zero-Knowledge** im Backend, keine Klartextschlüssel oder Persona-Daten
- **Kein „toter Briefkasten“ mehr:** Schlüsselwechsel sorgt für tatsächliche Rechteentziehung

---

**Hinweis:**  
Alle verbleibenden Owner müssen für die Migration der Daten/Keyblobs kurz online sein, da der Prozess die Verteilung und Re-Encryption clientseitig mit jedem ihrer Owner Public Keys durchführt.
