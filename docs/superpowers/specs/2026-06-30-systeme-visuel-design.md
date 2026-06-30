# Système visuel & restyle UI — Doc de conception

> Refonte visuelle de l'application (PySide6) d'après deux maquettes validées (accueil + écran texte).
> Les écrans fichier et paramètres sont adaptés « dans le même esprit ».
> Brainstorming du 2026-06-30. Complète [2026-06-29-anonymator-design.md](2026-06-29-anonymator-design.md) §8
> et s'articule avec [2026-06-30-revue-fichier-coloree-design.md](2026-06-30-revue-fichier-coloree-design.md).

---

## 1. Décisions verrouillées

1. **Barre de titre : native + bandeau d'en-tête.** On garde la barre Windows native ; la marque
   (logo + « Anonymator » + « RÉSEAU CUMA ») vit dans un **bandeau d'en-tête** sous la barre native.
   Le mode *frameless* (barre entièrement re-codée) est reporté.
2. **Approximation assumée du surlignage** : dans le texte, les entités sont rendues par **fond
   teinté + soulignement coloré** (`QTextEdit`), pas par de vraies pastilles arrondies (non natif).
   Les badges, toggles, pills du résultat et le panneau latéral, eux, sont fidèles.
3. **Palette CUMA** (verts + accent orange) comme défaut ; le basculement CAP/CUMA existant
   (`theme.py`) est conservé.

---

## 2. Formats & libellés (corrections vs maquette)

- La maquette d'accueil indique « .txt, .docx ou .pdf ». Les **formats réellement supportés** sont
  **.txt, .csv, .xlsx**. Le libellé de la carte « Importer un fichier » affichera donc
  **« .txt, .csv ou .xlsx »**. (PDF hors périmètre ; .docx non géré en v1.)
- Libellés d'accueil retenus (maquette) : **« Coller du texte »**, **« Importer un fichier »**,
  **« Paramètres »** — avec sous-titres « Analyser et masquer un texte collé », « .txt, .csv ou .xlsx »,
  « Règles de détection & masquage ».

---

## 3. Palette & tokens (extension de `theme.py`)

On enrichit les tokens existants (`primary`, `action`, `dark`, `accent`, `bg`, `text`) pour couvrir
les surfaces du nouveau design (sans casser le swap CAP/CUMA) :

| Token | CUMA (défaut) | Rôle |
| --- | --- | --- |
| `bg` | `#FFFFFF` | fond des panneaux droits / contenu |
| `bg_hero` | `#E8F3EA` (vert pâle quadrillé) | panneau gauche d'accueil |
| `surface` | `#FFFFFF` | cartes |
| `surface_alt` | `#F3FAF4` | cartes stat / hover |
| `border` | `#E2E8E4` | bordures de cartes (1px) |
| `primary` | `#31B700` | vert principal |
| `action` | `#00965E` | boutons primaires, accents verts |
| `accent` | `#E8621A` | orange (« la puissance du **groupe** », alertes) |
| `text` | `#10331F` | texte principal |
| `text_muted` | `#6B7C72` | sous-titres, libellés |
| `radius` | `10px` | rayon des cartes/boutons |

Les couleurs **fonctionnelles par typologie** (NOM/ADRESSE/IBAN…) restent le jeu fixe de
[`colors.py`](../../../anonymator/ui/colors.py), indépendant du thème.

Typo : titres **Space Grotesk** (déjà prévu), texte **Inter** ; fallback `Segoe UI`.

---

## 4. Bibliothèque de composants réutilisables

Nouveau paquet `anonymator/ui/components/` — widgets autonomes, testables par smoke-tests.

- **`HeaderBand`** : bandeau d'en-tête (logo CUMA + « Anonymator » + « RÉSEAU CUMA » à gauche).
  Affiché en haut de chaque écran sous la barre native.
- **`NavCard`** (accueil) : carte cliquable = icône (pastille verte) + titre + sous-titre + chevron `→`,
  effet de survol. Signal `clicked`.
- **`StatCard`** : icône + grand nombre + libellé + couleur d'accent (vert / orange / rouge selon le
  type). Méthode `set_value(n)`.
- **`ToggleSwitch`** : interrupteur on/off stylé (vert) — widget custom dérivé de `QAbstractButton`,
  `checkable`, signal `toggled`. Remplace les `QCheckBox` dans les listes d'entités.
- **`CategoryBadge`** : petite étiquette arrondie colorée (point + libellé de typologie), couleur via
  `colors.color_for(type)`.
- **`Card`** : conteneur titré (icône + titre en capitales + corps), bordure `border`, rayon `radius`.
- **Boutons** (par QSS + `objectName`) : `primary` (vert plein, icône), `secondary` (contour),
  `ghost` (transparent). Barre d'action en bas d'écran.
- **Surlignage d'entité** (`QTextEdit`) : `QTextCharFormat` fond teinté (alpha) + `setUnderlineColor`
  de la couleur du type. Helper partagé `highlight_format(type)`.
- **Pills de résultat** : libellés discrets `(NOM)`, `(ADRESSE)`… stylés (fond teinté, texte coloré) —
  rendus comme texte enrichi dans le `QTextEdit` résultat (pas de bordure arrondie inline).

Icônes : jeu **SVG** minimal dans `anonymator/ui/assets/icons/` (document, dossier, réglages, accueil,
texte, bouclier, calques, œil, œil-barré, alerte, copier, télécharger, analyser, chevron). Chargées
via `QIcon`. Style trait fin, monochrome teintable.

---

## 5. Indicateur « Niveau de risque »

Nouveau calcul (non-Qt, testable) `risk_level(entities, ref) -> "Faible"|"Moyen"|"Élevé"` à partir
de la **sensibilité** déclarée au référentiel (`sensitivity`) des entités **retenues** :
- **Élevé** : au moins une entité retenue de sensibilité **Haute**.
- **Moyen** : sinon, au moins une **Moyenne**.
- **Faible** : aucune (ou que des **Basse**).

La `StatCard` « Niveau de risque » colore son accent : Élevé→rouge, Moyen→orange, Faible→vert.

---

## 6. Application par écran

**Accueil** : panneau gauche `bg_hero` (fond quadrillé léger via tuile SVG) avec logo, titre
« Anonymisez. Partagez l'essentiel. », sous-titre, « la puissance du **groupe** » (groupe en orange) ;
panneau droit blanc « PAR OÙ COMMENCER ? » + 3 `NavCard` (Coller du texte / Importer un fichier /
Paramètres).

**Texte** : `HeaderBand` + fil d'Ariane (Accueil | Texte) + badge « N entités · N masquées » ; rangée
de 5 `StatCard` (Entités détectées / Catégories / À masquer / Conservées / Niveau de risque) ; colonne
gauche = `Card` « Texte à anonymiser » (surlignage) + `Card` « Résultat anonymisé » (pills) ; colonne
droite = `Card` « Entités détectées N/N » avec liste `CategoryBadge` + valeur + `ToggleSwitch` ; barre
d'action basse (Appliquer le masquage / Analyser / Copier / Exporter .txt).

**Fichier (revue)** : même coquille (HeaderBand, fil d'Ariane Accueil | Fichier, rangée de StatCard) ;
zone centrale = tableau paginé (P-C) ; panneau droit = typologies/valeurs avec `ToggleSwitch` et
`CategoryBadge` ; barre d'action basse (Analyser et revoir / Appliquer et enregistrer / Exporter le
rapport). La pagination reste comme spécifié dans le spec revue fichier.

**Paramètres** : même coquille ; titre « Règles de détection & masquage » ; section thème ; dossier de
sortie ; **types d'entités** (liste avec `ToggleSwitch` par type — active BIC/CP/URL) ; **liste
d'exclusion** (éditeur ajout/suppression). Composants partagés avec les autres écrans.

---

## 7. Architecture & impact

- **`theme.py`** : étendre les tokens + un `_TEMPLATE` QSS nettement plus riche (cartes, en-tête,
  stat, badges, boutons, scrollbars). Garder `build_qss(theme)` et le swap CAP/CUMA.
- **`anonymator/ui/components/`** (nouveau) : un fichier par composant, chacun testable isolément.
- **`anonymator/ui/assets/icons/`** (nouveau) : SVG + un petit helper `icon(name)`.
- **`anonymator/core/risk.py`** (nouveau, non-Qt) : `risk_level(...)`.
- **Restyle** des écrans existants : `home_screen.py`, `text_screen.py`, `settings_screen.py`
  (structure inchangée, on remplace les widgets bruts par les composants + objectName QSS).
- **`file_screen.py`** : construit directement dans le nouveau style lors de P-C (revu).
- Les `MainWindow`/navigation et toute la logique non-Qt (sessions, détection) sont **inchangées** :
  c'est une couche de présentation.

---

## 8. Tests

- Smoke `pytest-qt` par composant (`ToggleSwitch.toggled`, `NavCard.clicked`, `StatCard.set_value`,
  `CategoryBadge` couleur).
- `test_risk.py` (non-Qt) : Élevé/Moyen/Faible selon sensibilités.
- `test_theme.py` étendu : les nouveaux tokens existent pour chaque thème ; `build_qss` les injecte.
- Smoke écrans restylés : construction OK, présence des composants clés.

---

## 9. Hors périmètre / reporté

- Barre de titre frameless (logo intégré + boutons re-codés).
- Pastilles arrondies inline « parfaites » dans le texte (approximation assumée, §1.2).
- Animations/transitions soignées (au-delà du survol simple).
- Le contenu fonctionnel (détection, sessions, pagination) est déjà couvert par P-A/P-B/P-C — ce spec
  ne change que la présentation.

---

## 10. Plans d'exécution induits (à écrire ensuite)

- **Plan V1 — Fondations** : tokens/QSS étendus + `components/` (HeaderBand, NavCard, StatCard,
  ToggleSwitch, CategoryBadge, Card, boutons) + icônes + `risk.py`.
- **Plan V2 — Restyle écrans existants** : accueil, texte, paramètres (avec toggles types + éditeur
  stoplist) au-dessus des composants.
- **P-C (révisé)** : écran fichier de revue bâti directement avec les composants V1.
