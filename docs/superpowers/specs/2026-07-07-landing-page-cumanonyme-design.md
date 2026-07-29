# Landing page — Cum'Anonyme (édition CUMA)

> Date : 2026-07-07 · Source de contenu : `docs/DOCUMENTATION.md` (Anonymator v0.4.x)
> Livrable : une page web autonome présentant l'outil et permettant son téléchargement.

## 1. Objectif

Produire **une page d'atterrissage (landing page) unique** présentant l'outil
d'anonymisation dans son **édition CUMA (« Cum'Anonyme »)** et proposant son
**téléchargement**. La page suit la trame « landing page idéale » fournie par le
commanditaire et respecte la **charte graphique CUMA**.

## 2. Contraintes fermes

- **Édition CUMA uniquement.** Aucune mention de l'édition CAP, aucun sélecteur de
  thème, aucune version « dev ». Nom de produit affiché : **Cum'Anonyme**.
- **Un seul fichier autonome** : `html/index.html`. CSS **inline** (balise `<style>`),
  logos **embarqués en base64**. Aucune dépendance locale à charger (hors polices
  Google Fonts via CDN). La page s'ouvre et s'affiche sans serveur.
- **Hébergement web** : la page est destinée à être déposée sur un hébergement. Le
  **bouton de téléchargement pointe en relatif** vers `./CumAnonyme-v0.4.1.zip`
  (le zip est déposé à côté du HTML). Rappel visuel « Windows · ~280 Mo ».
- **Langue** : français.
- **Emplacement de sortie** : `C:\_pCloud\Extensions\anonymise\html\index.html`.

## 3. Charte graphique (CUMA)

Couleurs (issues de la charte jointe + `anonymator/ui/theme.py`, thème `cuma`) :

| Rôle | Hex |
|------|-----|
| Vert principal (identité) | `#31B700` |
| Vert action / CTA | `#00965E` |
| Vert foncé (footer, aplats) | `#063b27` |
| Orange accent (soulignés, puces) | `#FF8200` (hover `#C9500F`) |
| Bleu clair secondaire | `#B1DCE2` |
| Vert clair secondaire | `#93C90E` |
| Fond | `#FFFFFF` |
| Fond section alternée | `#F3FAF4` |
| Texte | `#10331F` · Texte atténué `#6B7C72` |
| Bordure | `#E2E8E4` |

Typographie : **Space Grotesk** (titres) + **Inter** (corps), via Google Fonts.

Logos embarqués (base64, source `anonymator/ui/assets/`) :
- `logo.png` — logo officiel **CUMA** (vert, « La puissance du groupe »), header + footer.
- `picto.png` — picto applicatif **« A »** (bleu marine/orange), comme icône produit.

## 4. Style visuel

- **Hero épuré** : fond **blanc**, grand titre, sous-titre, CTA, badges de réassurance.
  Pas de hero sombre.
- Sections alternées blanc / `#F3FAF4`. Cartes à coins arrondis (`border-radius:10px`),
  bordure `#E2E8E4`, ombre douce. Accents orange sur les puces/soulignés de titres.
- Responsive : lisible mobile (grilles qui repassent en colonne < 760px).
- Boutons CTA : aplat vert action `#00965E`, hover vert `#31B700`.

## 5. Structure de la page (mapping trame « landing idéale »)

1. **Header** (sticky léger) : logo CUMA à gauche, nom « Cum'Anonyme », lien ancre
   « Télécharger » à droite.
2. **Hero — proposition de valeur + CTA** : titre « Anonymisez vos données **sans
   qu'elles quittent votre poste** », sous-titre RGPD, **bouton Télécharger**
   (`⬇ Télécharger CumAnonyme · Windows`, **sans numéro de version affiché** ; cible
   relative `./CumAnonyme-v0.4.1.zip`), badges « 100 % local · Sans
   installation · Logiciel libre (AGPL) ».
3. **Le Why — bénéfices / problèmes réglés** : 3 cartes — le geste invisible (coller
   un fichier réel dans une IA en ligne = export de données), le risque RGPD
   (sanctions jusqu'à 4 % du CA, perte de confiance, fuites), la réponse : rien ne
   sort du poste.
4. **How — la méthode / les étapes** : frise 4 étapes — Télécharger → Dézipper →
   Lancer `cumanonyme.exe` → (au 1er lancement seulement) activer le modèle IA
   optionnel. Mention « aucun droit administrateur ».
5. **Fonctionnalités — les modules** : 6 cartes — Texte, Fichier
   (`.txt/.csv/.xlsx/.docx/.pptx`, mise en forme préservée), PDF (caviardage réel),
   Règles métier, Paramètres, Rapport d'audit.
6. **Comment ça détecte — double moteur** : bloc 2 colonnes — détection par règles +
   clés de contrôle (IBAN mod 97, NIR, SIREN/SIRET Luhn…) / détection IA **GLiNER**,
   modèle **souverain français**, zero-shot, tourne sur un simple CPU.
7. **Preuves / réassurance** : bandeau des briques technologiques et de confiance —
   AGPL-3.0 (code auditable), GLiNER 🇫🇷 (Apache-2.0), PyMuPDF, Qt ; « hors ligne
   après l'initialisation ».
8. **What — récapitulatif de l'offre** : tableau des 8 bénéfices repris du §3.6 de la
   documentation (100 % local, double moteur, IA souveraine, multi-formats, caviardage
   PDF réel, règles métier, sans abonnement, logiciel libre).
9. **Mini-FAQ** (remplace le point « FAQ » de la trame) : 3–4 Q/R —
   « Où vont mes données ? » (nulle part), « Faut-il une connexion Internet ? »
   (seulement au 1er téléchargement du modèle), « Est-ce que ça remplace un DPO /
   la conformité RGPD ? » (non, c'est un outil de minimisation), « Sur quels systèmes
   ça tourne ? » (Windows, exécutable autonome).
10. **CTA final** : rappel du bouton Télécharger + « Windows · ~280 Mo · gratuit » +
    lien vers le code source GitHub (`https://github.com/gudr-perso/Anonymator`).
11. **Footer** : logo CUMA, version, licence AGPL-3.0, lien dépôt, mention « Édition
    Réseau CUMA ».

**Sections volontairement écartées de la trame générique** : prix (point 6) et
garanties (point 7) — l'outil est **gratuit et libre**, aucun prix inventé.

## 6. Contenu — source

Tout le texte provient de `docs/DOCUMENTATION.md` (parties 2 fonctionnelle et 3
argumentaire) et est reformulé pour le web (phrases courtes, orientées bénéfice).
Aucune donnée chiffrée inventée ; la taille ~280 Mo correspond au zip réel
(`dist/CumAnonyme-v0.4.1.zip`), le modèle IA ~300 Mo est cité tel quel dans la doc.

## 7. Critères de réussite

- [ ] Le fichier `html/index.html` s'ouvre seul dans un navigateur, sans erreur console,
      sans requête réseau bloquante (hors Google Fonts).
- [ ] Le bouton Télécharger cible `./CumAnonyme-v0.4.1.zip` (relatif).
- [ ] Aucune occurrence de « CAP », « CAP'nonyme » ou du thème bleu dans la page.
- [ ] Charte CUMA respectée (couleurs, logo officiel, polices).
- [ ] Les 11 sections ci-dessus sont présentes, dans l'ordre.
- [ ] Rendu correct desktop et mobile (une largeur ~375px reste lisible).
- [ ] Logos affichés (base64 valides).
