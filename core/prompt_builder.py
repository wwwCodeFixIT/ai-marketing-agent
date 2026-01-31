"""
Prompt Builder - Modułowy system budowania promptów
- Komponenty wielokrotnego użytku
- Anti-generic filter
- Dynamiczne łączenie
- Kontekst z pamięci
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Wspierane platformy"""
    LINKEDIN = "LinkedIn"
    TWITTER = "Twitter"
    FACEBOOK = "Facebook"
    INSTAGRAM = "Instagram"
    THREADS = "Threads"


class ContentGoal(Enum):
    """Cele treści"""
    ENGAGEMENT = "engagement"  # Komentarze, dyskusja
    AUTHORITY = "authority"    # Budowanie ekspertyzy
    VIRAL = "viral"            # Maksymalny zasięg
    CONVERSION = "conversion"  # Kliknięcia, zapisy
    EDUCATION = "education"    # Wartość edukacyjna
    STORYTELLING = "storytelling"  # Opowieść


class ContentStyle(Enum):
    """Style treści"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    CONTROVERSIAL = "controversial"
    INSPIRATIONAL = "inspirational"
    ANALYTICAL = "analytical"
    HUMOROUS = "humorous"


@dataclass
class PromptContext:
    """Kontekst do budowania prompta"""
    topic: str
    platform: Platform
    goal: ContentGoal = ContentGoal.ENGAGEMENT
    style: ContentStyle = ContentStyle.PROFESSIONAL
    brand_context: str = ""
    learning_context: str = ""
    additional_instructions: str = ""
    max_length: Optional[int] = None


class PromptComponents:
    """
    Biblioteka komponentów promptów.
    Każdy komponent to cegiełka do złożenia pełnego prompta.
    """
    
    # === ROLE AGENTÓW ===
    
    AGENT_ROLES = {
        "strategist": """
Jesteś STRATEGIEM MARKETINGOWYM z 15-letnim doświadczeniem w tech marketing.
Twoja rola: Analiza, planowanie, określenie kąta podejścia.
NIE piszesz treści - tylko strategię.
Myślisz jak strateg, nie jak copywriter.
""",
        
        "copywriter": """
Jesteś SENIOR COPYWRITEREM specjalizującym się w content marketing dla branży IT.
Twoja rola: Pisanie angażujących treści na podstawie strategii.
Piszesz jak człowiek, nie jak AI.
Każde słowo ma znaczenie.
""",
        
        "editor": """
Jesteś REDAKTOREM z doświadczeniem w social media.
Twoja rola: Skracanie, poprawa flow, wzmocnienie CTA.
Wycinasz zbędne słowa bezlitośnie.
Każde zdanie musi pracować.
""",
        
        "critic": """
Jesteś SUROWYM KRYTYKIEM treści marketingowych.
Twoja rola: Ocena jakości, wykrywanie "AI-smrodu", banałów.
Jesteś bezlitosny ale konstruktywny.
Oceniasz w skali 1-10 z uzasadnieniem.
""",
        
        "brand_guardian": """
Jesteś STRAŻNIKIEM MARKI.
Twoja rola: Sprawdzenie zgodności z tone of voice i zasadami marki.
Wykrywasz naruszenia brand guidelines.
Zwracasz konkretne problemy do poprawy.
"""
    }
    
    # === ZASADY PLATFORM ===
    
    PLATFORM_RULES = {
    Platform.LINKEDIN: """
=== ZASADY LINKEDIN ===
FORMAT:
- Pierwszy wiersz = HOOK (przyciągnij uwagę w 2 sekundy) - może zaczynać się od emoji
- Krótkie akapity (1-2 zdania)
- Pusta linia między akapitami
- Użyj 2-4 emoji strategicznie (na początku sekcji, przy kluczowych punktach)
- CTA na końcu (pytanie lub zachęta do komentarza)

STYL:
- Storytelling > suche fakty
- Profesjonalny ale ludzki i ciepły
- Konkretne liczby i przykłady
- Unikaj korporacyjnego żargonu

STRUKTURA POSTA:
🎯 [HOOK - mocne otwarcie]

[Historia / Problem / Kontekst]

💡 [Kluczowy insight lub lekcja]

[Rozwinięcie z konkretnymi przykładami]

✅ [Podsumowanie / Takeaway]

👇 [CTA - pytanie do społeczności]

DŁUGOŚĆ: 1200-1800 znaków
EMOJI: 3-5 strategicznie rozmieszczonych (🎯💡✅🚀💪📈🔥⚡️👇)
HASHTAGI: 3-5 na końcu
""",
    
    Platform.TWITTER: """
=== ZASADY TWITTER/X ===
FORMAT:
- Jedna myśl = jeden tweet
- Punchy, kontrowersyjny lub ultra-konkretny
- Bez wstępów, od razu do rzeczy
- Emoji na początku lub końcu dla uwagi

STYL:
- Hot take > lukewarm opinion
- Liczby i konkret działają
- Pytania retoryczne angażują
- Można być ostrzejszym niż na LinkedIn

STRUKTURA:
🔥 [Mocne stwierdzenie]

[Rozwinięcie w 1-2 zdaniach]

[Opcjonalnie: CTA lub pytanie]

DŁUGOŚĆ: Max 280 znaków
EMOJI: 1-2 (🔥⚡️🚀💡🎯)
HASHTAGI: Max 2
""",
    
    Platform.FACEBOOK: """
=== ZASADY FACEBOOK ===
FORMAT:
- Hook z emoji na początku
- Historia lub anegdota osobista
- Zakończ pytaniem do dyskusji

STYL:
- Konwersacyjny, kumpelski, ciepły
- Emocjonalny > racjonalny
- Personal stories działają najlepiej
- Wywoływanie dyskusji w komentarzach

STRUKTURA:
😊 [Osobiste otwarcie]

[Historia / Anegdota]

🤔 [Refleksja / Lekcja]

❓ [Pytanie do społeczności]

DŁUGOŚĆ: 500-1500 znaków
EMOJI: 4-6 (😊🤔❓💪🎉👏)
HASHTAGI: 0-2
""",
    
    Platform.INSTAGRAM: """
=== ZASADY INSTAGRAM ===
FORMAT:
- Pierwszy wiersz widoczny bez rozwinięcia - musi przyciągać!
- Emoji w pierwszej linii obowiązkowo
- Możliwe bullet points z emoji
- Hashtagi na końcu lub w pierwszym komentarzu

STYL:
- Wizualny język
- Inspiracyjny lub edukacyjny
- Micro-storytelling
- Autentyczność > polerowany wizerunek

STRUKTURA:
✨ [Hook - przyciągający uwagę]

[Krótka historia lub kontekst]

📌 Punkt 1
📌 Punkt 2  
📌 Punkt 3

💬 [CTA]

DŁUGOŚĆ: 500-2200 znaków
EMOJI: 5-10 (✨📌💬🔥💪🙌⭐️💡🎯❤️)
HASHTAGI: 5-15 relevantnych
""",
    
    Platform.THREADS: """
=== ZASADY THREADS ===
FORMAT:
- Podobnie do Twittera ale dłuższe
- Seria powiązanych myśli
- Konwersacyjny ton
- Emoji naturalnie wplecione

STYL:
- Casual, jakbyś pisał do znajomych
- Opinie i hot takes
- Mniej "marketingowy" niż inne platformy
- Autentyczność jest kluczowa

DŁUGOŚĆ: Do 500 znaków
EMOJI: 2-4 naturalnie
HASHTAGI: 0-3
"""
}
    
    # === CELE TREŚCI ===
    
    GOAL_INSTRUCTIONS = {
        ContentGoal.ENGAGEMENT: """
CEL: MAKSYMALNE ZAANGAŻOWANIE
- Zakończ pytaniem które prowokuje do odpowiedzi
- Porusz temat kontrowersyjny ale bezpieczny
- Podziel się opinią i poproś o zdanie innych
- Unikaj zamkniętych stwierdzeń
""",
        
        ContentGoal.AUTHORITY: """
CEL: BUDOWANIE AUTORYTETU EKSPERTA
- Pokaż głęboką wiedzę, nie powierzchowną
- Użyj konkretnych danych i przykładów
- Podziel się unikalnym insight'em
- Zakończ actionable takeaway
""",
        
        ContentGoal.VIRAL: """
CEL: POTENCJAŁ VIRALOWY
- Kontrowersyjne ale nie obraźliwe
- Relatable - ludzie muszą się utożsamić
- Shareability - czy ktoś to podeśle znajomemu?
- Format łatwy do konsumpcji
""",
        
        ContentGoal.CONVERSION: """
CEL: KONWERSJA (kliknięcia, zapisy)
- Jasna propozycja wartości
- Konkretne CTA
- Usuń tarcie (wątpliwości)
- Social proof jeśli możliwe
""",
        
        ContentGoal.EDUCATION: """
CEL: WARTOŚĆ EDUKACYJNA
- Naucz czegoś konkretnego
- Struktura: Problem → Rozwiązanie → Jak zastosować
- Actionable tips
- Zapisywalne (ludzie będą wracać)
""",
        
        ContentGoal.STORYTELLING: """
CEL: STORYTELLING
- Struktura: Hook → Konflikt → Rozwiązanie → Lekcja
- Bohater (Ty lub klient)
- Emocjonalne momenty
- Uniwersalna prawda na końcu
"""
    }
    
    # === STYLE TREŚCI ===
    
    STYLE_MODIFIERS = {
        ContentStyle.PROFESSIONAL: """
STYL: PROFESJONALNY
- Rzeczowy ale nie suchy
- Ekspert który wyjaśnia, nie poucza
- Konkretne przykłady i dane
- Unikaj żargonu bez wyjaśnienia
""",
        
        ContentStyle.CASUAL: """
STYL: CASUAL / LUŹNY
- Pisz jak mówisz
- Skróty OK, slang dozwolony
- Humor mile widziany
- Nie udawaj kogoś kim nie jesteś
""",
        
        ContentStyle.CONTROVERSIAL: """
STYL: KONTROWERSYJNY
- Zajmij wyraźne stanowisko
- Spolaryzuj (nie wszyscy muszą się zgadzać)
- Bronialna pozycja (możesz ją uzasadnić)
- Prowokuj do myślenia
""",
        
        ContentStyle.INSPIRATIONAL: """
STYL: INSPIRACYJNY
- Energie i motywacja
- Historia transformacji
- "Jeśli ja mogłem, ty też możesz"
- Zakończ call to action
""",
        
        ContentStyle.ANALYTICAL: """
STYL: ANALITYCZNY
- Dane i fakty
- Logiczna argumentacja
- Wykresy i liczby (opisowo)
- Obiektywna perspektywa
""",
        
        ContentStyle.HUMOROUS: """
STYL: HUMORYSTYCZNY
- Ironia i sarkazm dozwolone
- Self-deprecating humor działa
- Nie bądź offensive
- Humor służy message'owi
"""
    }
    
    # === ANTI-GENERIC FILTER ===
    
    ANTI_GENERIC_FILTER = """
=== ANTI-GENERIC FILTER ===
ABSOLUTNIE ZAKAZANE:
❌ "W dzisiejszym dynamicznym świecie..."
❌ "Innowacyjne rozwiązania"
❌ "Game-changer"
❌ "Synergicznie"
❌ "Kompleksowe podejście"
❌ "Holistycznie"
❌ "Witajcie/Cześć wszystkim"
❌ "Miło mi poinformować"
❌ "Z przyjemnością ogłaszam"
❌ "Excited to announce"
❌ Ogólnikowe stwierdzenia bez konkretu
❌ Buzzwordy bez znaczenia
❌ Nadmierne przymiotniki

ZAMIAST TEGO:
✓ Konkrety, liczby, przykłady
✓ Opinie zamiast truizmów
✓ Personal stories
✓ Unikalny kąt spojrzenia
✓ Coś czego AI by nie napisał
✓ Zdania które można podważyć (= mają wartość)

TEST: Czy ten tekst mógłby napisać KAŻDY?
Jeśli tak - przepisz go tak, by był TWÓJ.
"""
    
    # === QUALITY CHECKLIST ===
    
    QUALITY_CHECKLIST = """
=== CHECKLIST JAKOŚCI ===
Przed zwróceniem treści sprawdź:

□ Hook - Czy pierwszy wiersz zatrzymuje scroll?
□ Konkret - Czy są specifics zamiast generics?
□ Value - Czy czytelnik coś zyskuje?
□ CTA - Czy wiadomo co robić dalej?
□ Flow - Czy czyta się płynnie?
□ Length - Czy długość pasuje do platformy?
□ Brand - Czy to brzmi jak TA marka?
□ Human - Czy to brzmi jak człowiek?
"""


class PromptBuilder:
    """
    Główna klasa do budowania promptów.
    Łączy komponenty w pełne, kontekstowe prompty.
    """
    
    def __init__(self):
        self.components = PromptComponents()
    
    def build_system_prompt(
        self,
        agent_role: str,
        context: PromptContext
    ) -> str:
        """
        Buduje system prompt dla danego agenta.
        
        Args:
            agent_role: Rola agenta (strategist, copywriter, editor, critic, brand_guardian)
            context: Kontekst z informacjami o zadaniu
        """
        parts = []
        
        # 1. Rola agenta
        role_prompt = self.components.AGENT_ROLES.get(agent_role, "")
        if role_prompt:
            parts.append(role_prompt)
        
        # 2. Zasady platformy
        platform_rules = self.components.PLATFORM_RULES.get(context.platform, "")
        if platform_rules:
            parts.append(platform_rules)
        
        # 3. Cel treści
        goal_instructions = self.components.GOAL_INSTRUCTIONS.get(context.goal, "")
        if goal_instructions:
            parts.append(goal_instructions)
        
        # 4. Styl treści
        style_modifier = self.components.STYLE_MODIFIERS.get(context.style, "")
        if style_modifier:
            parts.append(style_modifier)
        
        # 5. Kontekst marki (z Brand DNA)
        if context.brand_context:
            parts.append(context.brand_context)
        
        # 6. Kontekst uczenia (z Feedback)
        if context.learning_context:
            parts.append(context.learning_context)
        
        # 7. Anti-generic filter (zawsze dla copywritera i editora)
        if agent_role in ["copywriter", "editor"]:
            parts.append(self.components.ANTI_GENERIC_FILTER)
        
        # 8. Quality checklist (dla copywritera)
        if agent_role == "copywriter":
            parts.append(self.components.QUALITY_CHECKLIST)
        
        # 9. Dodatkowe instrukcje
        if context.additional_instructions:
            parts.append(f"\n=== DODATKOWE INSTRUKCJE ===\n{context.additional_instructions}")
        
        # 10. Limit długości
        if context.max_length:
            parts.append(f"\n⚠️ MAX DŁUGOŚĆ: {context.max_length} znaków")
        
        return "\n\n".join(parts)
    
    def build_user_prompt(
        self,
        agent_role: str,
        context: PromptContext,
        previous_output: str = None,
        critique: str = None
    ) -> str:
        """
        Buduje user prompt (zadanie dla agenta).
        
        Args:
            agent_role: Rola agenta
            context: Kontekst
            previous_output: Wynik poprzedniego kroku (dla editora/critic)
            critique: Krytyka do poprawy (dla editora)
        """
        
        if agent_role == "strategist":
            return f"""
TEMAT: {context.topic}
PLATFORMA: {context.platform.value}
CEL: {context.goal.value}

Opracuj strategię podejścia w 2-3 zdaniach.
Określ:
1. ANGLE (kąt podejścia)
2. HOOK (czym przyciągniesz uwagę)
3. KEY MESSAGE (główny przekaz)

Zwróć TYLKO strategię, nie pisz posta.
"""
        
        elif agent_role == "copywriter":
            return f"""
TEMAT: {context.topic}
PLATFORMA: {context.platform.value}

{f"STRATEGIA DO REALIZACJI: {previous_output}" if previous_output else ""}

Napisz post realizujący powyższą strategię.
Pamiętaj o wszystkich zasadach z system prompta.

Zwróć TYLKO treść posta, bez komentarzy.
"""
        
        elif agent_role == "editor":
            return f"""
ORYGINALNY TEKST:
{previous_output}

{f"UWAGI KRYTYKA: {critique}" if critique else ""}

Popraw tekst:
1. Skróć jeśli za długi
2. Wzmocnij hook
3. Popraw CTA
4. Usuń "AI-smród"

Zwróć TYLKO poprawioną treść, bez komentarzy.
"""
        
        elif agent_role == "critic":
            return f"""
TEKST DO OCENY:
{previous_output}

PLATFORMA: {context.platform.value}
CEL: {context.goal.value}

Oceń tekst krytycznie:
1. SCORE: X/10
2. CO DZIAŁA: (lista)
3. CO NIE DZIAŁA: (lista)
4. CZY BRZMI JAK AI: tak/nie i dlaczego
5. SUGESTIE POPRAWY: (konkretne)

Bądź bezlitosny ale konstruktywny.
"""
        
        elif agent_role == "brand_guardian":
            return f"""
TEKST DO SPRAWDZENIA:
{previous_output}

Sprawdź zgodność z Brand DNA:
1. Czy ton głosu jest zgodny?
2. Czy są zakazane słowa/frazy?
3. Czy polityka emoji jest przestrzegana?
4. Czy pasuje do grupy docelowej?

Zwróć:
- ZGODNY: tak/nie
- PROBLEMY: (lista jeśli są)
- SUGESTIE: (jak naprawić)
"""
        
        return f"TEMAT: {context.topic}"
    
    def build_quick_prompt(
        self,
        topic: str,
        platform: Platform,
        brand_context: str = "",
        style: ContentStyle = ContentStyle.PROFESSIONAL
    ) -> tuple[str, str]:
        """
        Szybki builder dla prostych przypadków.
        Zwraca (system_prompt, user_prompt).
        """
        context = PromptContext(
            topic=topic,
            platform=platform,
            style=style,
            brand_context=brand_context
        )
        
        system = self.build_system_prompt("copywriter", context)
        user = self.build_user_prompt("copywriter", context)
        
        return system, user


# === PRESET PROMPTS (dla szybkiego użycia) ===

class PromptPresets:
    """Gotowe presety dla typowych przypadków"""
    
    @staticmethod
    def viral_linkedin(topic: str, brand_context: str = "") -> PromptContext:
        return PromptContext(
            topic=topic,
            platform=Platform.LINKEDIN,
            goal=ContentGoal.VIRAL,
            style=ContentStyle.CONTROVERSIAL,
            brand_context=brand_context
        )
    
    @staticmethod
    def educational_thread(topic: str, brand_context: str = "") -> PromptContext:
        return PromptContext(
            topic=topic,
            platform=Platform.TWITTER,
            goal=ContentGoal.EDUCATION,
            style=ContentStyle.ANALYTICAL,
            brand_context=brand_context
        )
    
    @staticmethod
    def story_facebook(topic: str, brand_context: str = "") -> PromptContext:
        return PromptContext(
            topic=topic,
            platform=Platform.FACEBOOK,
            goal=ContentGoal.STORYTELLING,
            style=ContentStyle.CASUAL,
            brand_context=brand_context
        )
    
    @staticmethod
    def authority_post(topic: str, platform: Platform, brand_context: str = "") -> PromptContext:
        return PromptContext(
            topic=topic,
            platform=platform,
            goal=ContentGoal.AUTHORITY,
            style=ContentStyle.PROFESSIONAL,
            brand_context=brand_context
        )


# === TESTY MODUŁU ===
if __name__ == "__main__":
    print("=== Test Prompt Builder ===\n")
    
    builder = PromptBuilder()
    
    # Test kontekstu
    context = PromptContext(
        topic="Dlaczego AI nie zastąpi programistów",
        platform=Platform.LINKEDIN,
        goal=ContentGoal.ENGAGEMENT,
        style=ContentStyle.CONTROVERSIAL,
        brand_context="Marka: TechExpert, Ton: Profesjonalny ale odważny"
    )
    
    # Test budowania promptów
    print("1. System Prompt (Strategist):")
    print("-" * 40)
    system = builder.build_system_prompt("strategist", context)
    print(system[:500] + "...\n")
    
    print("2. User Prompt (Strategist):")
    print("-" * 40)
    user = builder.build_user_prompt("strategist", context)
    print(user)
    
    print("\n3. System Prompt (Copywriter):")
    print("-" * 40)
    system = builder.build_system_prompt("copywriter", context)
    print(system[:800] + "...\n")
    
    print("4. Quick Prompt:")
    print("-" * 40)
    sys_p, usr_p = builder.build_quick_prompt(
        "5 błędów juniorów w code review",
        Platform.LINKEDIN
    )
    print(f"System length: {len(sys_p)} chars")
    print(f"User length: {len(usr_p)} chars")
    
    print("\n✅ Prompt Builder działa poprawnie!")