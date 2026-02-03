"""
Spelling Verification Service.

This service provides intelligent name spelling verification and
phonetic analysis to handle the complexity of French names,
foreign names, and various transcription challenges.
"""

import re
from typing import Dict, List, Optional, Tuple

# French phonetic alphabet (NATO adapted for French)
FRENCH_PHONETIC_ALPHABET: Dict[str, str] = {
    "A": "Anatole",
    "B": "Berthe",
    "C": "Célestin",
    "D": "Désiré",
    "E": "Eugène",
    "F": "François",
    "G": "Gaston",
    "H": "Henri",
    "I": "Irma",
    "J": "Joseph",
    "K": "Kléber",
    "L": "Louis",
    "M": "Marcel",
    "N": "Nicolas",
    "O": "Oscar",
    "P": "Pierre",
    "Q": "Quintal",
    "R": "Raoul",
    "S": "Suzanne",
    "T": "Thérèse",
    "U": "Ursule",
    "V": "Victor",
    "W": "William",
    "X": "Xavier",
    "Y": "Yvonne",
    "Z": "Zoé",
}

# Common transcription confusions (phonetically similar)
COMMON_CONFUSIONS: Dict[str, List[str]] = {
    # Vowel confusions
    "au": ["o", "eau", "ô", "aud", "aut", "aux"],
    "eau": ["o", "au", "ô", "eaux"],
    "ai": ["é", "è", "ait", "ais", "aie", "ay"],
    "é": ["ai", "er", "ez", "ée", "és"],
    "è": ["ai", "ê", "et", "aie"],
    "ou": ["oo", "oû", "oux"],
    "an": ["en", "ant", "and", "anc", "ang"],
    "en": ["an", "ent", "end", "enc", "eng"],
    "in": ["ain", "ein", "im", "yn", "ym"],
    "on": ["om", "ont", "ond", "onc"],
    "un": ["um"],

    # Consonant confusions
    "c": ["k", "qu", "q", "ck"],
    "k": ["c", "qu", "q", "ck"],
    "qu": ["k", "c", "q"],
    "ph": ["f"],
    "f": ["ph"],
    "gu": ["g"],
    "gn": ["ni", "ny"],
    "ch": ["sh", "tch"],
    "j": ["g", "dj"],
    "g": ["j", "gu", "ge"],
    "s": ["ss", "c", "ç", "sc", "x", ""],  # includes silent ending
    "ss": ["s", "c", "ç"],
    "z": ["s", "x", ""],  # includes silent ending
    "x": ["ks", "gz", "s", "z", ""],  # includes silent ending
    "t": ["tt", "th", ""],  # includes silent ending
    "tt": ["t"],
    "th": ["t"],
    "d": ["dd", "t", ""],  # includes silent ending
    "b": ["bb", "p"],
    "p": ["pp", "b"],
    "m": ["mm", "n"],
    "n": ["nn", "m"],
    "l": ["ll"],
    "ll": ["l", "y", "ille"],
    "y": ["i", "ï", "ill"],
    "w": ["ou", "v"],

    # Common name endings (eau already defined above with vowel confusions)
    "ault": ["eau", "aut", "aud", "au", "o"],
    "aud": ["o", "eau", "au", "ault", "aut"],
    "et": ["ay", "ey", "é", "er"],
    "er": ["é", "ier", "yer"],
    "ier": ["yer", "ié", "iez"],
}

# Common French name patterns that are often misspelled
COMMON_NAME_PATTERNS: Dict[str, List[str]] = {
    # Double letters
    "Anne": ["Ann", "Ane", "An"],
    "Philippe": ["Philip", "Philipe", "Phillipe", "Filip"],
    "Guillaume": ["Guilaume", "Gillaume", "Giyom"],
    "Emmanuel": ["Emanuel", "Imanuel", "Emanuelle"],
    "Isabelle": ["Isabel", "Izabelle", "Izabel"],

    # Hyphenated names
    "Jean-Pierre": ["Jeanpierre", "Jean Pierre"],
    "Marie-Claire": ["Marieclaire", "Marie Claire"],
    "Anne-Sophie": ["Annesophie", "Anne Sophie"],

    # Accented names
    "Gaël": ["Gael", "Gaelle", "Gal"],
    "Noël": ["Noel", "Noelle"],
    "Zoé": ["Zoe", "Zoey"],
    "Anaïs": ["Anais", "Anaiss"],
    "Joël": ["Joel", "Joelle"],

    # Silent letters
    "Renault": ["Renaud", "Reno", "Renauld"],
    "Lefèbvre": ["Lefebvre", "Lefevre", "Lefebre"],
    "Lefebvre": ["Lefevre", "Lefèbvre", "Lefebre"],

    # Foreign origin names
    "Nguyen": ["Nuen", "Ngoyen", "Nguien", "Ngyen"],
    "Pham": ["Fam", "Pam", "Phame"],
    "N'Djoli": ["Ndjoli", "N Djoli", "Indjoli"],
    "D'Haene": ["Dhaene", "D Haene", "Dene"],
    "Tchatchouang": ["Tchatchoang", "Tchatchuang", "Chatchouang"],
}


class SpellingVerificationService:
    """
    Service for verifying and confirming name spellings.

    This service handles the complex task of verifying names
    that are prone to transcription errors in voice applications.
    """

    # Letters that sound similar and need phonetic clarification
    CONFUSING_LETTERS = {
        "B", "D",  # B/D confusion
        "M", "N",  # M/N confusion
        "P", "B",  # P/B confusion
        "T", "D",  # T/D confusion
        "F", "S",  # F/S confusion
        "V", "B",  # V/B confusion
        "G", "J",  # G/J confusion
        "C", "S",  # C/S confusion
        "K", "Q",  # K/Q confusion
    }

    def generate_phonetic_spelling(self, name: str) -> str:
        """
        Generate a smart phonetic spelling - only phonetic for confusing letters.

        Simple vowels (A, E, I, O, U) and clear consonants (L, R) are just spelled.
        Confusing consonants get phonetic help (B comme Berthe, D comme Désiré).

        Args:
            name: The name to spell out phonetically

        Returns:
            Concise phonetic spelling string
        """
        result = []
        name_upper = name.upper()
        
        for i, char in enumerate(name_upper):
            if char == "-":
                result.append("tiret")
            elif char == "'":
                result.append("apostrophe")
            elif char == " ":
                result.append("espace")
            elif char in FRENCH_PHONETIC_ALPHABET:
                # Only use phonetic for confusing letters
                if char in self.CONFUSING_LETTERS:
                    result.append(f"{char} comme {FRENCH_PHONETIC_ALPHABET[char]}")
                else:
                    result.append(char)
            elif char.isalpha():
                # For accented characters - always clarify
                base_char = self._remove_accents(char)
                accent_name = self._get_accent_name(char)
                if accent_name:
                    result.append(f"{char} ({accent_name})")
                else:
                    result.append(char)

        return ", ".join(result)

    def _get_accent_name(self, char: str) -> str:
        """Get the accent name for an accented character."""
        accent_names = {
            "À": "A accent grave", "Â": "A accent circonflexe", "Ä": "A tréma",
            "É": "E accent aigu", "È": "E accent grave", "Ê": "E accent circonflexe", "Ë": "E tréma",
            "Î": "I accent circonflexe", "Ï": "I tréma",
            "Ô": "O accent circonflexe", "Ö": "O tréma",
            "Ù": "U accent grave", "Û": "U accent circonflexe", "Ü": "U tréma",
            "Ç": "C cédille", "Ñ": "N tilde",
            # Lowercase
            "à": "a accent grave", "â": "a accent circonflexe", "ä": "a tréma",
            "é": "e accent aigu", "è": "e accent grave", "ê": "e accent circonflexe", "ë": "e tréma",
            "î": "i accent circonflexe", "ï": "i tréma",
            "ô": "o accent circonflexe", "ö": "o tréma",
            "ù": "u accent grave", "û": "u accent circonflexe", "ü": "u tréma",
            "ç": "c cédille", "ñ": "n tilde",
        }
        return accent_names.get(char, "")

    def _remove_accents(self, char: str) -> str:
        """Remove accents from a character."""
        accent_map = {
            "À": "A", "Â": "A", "Ä": "A", "Á": "A",
            "È": "E", "Ê": "E", "Ë": "E", "É": "E",
            "Ì": "I", "Î": "I", "Ï": "I", "Í": "I",
            "Ò": "O", "Ô": "O", "Ö": "O", "Ó": "O",
            "Ù": "U", "Û": "U", "Ü": "U", "Ú": "U",
            "Ç": "C", "Ñ": "N",
        }
        return accent_map.get(char, char)

    def generate_verification_prompt(self, name: str) -> str:
        """
        Generate a natural verification prompt for a name.

        Creates a human-friendly way to verify the name spelling,
        emphasizing potential confusion points.

        Args:
            name: The name to create a verification prompt for

        Returns:
            A natural language verification prompt with phonetic spelling
        """
        phonetic = self.generate_phonetic_spelling(name)
        issues = self._identify_potential_issues(name)

        if not issues:
            # Simple verification with phonetic spelling
            return (
                f"J'ai noté '{name}', soit : {phonetic}. "
                f"Est-ce correct ?"
            )

        # Build a detailed verification with emphasis on tricky parts
        emphasis_parts = []
        for issue_type, description in issues:
            emphasis_parts.append(description)

        emphasis_text = ", ".join(emphasis_parts)

        return (
            f"J'ai compris '{name}', soit : {phonetic}. "
            f"Pour être sûr, pouvez-vous me confirmer : {emphasis_text} ? "
            f"Est-ce bien orthographié ainsi ?"
        )

    def _identify_potential_issues(self, name: str) -> List[Tuple[str, str]]:
        """
        Identify potential spelling issues in a name.

        Args:
            name: The name to analyze

        Returns:
            List of (issue_type, description) tuples
        """
        issues = []
        name_lower = name.lower()

        # Check for double letters
        double_letters = re.findall(r'(.)\1', name_lower)
        if double_letters:
            for letter in set(double_letters):
                issues.append(("double_letter", f"deux '{letter}'"))

        # Check for special characters
        if "-" in name:
            issues.append(("hyphen", "avec un tiret"))
        if "'" in name:
            issues.append(("apostrophe", "avec une apostrophe"))
        if " " in name:
            issues.append(("space", "en plusieurs mots"))

        # Check for accented characters
        accented = re.findall(r'[àâäéèêëïîôùûüç]', name_lower)
        if accented:
            for char in set(accented):
                accent_desc = self._get_accent_name(char)
                issues.append(("accent", f"'{char}' {accent_desc}"))

        # Check for silent letters at end
        if name_lower.endswith(('d', 't', 's', 'x', 'z')):
            issues.append(("silent_ending", f"terminant par '{name[-1]}'"))

        # Check for potentially confusing patterns
        for pattern in ["ph", "ch", "gn", "gu", "qu", "th"]:
            if pattern in name_lower:
                issues.append(("digraph", f"'{pattern}' comme dans {self._get_pattern_example(pattern)}"))

        return issues

    def _get_pattern_example(self, pattern: str) -> str:
        """Get an example word for a digraph pattern."""
        examples = {
            "ph": "'Philippe'",
            "ch": "'Charles'",
            "gn": "'Champagne'",
            "gu": "'Guillaume'",
            "qu": "'Jacques'",
            "th": "'Thomas'",
        }
        return examples.get(pattern, f"'{pattern}'")

    def find_correct_spelling(self, name: str) -> Optional[str]:
        """
        Check if the name matches a known misspelling and return the correct form.

        Uses COMMON_NAME_PATTERNS to detect common transcription errors
        like "Nuen" -> "Nguyen" or "Philip" -> "Philippe".

        Args:
            name: The name as transcribed (potentially misspelled)

        Returns:
            The correct spelling if found, None otherwise
        """
        name_normalized = name.strip()

        # Check if it's a known misspelling
        for correct_name, misspellings in COMMON_NAME_PATTERNS.items():
            if name_normalized.lower() in [m.lower() for m in misspellings]:
                return correct_name

        return None

    def get_possible_confusions(self, name: str) -> List[str]:
        """
        Generate possible alternative spellings based on phonetic confusions.

        Uses COMMON_CONFUSIONS to find patterns in the name that could
        be confused with other spellings (e.g., "au" vs "eau" vs "o").

        Args:
            name: The name to analyze

        Returns:
            List of possible alternative spellings
        """
        alternatives = set()
        name_lower = name.lower()

        for pattern, confusions in COMMON_CONFUSIONS.items():
            if pattern in name_lower:
                for alternative in confusions:
                    if alternative:  # Skip empty strings (silent endings)
                        alt_name = name_lower.replace(pattern, alternative, 1)
                        # Preserve original capitalization
                        if name[0].isupper():
                            alt_name = alt_name.capitalize()
                        alternatives.add(alt_name)

        return list(alternatives)[:5]  # Limit to 5 suggestions


# Singleton instance
_spelling_service: Optional[SpellingVerificationService] = None


def get_spelling_service() -> SpellingVerificationService:
    """Get the singleton spelling verification service instance."""
    global _spelling_service
    if _spelling_service is None:
        _spelling_service = SpellingVerificationService()
    return _spelling_service
