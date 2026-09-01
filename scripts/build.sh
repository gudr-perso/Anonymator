#!/usr/bin/env bash
# scripts/build.sh
# Build + zip d'une (ou des) marque(s) Anonymator sur macOS.
#   ./scripts/build.sh cap | cuma | dev | all
#
# Pendant macOS de scripts/build.ps1. Deux differences de fond avec Windows :
#   - PyInstaller produit un .app (bloc BUNDLE du .spec) en plus du dossier
#     COLLECT ; c'est le .app qu'on distribue, le dossier nu est ignore.
#   - on archive avec `ditto` et non `zip` : le .app contient des liens
#     symboliques (frameworks Qt) et une signature ad-hoc que `zip` casse.
set -euo pipefail

brand="${1:-}"
case "$brand" in
    cap|cuma|dev|all) ;;
    *) echo "Usage: $0 {cap|cuma|dev|all}" >&2; exit 2 ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

# Interpreteur : .venv local s'il existe, sinon le python de l'environnement
# (cas de la CI, ou setup-python fournit deja un env isole).
if [[ -x ".venv/bin/python" ]]; then python=".venv/bin/python"; else python="$(command -v python3)"; fi

# Version lue depuis anonymator/__init__.py (source de verite unique).
version="$("$python" -c 'import anonymator; print(anonymator.__version__)')"
# Taille du telechargement du modele : derivee du code (source de verite unique),
# jamais recopiee en dur — cf. anonymator/core/model_status.py.
model_size="$("$python" -c 'from anonymator.core.model_status import MODEL_DOWNLOAD_SIZE; print(MODEL_DOWNLOAD_SIZE)')"
arch="$(uname -m)"

# Noms lus dans anonymator/brand.py plutot que recopies ici : la table BRANDS
# est la source de verite unique. Renvoie « exe_name<TAB>product_name ».
brand_names() {
    "$python" -c "
from anonymator.brand import BRANDS, DEV_BRAND
b = BRANDS.get('$1', DEV_BRAND)
print(b.exe_name + '	' + b.product_name)
"
}

# Notice de premier lancement, placee a la racine de l'archive. Le .app n'etant
# pas signe aupres d'Apple, Gatekeeper le bloque des lors qu'il a ete transfere
# (pCloud, mail, telechargement) avec un message trompeur. La destinataire n'est
# pas developpeuse : la procedure doit voyager AVEC l'app, pas dans docs/.
write_readme() {
    local exe="$1" product="$2" dest="$3"
    local title="$product pour macOS"
    cat > "$dest" <<EOF
$title
$(printf '=%.0s' $(seq 1 ${#title}))

PREMIER LANCEMENT — a faire une seule fois
-------------------------------------------

macOS affichera peut-etre, au premier double-clic :

    « $exe est endommage et ne peut pas etre ouvert.
      Vous devriez le placer dans la corbeille. »

Ce message est trompeur : l'application n'est pas endommagee. macOS bloque par
defaut toute application qui n'a pas ete enregistree aupres d'Apple (un
abonnement payant que ce projet n'a pas souscrit).

Pour l'autoriser :

  1. Glissez $exe.app dans votre dossier Applications.

  2. Ouvrez le Terminal
     (Applications > Utilitaires > Terminal, ou Cmd+Espace puis « Terminal »).

  3. Copiez-collez EXACTEMENT cette ligne, puis appuyez sur Entree :

         xattr -dr com.apple.quarantine /Applications/$exe.app

     (rien ne s'affiche : c'est normal, cela signifie que tout s'est bien passe)

  4. Lancez l'application normalement. Les lancements suivants sont directs.

Si le Terminal vous intimide, l'alternative sans ligne de commande :
faites un clic droit sur l'app > Ouvrir, puis confirmez. Sur les versions
recentes de macOS, passez plutot par Reglages Systeme > Confidentialite et
securite : un bouton « Ouvrir quand meme » y apparait apres une tentative
de lancement bloquee.

PREREQUIS
---------
- Mac a puce Apple (M1 ou plus recent). Les Mac Intel ne sont pas supportes.
- macOS 11 (Big Sur) minimum.

PREMIERE UTILISATION
--------------------
L'application telecharge un modele d'analyse ($model_size) a sa premiere
ouverture. Prevoyez une connexion internet confortable pour cette etape
uniquement : ensuite, toute l'anonymisation se fait en local, aucune donnee ne
quitte votre machine.

LICENCE
-------
AGPL-3.0-or-later — voir le fichier LICENSE.
Code source : https://github.com/gudr-perso/Anonymator
EOF
}

# L'icone .icns n'est pas versionnee : on la regenere avant tout build.
./scripts/make_icns.sh

if [[ "$brand" == "all" ]]; then targets=( cap cuma ); else targets=( "$brand" ); fi

for b in "${targets[@]}"; do
    echo "== Build $b (v$version, macOS $arch) =="
    IFS=$'	' read -r exe product < <(brand_names "$b")
    ANONYMATOR_BUILD_BRAND="$b" "$python" -m PyInstaller --noconfirm anonymator.spec

    app="dist/$exe.app"
    [[ -d "$app" ]] || { echo "Bundle absent : $app" >&2; exit 1; }

    # Nom d'archive : nom de produit sans apostrophe (CAP'nonyme -> CAPnonyme),
    # aligne sur la convention de scripts/build.ps1. Pas de livrable en dev.
    if [[ "$b" == "dev" ]]; then
        echo "Marque dev : pas d'archive de diffusion."
        continue
    fi
    apos="'"
    stem="${product//$apos/}-v$version-macOS-$arch"

    # Dossier de diffusion : le .app, plus le LICENSE et les exemples A COTE
    # du bundle. Rien n'est ajoute *dans* le .app : toute modification
    # posterieure au build invaliderait sa signature (ad-hoc ou Developer ID).
    stage="dist/$stem"
    rm -rf "$stage"; mkdir -p "$stage"
    ditto "$app" "$stage/$exe.app"          # ditto preserve symlinks + signature
    cp LICENSE "$stage/LICENSE"             # AGPL visible a la racine, cf. docs/RELEASE.md
    write_readme "$exe" "$product" "$stage/LISEZ-MOI.txt"
    if [[ -d exemples ]]; then cp -R exemples "$stage/exemples"; fi

    zip_path="dist/$stem.zip"
    rm -f "$zip_path"
    ditto -c -k --sequesterRsrc --keepParent "$stage" "$zip_path"
    echo "Zip cree : $zip_path"
done
echo "Termine."
