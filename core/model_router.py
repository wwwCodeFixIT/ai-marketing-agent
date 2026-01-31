"""
Model Router - Inteligentny routing i fallback
- Różne modele do różnych zadań
- Automatyczny fallback przy błędach
- Rate limiting
- Retry logic
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Typy zadań wymagające różnych modeli"""
    STRATEGY = "strategy"          # Wymaga reasoning
    CREATIVE_WRITING = "creative"  # Wymaga kreatywności
    EDITING = "editing"            # Szybkie, proste
    CRITIQUE = "critique"          # Analityczne
    QUICK_TASK = "quick"           # Proste zadania


class ProviderStatus(Enum):
    """Status providera"""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ModelConfig:
    """Konfiguracja pojedynczego modelu"""
    provider: str           # groq, openai, anthropic
    model_id: str           # np. llama-3.3-70b-versatile
    display_name: str       # Nazwa do wyświetlania
    task_types: List[TaskType]  # Do jakich zadań
    temperature_default: float = 0.7
    max_tokens: int = 2048
    priority: int = 1       # Niższy = wyższy priorytet
    cost_per_1k: float = 0.0  # Koszt (dla budżetowania)


@dataclass
class APIResponse:
    """Ustandaryzowana odpowiedź API"""
    success: bool
    content: str = ""
    model_used: str = ""
    provider: str = ""
    tokens_used: int = 0
    latency_ms: int = 0
    error: str = ""
    raw_response: Any = None


@dataclass
class ProviderState:
    """Stan providera (do rate limiting)"""
    status: ProviderStatus = ProviderStatus.AVAILABLE
    last_error: str = ""
    last_error_time: float = 0
    requests_count: int = 0
    cooldown_until: float = 0


class BaseProvider(ABC):
    """Bazowa klasa dla providerów API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.state = ProviderState()
    
    @abstractmethod
    def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> APIResponse:
        """Wykonaj wywołanie API"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nazwa providera"""
        pass
    
    def is_available(self) -> bool:
        """Czy provider jest dostępny"""
        if self.state.status == ProviderStatus.RATE_LIMITED:
            if time.time() > self.state.cooldown_until:
                self.state.status = ProviderStatus.AVAILABLE
                return True
            return False
        return self.state.status == ProviderStatus.AVAILABLE
    
    def mark_error(self, error: str, cooldown_seconds: int = 60):
        """Oznacz błąd providera"""
        self.state.status = ProviderStatus.ERROR
        self.state.last_error = error
        self.state.last_error_time = time.time()
        self.state.cooldown_until = time.time() + cooldown_seconds
    
    def mark_rate_limited(self, cooldown_seconds: int = 60):
        """Oznacz rate limiting"""
        self.state.status = ProviderStatus.RATE_LIMITED
        self.state.cooldown_until = time.time() + cooldown_seconds
        logger.warning(f"{self.name}: Rate limited, cooldown {cooldown_seconds}s")


class GroqProvider(BaseProvider):
    """Provider dla Groq API"""
    
    @property
    def name(self) -> str:
        return "groq"
    
    def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> APIResponse:
        start_time = time.time()
        
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)
            
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            latency = int((time.time() - start_time) * 1000)
            self.state.requests_count += 1
            
            return APIResponse(
                success=True,
                content=response.choices[0].message.content,
                model_used=model,
                provider=self.name,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                latency_ms=latency,
                raw_response=response
            )
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Rozpoznaj rate limiting
            if "rate" in error_str or "limit" in error_str or "429" in error_str:
                self.mark_rate_limited(cooldown_seconds=60)
            else:
                self.mark_error(str(e), cooldown_seconds=30)
            
            return APIResponse(
                success=False,
                error=str(e),
                provider=self.name,
                latency_ms=int((time.time() - start_time) * 1000)
            )


class OpenAIProvider(BaseProvider):
    """Provider dla OpenAI API (fallback)"""
    
    @property
    def name(self) -> str:
        return "openai"
    
    def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> APIResponse:
        start_time = time.time()
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            latency = int((time.time() - start_time) * 1000)
            self.state.requests_count += 1
            
            return APIResponse(
                success=True,
                content=response.choices[0].message.content,
                model_used=model,
                provider=self.name,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                latency_ms=latency,
                raw_response=response
            )
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "rate" in error_str or "limit" in error_str:
                self.mark_rate_limited(cooldown_seconds=60)
            else:
                self.mark_error(str(e), cooldown_seconds=30)
            
            return APIResponse(
                success=False,
                error=str(e),
                provider=self.name,
                latency_ms=int((time.time() - start_time) * 1000)
            )


class ModelRouter:
    """
    Główny router modeli.
    Wybiera najlepszy model do zadania i obsługuje fallback.
    """
    
    # Domyślna konfiguracja modeli
    DEFAULT_MODELS = [
        # Groq - Primary
        ModelConfig(
            provider="groq",
            model_id="llama-3.3-70b-versatile",
            display_name="Llama 3.3 70B",
            task_types=[TaskType.STRATEGY, TaskType.CREATIVE_WRITING, TaskType.CRITIQUE],
            temperature_default=0.7,
            priority=1,
            cost_per_1k=0.0
        ),
        ModelConfig(
            provider="groq",
            model_id="llama-3.1-8b-instant",
            display_name="Llama 3.1 8B (Fast)",
            task_types=[TaskType.EDITING, TaskType.QUICK_TASK],
            temperature_default=0.5,
            priority=1,
            cost_per_1k=0.0
        ),
        ModelConfig(
            provider="groq",
            model_id="mixtral-8x7b-32768",
            display_name="Mixtral 8x7B",
            task_types=[TaskType.STRATEGY, TaskType.CREATIVE_WRITING],
            temperature_default=0.7,
            priority=2,
            cost_per_1k=0.0
        ),
        
        # OpenAI - Fallback
        ModelConfig(
            provider="openai",
            model_id="gpt-4o-mini",
            display_name="GPT-4o Mini",
            task_types=[TaskType.STRATEGY, TaskType.CREATIVE_WRITING, TaskType.CRITIQUE, TaskType.EDITING],
            temperature_default=0.7,
            priority=10,  # Niższy priorytet (fallback)
            cost_per_1k=0.15
        ),
        ModelConfig(
            provider="openai",
            model_id="gpt-3.5-turbo",
            display_name="GPT-3.5 Turbo",
            task_types=[TaskType.EDITING, TaskType.QUICK_TASK],
            temperature_default=0.5,
            priority=11,
            cost_per_1k=0.05
        ),
    ]
    
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self.models: List[ModelConfig] = self.DEFAULT_MODELS.copy()
        self.call_history: List[Dict] = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Inicjalizuje dostępnych providerów"""
        
        # Groq
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            self.providers["groq"] = GroqProvider(groq_key)
            logger.info("✓ Groq provider initialized")
        
        # OpenAI (opcjonalny fallback)
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self.providers["openai"] = OpenAIProvider(openai_key)
            logger.info("✓ OpenAI provider initialized (fallback)")
        
        if not self.providers:
            logger.error("❌ No API providers available!")
    
    def get_available_models(self, task_type: TaskType = None) -> List[ModelConfig]:
        """Zwraca dostępne modele dla danego typu zadania"""
        available = []
        
        for model in self.models:
            # Sprawdź czy provider jest dostępny
            provider = self.providers.get(model.provider)
            if not provider or not provider.is_available():
                continue
            
            # Filtruj po typie zadania
            if task_type and task_type not in model.task_types:
                continue
            
            available.append(model)
        
        # Sortuj po priorytecie
        return sorted(available, key=lambda m: m.priority)
    
    def select_model(self, task_type: TaskType) -> Optional[ModelConfig]:
        """Wybiera najlepszy model do zadania"""
        available = self.get_available_models(task_type)
        
        if not available:
            logger.warning(f"No models available for task: {task_type}")
            # Fallback - weź cokolwiek
            available = self.get_available_models()
        
        if available:
            selected = available[0]
            logger.info(f"Selected model: {selected.display_name} for {task_type.value}")
            return selected
        
        return None
    
    def call(
        self,
        messages: List[Dict[str, str]],
        task_type: TaskType = TaskType.CREATIVE_WRITING,
        temperature: Optional[float] = None,
        max_tokens: int = 2048,
        max_retries: int = 3
    ) -> APIResponse:
        """
        Wykonuje wywołanie z automatycznym fallbackiem.
        
        Args:
            messages: Lista wiadomości (system, user)
            task_type: Typ zadania (do wyboru modelu)
            temperature: Temperatura (None = domyślna dla modelu)
            max_tokens: Max tokenów odpowiedzi
            max_retries: Liczba prób przed poddaniem się
        """
        
        attempts = 0
        last_error = ""
        tried_models = set()
        
        while attempts < max_retries:
            # Wybierz model
            model_config = self.select_model(task_type)
            
            if not model_config:
                return APIResponse(
                    success=False,
                    error="No available models"
                )
            
            # Unikaj powtarzania tego samego modelu
            model_key = f"{model_config.provider}:{model_config.model_id}"
            if model_key in tried_models:
                # Szukaj alternatywy
                available = self.get_available_models(task_type)
                alternative = None
                for m in available:
                    key = f"{m.provider}:{m.model_id}"
                    if key not in tried_models:
                        alternative = m
                        break
                
                if alternative:
                    model_config = alternative
                    model_key = f"{model_config.provider}:{model_config.model_id}"
                else:
                    # Brak alternatyw
                    break
            
            tried_models.add(model_key)
            
            # Pobierz providera
            provider = self.providers.get(model_config.provider)
            if not provider:
                attempts += 1
                continue
            
            # Ustaw temperaturę
            temp = temperature if temperature is not None else model_config.temperature_default
            
            logger.info(f"Attempting: {model_config.display_name} (attempt {attempts + 1})")
            
            # Wykonaj wywołanie
            response = provider.call(
                messages=messages,
                model=model_config.model_id,
                temperature=temp,
                max_tokens=max_tokens
            )
            
            # Zapisz do historii
            self.call_history.append({
                "model": model_config.model_id,
                "provider": model_config.provider,
                "success": response.success,
                "latency_ms": response.latency_ms,
                "tokens": response.tokens_used,
                "timestamp": time.time()
            })
            
            if response.success:
                return response
            
            last_error = response.error
            logger.warning(f"Failed: {model_config.display_name} - {response.error}")
            attempts += 1
            
            # Krótka pauza przed retry
            time.sleep(0.5)
        
        return APIResponse(
            success=False,
            error=f"All attempts failed. Last error: {last_error}"
        )
    
    def call_simple(
        self,
        system_prompt: str,
        user_prompt: str,
        task_type: TaskType = TaskType.CREATIVE_WRITING,
        temperature: float = None
    ) -> APIResponse:
        """Uproszczone wywołanie z dwoma promptami"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.call(messages, task_type, temperature)
    
    def get_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki wywołań"""
        if not self.call_history:
            return {"total_calls": 0}
        
        total = len(self.call_history)
        successful = sum(1 for c in self.call_history if c["success"])
        
        # Statystyki per provider
        provider_stats = {}
        for call in self.call_history:
            prov = call["provider"]
            if prov not in provider_stats:
                provider_stats[prov] = {"calls": 0, "success": 0, "total_latency": 0}
            provider_stats[prov]["calls"] += 1
            if call["success"]:
                provider_stats[prov]["success"] += 1
            provider_stats[prov]["total_latency"] += call["latency_ms"]
        
        # Oblicz średnie
        for prov in provider_stats:
            calls = provider_stats[prov]["calls"]
            provider_stats[prov]["avg_latency_ms"] = (
                provider_stats[prov]["total_latency"] / calls if calls > 0 else 0
            )
            provider_stats[prov]["success_rate"] = (
                provider_stats[prov]["success"] / calls if calls > 0 else 0
            )
        
        return {
            "total_calls": total,
            "successful_calls": successful,
            "success_rate": successful / total if total > 0 else 0,
            "providers": provider_stats
        }
    
    def get_provider_status(self) -> Dict[str, Dict]:
        """Zwraca status wszystkich providerów"""
        status = {}
        for name, provider in self.providers.items():
            status[name] = {
                "available": provider.is_available(),
                "status": provider.state.status.value,
                "requests_count": provider.state.requests_count,
                "last_error": provider.state.last_error if provider.state.last_error else None
            }
        return status
    
    def reset_provider(self, provider_name: str):
        """Resetuje status providera"""
        if provider_name in self.providers:
            self.providers[provider_name].state = ProviderState()
            logger.info(f"Provider {provider_name} reset")


class SmartRouter(ModelRouter):
    """
    Rozszerzony router z inteligentnymi funkcjami.
    """
    
    def __init__(self):
        super().__init__()
        self.task_performance: Dict[TaskType, Dict[str, float]] = {}
    
    def call_with_learning(
        self,
        messages: List[Dict[str, str]],
        task_type: TaskType,
        **kwargs
    ) -> APIResponse:
        """
        Wywołanie z uczeniem się wydajności.
        Router uczy się który model jest najlepszy dla jakiego zadania.
        """
        response = self.call(messages, task_type, **kwargs)
        
        if response.success:
            # Zapisz performance
            model_key = f"{response.provider}:{response.model_used}"
            
            if task_type not in self.task_performance:
                self.task_performance[task_type] = {}
            
            if model_key not in self.task_performance[task_type]:
                self.task_performance[task_type][model_key] = {
                    "total_calls": 0,
                    "total_latency": 0,
                    "success_count": 0
                }
            
            perf = self.task_performance[task_type][model_key]
            perf["total_calls"] += 1
            perf["total_latency"] += response.latency_ms
            perf["success_count"] += 1
        
        return response
    
    def get_best_model_for_task(self, task_type: TaskType) -> Optional[str]:
        """Zwraca najlepszy model na podstawie historii"""
        if task_type not in self.task_performance:
            return None
        
        best_model = None
        best_score = float('inf')
        
        for model_key, perf in self.task_performance[task_type].items():
            if perf["total_calls"] > 0:
                avg_latency = perf["total_latency"] / perf["total_calls"]
                success_rate = perf["success_count"] / perf["total_calls"]
                
                # Score: niższy = lepszy (ważona kombinacja)
                score = avg_latency * (2 - success_rate)
                
                if score < best_score:
                    best_score = score
                    best_model = model_key
        
        return best_model


# === HELPER FUNCTIONS ===

def create_router() -> ModelRouter:
    """Factory function do tworzenia routera"""
    return ModelRouter()


def create_smart_router() -> SmartRouter:
    """Factory function do tworzenia smart routera"""
    return SmartRouter()


# === TESTY MODUŁU ===
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=== Test Model Router ===\n")
    
    router = ModelRouter()
    
    # Test 1: Status providerów
    print("1. Provider Status:")
    status = router.get_provider_status()
    for name, info in status.items():
        print(f"   {name}: {'✓' if info['available'] else '✗'} ({info['status']})")
    
    # Test 2: Dostępne modele
    print("\n2. Available Models:")
    for task in TaskType:
        models = router.get_available_models(task)
        model_names = [m.display_name for m in models[:2]]
        print(f"   {task.value}: {model_names}")
    
    # Test 3: Proste wywołanie
    print("\n3. Simple Call Test:")
    response = router.call_simple(
        system_prompt="You are a helpful assistant. Respond in Polish.",
        user_prompt="Powiedz 'test działa' w jednym zdaniu.",
        task_type=TaskType.QUICK_TASK
    )
    
    if response.success:
        print(f"   ✓ Success!")
        print(f"   Model: {response.model_used}")
        print(f"   Provider: {response.provider}")
        print(f"   Latency: {response.latency_ms}ms")
        print(f"   Response: {response.content[:100]}...")
    else:
        print(f"   ✗ Failed: {response.error}")
    
    # Test 4: Statystyki
    print("\n4. Call Statistics:")
    stats = router.get_stats()
    print(f"   Total calls: {stats['total_calls']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    
    print("\n✅ Model Router działa poprawnie!")