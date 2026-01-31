"""
Memory System - Pamięć długoterminowa agenta
- Brand DNA (tożsamość marki)
- Feedback Manager (uczenie się preferencji)
- Posts History (historia dla few-shot learning)
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ścieżka do folderu data
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


class BrandMemory:
    """
    Przechowuje DNA marki - tożsamość, ton, zasady.
    Agent ZAWSZE uwzględnia te ustawienia.
    """
    
    DEFAULT_DNA = {
        "brand_name": "Moja Marka",
        "tagline": "",
        
        # Ton i styl
        "tone_of_voice": "Ekspercki, ale przystępny",
        "formality_level": "medium",  # low, medium, high
        "personality_traits": ["profesjonalny", "pomocny", "konkretny"],
        
        # Zasady treści
        "forbidden_words": [
            "innowacyjny", "dynamiczny", "game-changer", 
            "witajcie", "w dzisiejszym świecie", "synergiczny"
        ],
        "preferred_phrases": [],
        
        # Formatowanie
        "emoji_policy": "minimal",  # none, minimal, moderate, heavy
        "max_emojis_per_post": 3,
        "hashtag_policy": "minimal",  # none, minimal, moderate
        "max_hashtags": 3,
        
        # Grupa docelowa
        "target_audience": "Profesjonaliści IT, deweloperzy, tech leads",
        "audience_pain_points": [],
        "audience_goals": [],
        
        # Preferencje długości
        "preferred_length": {
            "LinkedIn": "medium",  # short, medium, long
            "Twitter": "short",
            "Facebook": "medium"
        },
        
        # Meta
        "created_at": None,
        "updated_at": None
    }
    
    def __init__(self, filename: str = "brand_dna.json"):
        self.filepath = DATA_DIR / filename
        self.dna = self._load()
        logger.info(f"Brand DNA załadowane: {self.dna['brand_name']}")
    
    def _load(self) -> Dict[str, Any]:
        """Ładuje DNA z pliku lub tworzy domyślne"""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    saved_dna = json.load(f)
                    # Merge z domyślnymi (na wypadek nowych pól)
                    merged = {**self.DEFAULT_DNA, **saved_dna}
                    return merged
            except json.JSONDecodeError:
                logger.warning("Błąd odczytu brand_dna.json, tworzę nowy")
                return self._create_default()
        return self._create_default()
    
    def _create_default(self) -> Dict[str, Any]:
        """Tworzy domyślne DNA"""
        dna = self.DEFAULT_DNA.copy()
        dna["created_at"] = datetime.now().isoformat()
        dna["updated_at"] = datetime.now().isoformat()
        self._save(dna)
        return dna
    
    def _save(self, dna: Dict[str, Any] = None):
        """Zapisuje DNA do pliku"""
        if dna is None:
            dna = self.dna
        dna["updated_at"] = datetime.now().isoformat()
        
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(dna, f, ensure_ascii=False, indent=2)
        logger.info("Brand DNA zapisane")
    
    def update(self, key: str, value: Any) -> bool:
        """Aktualizuje pojedyncze pole DNA"""
        if key in self.dna:
            self.dna[key] = value
            self._save()
            return True
        logger.warning(f"Nieznany klucz DNA: {key}")
        return False
    
    def update_bulk(self, updates: Dict[str, Any]):
        """Aktualizuje wiele pól naraz"""
        for key, value in updates.items():
            if key in self.dna:
                self.dna[key] = value
        self._save()
    
    def add_forbidden_word(self, word: str):
        """Dodaje słowo do listy zakazanych"""
        word = word.lower().strip()
        if word not in self.dna["forbidden_words"]:
            self.dna["forbidden_words"].append(word)
            self._save()
    
    def remove_forbidden_word(self, word: str):
        """Usuwa słowo z listy zakazanych"""
        word = word.lower().strip()
        if word in self.dna["forbidden_words"]:
            self.dna["forbidden_words"].remove(word)
            self._save()
    
    def get_prompt_context(self) -> str:
        """
        Zwraca sformatowany kontekst dla promptów.
        Używane przez AgentEngine.
        """
        forbidden = ", ".join(self.dna["forbidden_words"]) or "brak"
        traits = ", ".join(self.dna["personality_traits"]) or "profesjonalny"
        
        return f"""
=== BRAND DNA ===
Marka: {self.dna['brand_name']}
Ton głosu: {self.dna['tone_of_voice']}
Poziom formalności: {self.dna['formality_level']}
Cechy osobowości: {traits}

Grupa docelowa: {self.dna['target_audience']}

ZASADY:
- Zakazane słowa/frazy: {forbidden}
- Polityka emoji: {self.dna['emoji_policy']} (max {self.dna['max_emojis_per_post']})
- Polityka hashtagów: {self.dna['hashtag_policy']} (max {self.dna['max_hashtags']})
=================
"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Zwraca kopię DNA jako słownik"""
        return self.dna.copy()


class FeedbackManager:
    """
    Zarządza feedbackiem użytkownika.
    Uczy agenta co jest dobre, a co złe.
    """
    
    def __init__(self, filename: str = "feedback.json"):
        self.filepath = DATA_DIR / filename
        self.feedback_data = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """Ładuje historię feedbacku"""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Błąd odczytu feedback.json")
        
        return {
            "positive": [],  # Posty które się podobały
            "negative": [],  # Posty które się nie podobały
            "adjustments": [],  # Konkretne korekty (np. "krótsze", "mniej emoji")
            "stats": {
                "total_positive": 0,
                "total_negative": 0,
                "total_adjustments": 0
            }
        }
    
    def _save(self):
        """Zapisuje feedback"""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.feedback_data, f, ensure_ascii=False, indent=2)
    
    def add_positive(self, content: str, platform: str, metadata: Dict = None):
        """Zapisuje pozytywny feedback"""
        entry = {
            "content_preview": content[:200] + "..." if len(content) > 200 else content,
            "platform": platform,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.feedback_data["positive"].append(entry)
        self.feedback_data["stats"]["total_positive"] += 1
        
        # Limit do 50 ostatnich
        self.feedback_data["positive"] = self.feedback_data["positive"][-50:]
        self._save()
        logger.info(f"Zapisano pozytywny feedback dla {platform}")
    
    def add_negative(self, content: str, platform: str, reason: str = None):
        """Zapisuje negatywny feedback"""
        entry = {
            "content_preview": content[:200] + "..." if len(content) > 200 else content,
            "platform": platform,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self.feedback_data["negative"].append(entry)
        self.feedback_data["stats"]["total_negative"] += 1
        
        # Limit do 50 ostatnich
        self.feedback_data["negative"] = self.feedback_data["negative"][-50:]
        self._save()
        logger.info(f"Zapisano negatywny feedback dla {platform}")
    
    def add_adjustment(self, adjustment_type: str, details: str = None):
        """
        Zapisuje preferencję korekty.
        np. "shorter", "less_emoji", "more_professional"
        """
        entry = {
            "type": adjustment_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.feedback_data["adjustments"].append(entry)
        self.feedback_data["stats"]["total_adjustments"] += 1
        self._save()
    
    def get_learning_context(self, platform: str = None) -> str:
        """
        Zwraca kontekst uczenia dla promptów.
        Agent wie co użytkownik lubi/nie lubi.
        """
        positive = self.feedback_data["positive"]
        negative = self.feedback_data["negative"]
        adjustments = self.feedback_data["adjustments"]
        
        if platform:
            positive = [p for p in positive if p["platform"] == platform]
            negative = [n for n in negative if n["platform"] == platform]
        
        context_parts = []
        
        # Przykłady pozytywne (few-shot)
        if positive:
            context_parts.append("=== PRZYKŁADY DOBREGO STYLU ===")
            for p in positive[-3:]:  # Ostatnie 3
                context_parts.append(f"✓ {p['content_preview']}")
        
        # Czego unikać
        if negative:
            context_parts.append("\n=== CZEGO UNIKAĆ ===")
            for n in negative[-3:]:
                reason = f" (Powód: {n['reason']})" if n.get('reason') else ""
                context_parts.append(f"✗ {n['content_preview']}{reason}")
        
        # Preferencje korekt
        if adjustments:
            recent_adj = {}
            for adj in adjustments[-10:]:
                adj_type = adj["type"]
                recent_adj[adj_type] = recent_adj.get(adj_type, 0) + 1
            
            if recent_adj:
                context_parts.append("\n=== PREFERENCJE UŻYTKOWNIKA ===")
                for adj_type, count in recent_adj.items():
                    if count >= 2:  # Tylko jeśli powtórzone
                        context_parts.append(f"- Preferuje: {adj_type}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def get_stats(self) -> Dict[str, int]:
        """Zwraca statystyki feedbacku"""
        return self.feedback_data["stats"]


class PostsHistory:
    """
    Historia wygenerowanych postów.
    Używana do unikania powtórzeń i analizy.
    """
    
    def __init__(self, filename: str = "posts_history.json"):
        self.filepath = DATA_DIR / filename
        self.history = self._load()
    
    def _load(self) -> List[Dict[str, Any]]:
        """Ładuje historię"""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []
    
    def _save(self):
        """Zapisuje historię"""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def add_post(self, content: str, platform: str, topic: str, 
                 agent_logs: List[str] = None, score: float = None):
        """Dodaje post do historii"""
        entry = {
            "id": len(self.history) + 1,
            "content": content,
            "platform": platform,
            "topic": topic,
            "agent_logs": agent_logs or [],
            "score": score,
            "created_at": datetime.now().isoformat()
        }
        self.history.append(entry)
        
        # Limit do 200 postów
        self.history = self.history[-200:]
        self._save()
        
        return entry["id"]
    
    def get_recent(self, count: int = 10, platform: str = None) -> List[Dict]:
        """Pobiera ostatnie posty"""
        posts = self.history
        if platform:
            posts = [p for p in posts if p["platform"] == platform]
        return posts[-count:]
    
    def get_by_topic(self, topic_keywords: List[str]) -> List[Dict]:
        """Znajduje posty po słowach kluczowych tematu"""
        results = []
        for post in self.history:
            topic_lower = post.get("topic", "").lower()
            if any(kw.lower() in topic_lower for kw in topic_keywords):
                results.append(post)
        return results
    
    def count(self) -> int:
        """Liczba postów w historii"""
        return len(self.history)


# === TESTY MODUŁU ===
if __name__ == "__main__":
    print("=== Test Memory System ===\n")
    
    # Test Brand DNA
    print("1. Brand DNA:")
    brand = BrandMemory()
    print(f"   Marka: {brand.dna['brand_name']}")
    print(f"   Ton: {brand.dna['tone_of_voice']}")
    brand.add_forbidden_word("rewolucyjny")
    print(f"   Zakazane: {brand.dna['forbidden_words'][:5]}...")
    
    # Test Feedback
    print("\n2. Feedback Manager:")
    feedback = FeedbackManager()
    feedback.add_positive("To był świetny post o AI", "LinkedIn")
    feedback.add_adjustment("shorter")
    print(f"   Stats: {feedback.get_stats()}")
    
    # Test History
    print("\n3. Posts History:")
    history = PostsHistory()
    post_id = history.add_post(
        content="Testowy post",
        platform="LinkedIn",
        topic="AI w biznesie"
    )
    print(f"   Dodano post ID: {post_id}")
    print(f"   Łącznie postów: {history.count()}")
    
    print("\n✅ Memory System działa poprawnie!")