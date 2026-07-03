# Refonte du thème CAP d'après le thème CUMA

*Date : 2026-07-02*

## Contexte et problème

Lors de la refonte du style du logiciel, le thème **CAP (bleu)** a hérité d'une
grande partie du rendu du thème **CUMA (vert)**. En pratique, quand on
sélectionne CAP, les boutons deviennent bleus mais le héros de l'accueil, le
quadrillage, les interrupteurs on/off et les icônes peintes restent **verts**.

### Cause racine

Le style vit dans **deux couches**, dont une seule est réellement pilotée par le
thème :

1. **Couche QSS** (`anonymator/ui/theme.py`) — pilotée par thème. Le jeu de
   tokens `cap` existe déjà en bleu ; boutons, onglets, cartes se colorent
   correctement.
2. **Couche peinte / icônes** — code des couleurs **en dur** en vert CUMA,
   indépendamment du thème sélectionné :
   - `home_screen.py` : fond héros `#E8F3EA`, quadrillage `#E1EBE3`, texte logo
     `#31B700`, texte grisé, carte d'invitation modèle en vert.
   - `components/grid.py` : quadrillage (`GRID_BG`/`GRID_LINE`) des écrans
     Texte / Fichier / PDF.
   - `components/toggle.py` : interrupteur on/off `#00965E`.
   - Icônes dans `cards.py`, `header.py`, `nav_band.py`, `about_screen.py`,
     `file_screen.py`, `pdf_screen.py`, `text_screen.py`, badges — toutes en
     `#00965E` / `#31B700` / `#E8621A`.

## Objectif

Refaire le thème CAP en bleu, fidèlement calqué sur la **structure** de CUMA.

**Contrainte absolue : ne jamais modifier le rendu du thème CUMA.** Toute valeur
CUMA (existante ou nouvellement introduite comme token) doit être figée sur le
rendu actuel, de sorte que CUMA reste identique au pixel près.

## Principe de la solution

Rendre la **couche peinte / icônes pilotée par le thème actif**, avec les
valeurs CUMA figées sur les couleurs d'aujourd'hui.

Mécanisme :

- `theme.py` expose un **thème actif** : `set_active_theme(name)`,
  `active_theme()`, `tokens(name=None)`, `color(role, name=None)`.
- `main_window._apply_theme()` appelle `set_active_theme(self.prefs.theme)`
  **avant** d'appliquer le QSS.
- Les widgets **peints** (héros, quadrillage, toggle) lisent les tokens au
  moment du `paintEvent` → recolorés automatiquement au prochain repaint.
- Les **icônes** (pixmaps posés à la construction) sont recolorées à la
  (re)construction des écrans.
- Le changement de thème dans les Paramètres **reconstruit la pile d'écrans**
  pour tout recolorer. Le thème se change rarement ; ce compromis est accepté
  (une saisie/fichier en cours serait réinitialisé au changement de thème).

## Décisions de conception (validées)

1. **Héros de l'accueil en CAP = panneau navy foncé** : fond `#0a1556`
   (cap-navy-lift), titre et sous-titre en **blanc**, **logo CAP** à la place du
   logo CUMA. Colle au `--grad-hero` de la charte.
2. **Quadrillage navy partout** : accueil **et** écrans Texte, Fichier, PDF
   (qui partagent aujourd'hui le même quadrillage vert).
3. **Boutons `primary` en cyan** (cohérent avec CUMA où `primary` = couleur
   `action`). L'orange reste réservé aux CTA `accent` (bouton Accueil, badges,
   cartes stats).
4. **Logo** : `cap-logo-trans.png` (cyan + orange, contour hexagone cyan) —
   ressort bien sur navy foncé, pas besoin d'une variante blanche.

## Charte CAP (pièce jointe de référence)

| Nom | Hex |
|---|---|
| `--cap-navy` | `#050c3f` |
| `--cap-navy-lift` | `#0a1556` |
| `--cap-navy-deep` | `#030826` |
| `--cap-orange` | `#f36100` |
| `--cap-orange-bright` | `#ff7a1f` |
| `--cap-cyan` | `#138fdb` |
| `--cap-cyan-light` | `#2aa6e8` |

## Jeu de tokens CAP (CUMA laissé intact)

| Token | CUMA (référence, inchangé) | CAP |
|---|---|---|
| `action` (onglets, pastilles, liens, btn primary) | `#00965E` | `#138fdb` cap-cyan |
| `primary` (survol vif) | `#31B700` | `#2aa6e8` cap-cyan-light |
| `dark` (btn ouvrir / onglet verrouillé) | `#063b27` | `#050c3f` cap-navy |
| `accent` / `accent_hover` (CTA orange) | `#E8621A` / `#C9500F` | `#f36100` / `#d15400` |
| `bg` | `#FFFFFF` | `#FFFFFF` |
| `text` | `#10331F` | `#050c3f` |
| `surface` | `#FFFFFF` | `#FFFFFF` |
| `surface_alt` | `#F3FAF4` | `#EEF5FB` |
| `border` | `#E2E8E4` | `#DCE6F0` |
| `text_muted` | `#6B7C72` | `#64748B` |
| `info` / `info_hover` | `#4FA8D8` / `#3D93C2` | `#2aa6e8` / `#138fdb` |

## Tokens nouveaux (ajoutés aux deux thèmes)

Ces tokens portent, côté CUMA, exactement les valeurs codées en dur
aujourd'hui, pour garantir un rendu CUMA identique.

| Token | CUMA | CAP |
|---|---|---|
| `grid_bg` (fond héros + fonds Texte/Fichier/PDF) | `#E8F3EA` | `#0a1556` cap-navy-lift |
| `grid_line` (quadrillage) | `#E1EBE3` | `#1e2a63` (navy éclairci) |
| `hero_text` | `#10331F` | `#FFFFFF` |
| `hero_muted` | `#6B7C72` | `rgba(255,255,255,0.82)` |
| `toggle_off` | `#C7D2CC` | `#C3CCE0` |
| `logo` (nom de fichier dans assets) | `logo.png` | `logo-cap.png` |
| `header_tag` (étiquette réseau du bandeau) | `RÉSEAU CUMA` | `""` (masquée) |

En CAP, `header_tag` vide masque l'étiquette « RÉSEAU CUMA » **et** son séparateur
`|` dans le bandeau d'en-tête (aujourd'hui codés en dur). CUMA reste inchangé.

## Fichiers touchés

- `anonymator/ui/theme.py` : jeu `cap` réécrit ; nouveaux tokens dans les deux
  thèmes ; accesseur de thème actif (`set_active_theme`, `active_theme`,
  `tokens`, `color`).
- `anonymator/ui/home_screen.py` : héros lit `grid_bg` / `grid_line` /
  `hero_text` / `hero_muted` / `logo` ; texte blanc sur navy en CAP ; logo CAP.
- `anonymator/ui/components/grid.py` : `paint_grid` lit `grid_bg` / `grid_line`
  du thème actif (défauts = valeurs CUMA → inchangé si appelé sans thème).
- `anonymator/ui/components/toggle.py` : `action` (on) / `toggle_off` (off).
- `anonymator/ui/components/cards.py`, `header.py`, `nav_band.py`,
  `about_screen.py`, `file_screen.py`, `pdf_screen.py`, `text_screen.py`,
  `components/rule_action_badge.py` : icônes / badges `#00965E` / `#31B700` /
  `#E8621A` → `action` / `primary` / `accent` du thème actif.
- `anonymator/ui/main_window.py` : `set_active_theme` avant le QSS +
  reconstruction de la pile d'écrans au changement de thème.
- `anonymator/ui/assets/logo-cap.png` : nouvelle copie de
  `C:\_pCloud\__CAP Consulting\logos\cap-logo-trans.png`.

## Tests et vérification

- **Garde-fou anti-régression CUMA** : test asserant que `tokens("cuma")`
  contient exactement les valeurs actuelles (y compris les nouveaux tokens
  figés sur les couleurs d'aujourd'hui).
- **Complétude** : test asserant que chaque token présent dans `cuma` est
  présent dans `cap` (aucune clé manquante), pour les deux thèmes.
- **Vérification manuelle** : lisibilité des textes **hors carte** posés
  directement sur le fond navy (écrans Texte / Fichier / PDF). Tout libellé /
  texte gris posé sur le fond devra être repassé en clair (`hero_text` /
  `hero_muted`) — à traiter au cas par cas au rendu.

## Hors périmètre

- Aucune modification du rendu du thème CUMA.
- Pas de refonte des couleurs d'entités (`anonymator/ui/colors.py`).
- Pas de nouveau système de thème (on garde le dict de tokens + QSS actuel).
