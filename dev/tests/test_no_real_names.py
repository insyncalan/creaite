"""No real client, company, project or people names in the repository (Alan, 14-10-2026).

creaite's examples, mockups, tests and docs use fictional data only (the sample registers, dev/tools/demo_data.py and
the test fixtures). This scans every tracked text file (`git ls-files`, skipping vendored libraries and binary files)
and fails if any word, or any two-word phrase, matches a banned name. The banned names are stored only as SHA-256
hashes of the lower-cased name, so this file never publishes them.

To ban another name, add the hash of its lower-cased form (one word, or two words separated by one space):
    python3 -c "import hashlib;print(hashlib.sha256(b'name').hexdigest())"

Run: python3 dev/tests/test_no_real_names.py
"""
import hashlib
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANNED = frozenset({
    "97a6eb426111984bea4e6346d4381bf7265c1acb864ff88aa65e3cacbf698d9e",
    "e192cd5626a00f0dfd97cee3d5d99b64972a8c161c31bec2c67395e68a6adca4",
    "aaadc31b1826c3b92a9fb03cb28c0f06110f82942877a040acebb8604937ba12",
    "cc446d5e475fe2936f5089841eaf6d13618b57625be8437021e156518e596418",
    "6aff1bb1b50525063ad48e222220a50a0c47374eea325abd5533c979ba204191",
    "ac2c6f6fc9cdd1ccb1bc307070396eab61f5bcbdb98c3b9b1f7c930b14c422c3",
    "60bd7fd2ab7e986e85355c8011d197aa4d97c3956352aa32cc6d94b5b92df295",
    "704d45f5fa2b893677831d0394693e388e9826de155a5d29f77472397229bdae",
    "33ec6ed7a20fab8d7207db970a9308768473be8b64d59277a2b30f6524584a6e",
    "64d68806ef56ee71e8b59e7f19bc50fee515ed11e1ebd6dbda5a109f4fd75356",
    "8aed32fd8a238520301c00b64ad98b2f18295efb2dc53bbc6e27c92c3fdb162c",
    "b32f52bf59a62214b66a6d6769611b7e7c2c5361cb940d54874c64a4189692e9",
    "1c7272b3cb1d980b7701040e8afd537af886a437cd718ffdaf7c49c41171e11c",
    "bdaf2f8d04cea26aa546876b1e27b3e4db96a524a128dd033745b2de5a5c175a",
    "e4bb33e05498befc02052011b9a04bcb4eb99006088fcea77fc829385430f288",
    "c932bc96718c66e1dfea8f9432471e296a81d33c1fd0d3970ed7f87e57bb2459",
    "4b7bb8c301065be38ebed64ed1e85e4ef6f6a06210b6c29abc5919619819b7c0",
    "160a5c716369cdb64d13e8f4cf6ee75f1cf7d70c2252a75d50f86223835716d6",
    "3b9b21b853639a9b7c1ce503095776aba9c567961c27a665a3cd87702a8acc3d",
    "4ec0fd7916e201d92f7ba220d13f227794d2c37fd91b8d5c733c0491e71d53a6",
    "2b98fb6954368ff3f28f3367b697c1ae3b3d1e69b82a5de92b58a5e40993bbe0",
    "e52b22b4438ef532d7f816216eb50de1ac9ea7646bcf2d356ac6eac6f4abe013",
    "8b4bbb2e1aa22e7a50140affbd254bc86bdffcd3c1700e57b00282e1cb1b9c33",
    "2ebae47bc84f5cc5a86d5de2cf3508720acedd2e30f1595c028412bd5eacbb0f",
    "3343cd126b042f8d61c1c3cdcf543926d3f67c1354a703662a8e7292c77b03f9",
    "d6e2ded0c7a3fba5aea5494d699088f14bd6fca977fe8f6dc44c3b7a3665e1f6",
    "3a22797258870f8ca0a9c898e29b9e5d08f76d65302c3794d322590808944e2c",
    "3a8ce1b9a36dd74a795466108fc8c285d7715ddc716254fef017afd003777774",
    "be53aa7b1e2d707d139b6a4cab9efc5dcdedd730bd649b504555736d955f2301",
    "319ec3e742d3a04898f95a619fe42172baba030c0c00c5deb32968108ffa41e4",
    "6459067ae461097b1099d067b577b600bd4da33315a3645801cc82034dd60fb2",
    "9fe03ea331bba94a4369f1c82cf0981fe401dda25c26a9b2abbb9c242e7a4ebd",
    "0e16af977ef0e07a117d91be07452c6ee2e306347eaf1e14aca1b1454f0af846",
    "ec6a13b802f63ae75d26f5635297a1c725b5ad6f2489fd229f77661ff80602f0",
    "626858e017b57b84c2c082ba464c4e9179e65647c23ed0ea9c6926bdb753f599",
    "8b09cc07d943ee9d68dd3e53d34b09b88779427e9b3013fa9111f41cc74baa6b",
    "22f83076aa7a9955ce280140369a92974477e316c2bf997dc8e1390d9432fc6c",
})
WORD = re.compile(r"[a-z0-9]+")
DOMAIN = re.compile(r"@([a-z0-9-]+(?:\.[a-z0-9-]+)+)")
SKIP = re.compile(r"(^|/)vendor/|\.(png|jpe?g|gif|ic(?:o|ns)|docx|xlsx|pptx|pdf|zip|gz|woff2?|ttf|otf|db|sqlite)$", re.I)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p and not SKIP.search(p)]


def text_of(path):
    try:
        data = (ROOT / path).read_bytes()
    except (FileNotFoundError, IsADirectoryError):
        return None
    if b"\0" in data:
        return None
    return data.decode("utf-8", "ignore")


def banned_domain(domain):
    """An email domain is banned when the whole of it, or the part before its last dot, or any one part is."""
    parts = domain.split(".")
    return any(digest(x) in BANNED for x in (domain, ".".join(parts[:-1]), *parts))


def banned_in(text):
    """Line numbers and (hashed) hits: each word, each pair of neighbouring words and each email domain, lower-cased."""
    hits = []
    for n, line in enumerate(text.lower().splitlines(), 1):
        if any(banned_domain(d) for d in DOMAIN.findall(line)):
            hits.append(n)
            continue
        words = WORD.findall(line)
        for i, w in enumerate(words):
            if digest(w) in BANNED or (i + 1 < len(words) and digest(f"{w} {words[i + 1]}") in BANNED):
                hits.append(n)
                break
    return hits


class NoRealNames(unittest.TestCase):
    def test_the_check_itself(self):
        self.assertEqual(len(BANNED), len(set(BANNED)))
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", h) for h in BANNED))
        self.assertEqual(banned_in("Jane Doe and Omar Ali, ABC Example Programme, jane.doe@client.com"), [])
        self.assertFalse(banned_domain("brightwater.example"))

    def test_no_tracked_file_names_a_real_client_project_or_person(self):
        found = []
        for path in tracked():
            if digest(path.lower()) in BANNED or any(digest(w) in BANNED for w in WORD.findall(path.lower())):
                found.append(f"{path} (its name)")
            text = text_of(path)
            if text is not None:
                found += [f"{path}:{n}" for n in banned_in(text)]
        self.assertEqual(found, [], "a real name (by its hash) is in these places; use the fictional sample data instead")


if __name__ == "__main__":
    unittest.main()
