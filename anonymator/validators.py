import re


def luhn_is_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 2:
        return False
    checksum = 0
    parity = (len(digits) - 1) % 2
    for i, d in enumerate(digits):
        if i % 2 != parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def iban_is_valid(iban: str) -> bool:
    s = iban.replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    rearranged = s[4:] + s[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1


def nir_is_valid(nir: str) -> bool:
    s = nir.replace(" ", "").upper()
    m = re.fullmatch(r"([12]\d{2}(?:0[1-9]|1[0-2]|[02-9]\d)"
                     r"(?:\d{2}|2[AB])\d{3}\d{3})(\d{2})", s)
    if not m:
        return False
    body, key = m.group(1), int(m.group(2))
    num = body.replace("2A", "19").replace("2B", "18")
    return (97 - (int(num) % 97)) == key
