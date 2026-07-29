from anonymator.files.columns import (
    SKIP, TEXT, TYPED,
    looks_structured, default_maskable_columns, classify_columns,
    normalize_header, header_type, dominant_full_match_type,
    is_column_name, looks_like_header_row,
)


def test_looks_structured_true_for_numbers_dates_empty():
    assert looks_structured("       1284")
    assert looks_structured("15866,00")
    assert looks_structured("20230101")
    assert looks_structured("")
    assert looks_structured("51211000")


def test_looks_structured_false_when_has_letter():
    assert not looks_structured("Banque Crédit Agricole")
    assert not looks_structured("A.N. au 01/01/2023")


def test_default_maskable_columns_skips_header_and_numeric_cols():
    rows = [
        ["CompteNum", "CompteLib", "Debit"],
        ["10131000", "CS appelé", "0,00"],
        ["51211000", "Banque CRCA", "9702,88"],
    ]
    cols = default_maskable_columns(rows, has_header=True)
    assert cols == {1}


def test_default_maskable_columns_without_header():
    rows = [["10121000", "CS appelé", "20,00"], ["16423000", "", "2173,39"]]
    assert default_maskable_columns(rows, has_header=False) == {1}


# --- normalisation des en-têtes -------------------------------------------

def test_normalize_header_strips_accents_separators_and_camel_case():
    assert normalize_header("Raison_Sociale") == "raison sociale"
    assert normalize_header("CompteNum") == "compte num"
    assert normalize_header("N° Téléphone") == "n telephone"
    assert normalize_header("﻿code_client") == "code client"


# --- typage par en-tête ----------------------------------------------------

def test_header_type_recognises_usual_columns():
    assert header_type("contact_nom") == "PERSON"
    assert header_type("contact_prenom") == "PERSON"
    assert header_type("commercial") == "PERSON"
    assert header_type("raison_sociale") == "ORG"
    assert header_type("NomSociete") == "ORG"
    assert header_type("email") == "EMAIL"
    assert header_type("telephone") == "PHONE"
    assert header_type("ville") == "ADDRESS"
    assert header_type("adresse de livraison") == "ADDRESS"
    assert header_type("code_postal") == "POSTAL_CODE"
    assert header_type("N° SIRET") == "SIRET"
    assert header_type("numero_secu") == "NIR"


def test_header_type_ignores_identifier_columns():
    """Un code client est une clé de jointure, pas une identité : on ne
    le type pas d'office sur le mot « client »."""
    assert header_type("code_client") is None
    assert header_type("id_societe") is None
    assert header_type("CompteNum") is None
    assert header_type("reference_dossier") is None


def test_header_type_keeps_technical_types_over_identifier_guard():
    """« code postal » et « num tel » contiennent code/num mais restent typés."""
    assert header_type("code_postal") == "POSTAL_CODE"
    assert header_type("num_tel") == "PHONE"
    assert header_type("numero SIREN") == "SIREN"


def test_header_type_unknown_returns_none():
    assert header_type("secteur") is None
    assert header_type("statut") is None
    assert header_type("note") is None


# --- profilage des colonnes sans lettre ------------------------------------

def test_dominant_full_match_type_on_homogeneous_column():
    phones = ["03 73 41 92 92", "05 32 14 00 01", "01 51 64 22 10"]
    assert dominant_full_match_type(phones) == "PHONE"
    assert dominant_full_match_type(["69003", "44000", "31000"]) == "POSTAL_CODE"


def test_dominant_full_match_type_ignores_partial_matches():
    """Un montant contient bien 5 chiffres, mais la cellule entière n'est
    pas un code postal : aucune correspondance."""
    assert dominant_full_match_type(["15866,00", "9702,88", "0,00"]) is None
    assert dominant_full_match_type(["10131000", "51211000"]) is None
    assert dominant_full_match_type(["2019-11-10", "2026-05-17"]) is None


def test_dominant_full_match_type_tolerates_some_noise():
    assert dominant_full_match_type(
        ["03 73 41 92 92", "05 32 14 00 01", "", "non renseigné"]) == "PHONE"


# --- classification complète ------------------------------------------------

def _clients_rows(n=30):
    header = ["code_client", "raison_sociale", "contact_nom", "email",
              "telephone", "ville", "secteur", "effectif", "ca_2025"]
    rows = [header]
    secteurs = ["Industrie", "BTP", "Textile"]
    for i in range(n):
        rows.append([
            "C%07d" % (i + 1),
            "Atelier Verlaine SAS %d" % i,
            "Leclerc%d" % i,
            "a%d@exemple.fr" % i,
            "03 73 41 92 %02d" % (i % 100),
            "Nantes" if i % 2 else "La Rochelle",
            secteurs[i % 3],
            str(10 + i),
            str(100000 + i),
        ])
    return rows


def test_classify_columns_types_known_headers():
    plans = classify_columns(_clients_rows(), has_header=True)
    assert plans[2].policy == TYPED and plans[2].etype == "PERSON"
    assert plans[1].policy == TYPED and plans[1].etype == "ORG"
    assert plans[3].policy == TYPED and plans[3].etype == "EMAIL"
    assert plans[5].policy == TYPED and plans[5].etype == "ADDRESS"


def test_classify_columns_scans_numeric_phone_column():
    """Régression : une colonne sans lettre était totalement ignorée."""
    plans = classify_columns(_clients_rows(), has_header=True)
    assert plans[4].policy == TYPED and plans[4].etype == "PHONE"


def test_classify_columns_skips_nomenclature_column():
    plans = classify_columns(_clients_rows(), has_header=True)
    assert plans[6].policy == SKIP          # secteur : 3 valeurs pour 30 lignes


def test_classify_columns_skips_numeric_measures():
    plans = classify_columns(_clients_rows(), has_header=True)
    assert plans[7].policy == SKIP          # effectif
    assert plans[8].policy == SKIP          # ca_2025


def test_classify_columns_leaves_identifier_column_to_the_model():
    plans = classify_columns(_clients_rows(), has_header=True)
    assert plans[0].policy == TEXT          # code_client : ni typé, ni exclu


def test_classify_columns_keeps_free_text_column_as_text():
    rows = [["Commentaire"]] + [["Vu avec Claire Martin le %d/01" % (i + 1)]
                                for i in range(30)]
    plans = classify_columns(rows, has_header=True)
    assert plans[0].policy == TEXT


def test_classify_columns_without_header_never_types():
    rows = [["Claire Martin", "Nantes"], ["Hugo Dupont", "Lyon"]]
    plans = classify_columns(rows, has_header=False)
    assert all(p.policy != TYPED or p.etype != "PERSON" for p in plans.values())


def test_cardinality_guard_spares_repeated_identities():
    """Dans un grand livre comptable, un même client revient sur des milliers
    de lignes : ratio faible, mais ce n'est pas une nomenclature."""
    rows = [["CompteNum", "CompAuxLib"]]
    for i in range(2000):
        rows.append(["41100000", "Client %d" % (i % 300)])
    assert classify_columns(rows, has_header=True)[1].policy == TEXT


def test_cardinality_guard_needs_enough_rows():
    """Sur un petit fichier, peu de valeurs distinctes ne prouve rien."""
    rows = [["Metier"], ["Plombier"], ["Plombier"], ["Couvreur"]]
    assert classify_columns(rows, has_header=True)[0].policy == TEXT


def test_default_maskable_columns_excludes_skipped_only():
    plans = classify_columns(_clients_rows(), has_header=True)
    cols = default_maskable_columns(_clients_rows(), has_header=True)
    assert cols == {c for c, p in plans.items() if p.policy != SKIP}
    assert 4 in cols and 6 not in cols


# --- vocabulaire de noms de colonnes --------------------------------------

def test_is_column_name_accepts_typed_identifier_and_neutral_headers():
    assert is_column_name("contact_nom")        # typé PERSON
    assert is_column_name("code_client")        # identifiant, non typé
    assert is_column_name("secteur")            # nomenclature, non typée
    assert is_column_name("Montant HT")
    assert is_column_name("date_entree")


def test_is_column_name_rejects_data_values():
    assert not is_column_name("Claire Martin")
    assert not is_column_name("La Rochelle")
    assert not is_column_name("Atelier Verlaine SAS")
    assert not is_column_name("03 73 41 92 92")
    assert not is_column_name("")


def test_looks_like_header_row_on_column_names():
    assert looks_like_header_row(["contact_nom", "ville", "secteur"])
    assert looks_like_header_row(["code_client", "raison_sociale", "libelle"])


def test_looks_like_header_row_rejects_data_row():
    assert not looks_like_header_row(["Claire Martin", "Nantes", "Industrie"])
    assert not looks_like_header_row(["Hugo Dupont", "Lyon"])


def test_looks_like_header_row_needs_two_recognised_names():
    """Un seul mot reconnu peut être une coïncidence : on ne tranche pas."""
    assert not looks_like_header_row(["contact_nom", "Nantes", "Industrie"])


def test_looks_like_header_row_rejects_duplicates_and_short_rows():
    assert not looks_like_header_row(["nom", "nom"])
    assert not looks_like_header_row(["contact_nom"])
    assert not looks_like_header_row([])
